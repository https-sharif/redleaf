import os
import uuid
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from PIL import Image as PilImage
from django.core.files.uploadedfile import InMemoryUploadedFile

from .forms import CommentForm, PostForm, ProfileForm, RegisterForm, UserRoleForm
from .models import Category, Comment, Like, Post, UserProfile
from .permissions import (
    can_delete_comment,
    can_delete_post,
    can_edit_post,
    get_role,
    is_super_admin,
)


def _compress_image(image_file, max_size=(1200, 1200), quality=82):
    try:
        img = PilImage.open(image_file)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        img.thumbnail(max_size, PilImage.LANCZOS)
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        buf.seek(0)
        name = f'{uuid.uuid4().hex}.jpg'
        return InMemoryUploadedFile(buf, 'ImageField', name, 'image/jpeg', buf.getbuffer().nbytes, None)
    except Exception:
        return None


def _delete_file(field):
    if field and field.name:
        try:
            os.remove(field.path)
        except (ValueError, FileNotFoundError, OSError):
            pass


# ---------------------------------------------------------------------------
# Blog posts
# ---------------------------------------------------------------------------

def post_list(request):
    posts = (
        Post.objects
        .select_related('author', 'category')
        .annotate(like_count=Count('likes'))
    )
    categories = Category.objects.all()
    return render(request, 'blog/post_list.html', {
        'posts': posts,
        'categories': categories,
        'active_category': None,
    })


def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    posts = (
        Post.objects
        .filter(category=category)
        .select_related('author', 'category')
        .annotate(like_count=Count('likes'))
    )
    categories = Category.objects.all()
    return render(request, 'blog/post_list.html', {
        'posts': posts,
        'categories': categories,
        'active_category': category,
    })


def post_detail(request, pk):
    post = get_object_or_404(Post.objects.select_related('author', 'category'), pk=pk)
    comments = post.comments.select_related('author').all()
    comment_form = CommentForm()
    liked = post.likes.filter(user=request.user).exists() if request.user.is_authenticated else False
    like_count = post.likes.count()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comment added.')
            return redirect('post_detail', pk=pk)

    return render(request, 'blog/post_detail.html', {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'can_edit': can_edit_post(request.user, post),
        'can_delete': can_delete_post(request.user, post),
        'liked': liked,
        'like_count': like_count,
    })


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            if 'image' in request.FILES:
                compressed = _compress_image(request.FILES['image'])
                if compressed:
                    post.image = compressed
                else:
                    form.add_error('image', 'Could not process image.')
                    return render(request, 'blog/post_form.html', {'form': form, 'action': 'Create'})
            post.save()
            messages.success(request, 'Post created.')
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm()
    return render(request, 'blog/post_form.html', {'form': form, 'action': 'Create'})


@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if not can_edit_post(request.user, post):
        return HttpResponseForbidden('You cannot edit this post.')
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated = form.save(commit=False)
            if 'image' in request.FILES:
                compressed = _compress_image(request.FILES['image'])
                if compressed:
                    _delete_file(post.image)
                    updated.image = compressed
                else:
                    form.add_error('image', 'Could not process image.')
                    return render(request, 'blog/post_form.html', {'form': form, 'action': 'Edit', 'post': post})
            updated.save()
            messages.success(request, 'Post updated.')
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/post_form.html', {'form': form, 'action': 'Edit', 'post': post})


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if not can_delete_post(request.user, post):
        return HttpResponseForbidden('You cannot delete this post.')
    if request.method == 'POST':
        _delete_file(post.image)
        post.delete()
        messages.success(request, 'Post deleted.')
        return redirect('post_list')
    return render(request, 'blog/post_confirm_delete.html', {'post': post})


@login_required
def post_like(request, pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    return redirect('post_detail', pk=pk)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    post_pk = comment.post.pk
    if not can_delete_comment(request.user, comment):
        return HttpResponseForbidden('You cannot delete this comment.')
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comment deleted.')
        return redirect('post_detail', pk=post_pk)
    return render(request, 'blog/comment_confirm_delete.html', {'comment': comment})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def register(request):
    if request.user.is_authenticated:
        return redirect('post_list')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user, role='user')
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('post_list')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('post_list')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next', 'post_list')
            return redirect(next_url)
        messages.error(request, 'Invalid username or password.')
    return render(request, 'registration/login.html')


def user_logout(request):
    logout(request)
    return redirect('post_list')


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------

def profile_view(request, username):
    target_user = get_object_or_404(User, username=username)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    posts = (
        Post.objects
        .filter(author=target_user)
        .select_related('category')
        .annotate(like_count=Count('likes'))
    )
    total_likes = Like.objects.filter(post__author=target_user).count()
    return render(request, 'blog/profile.html', {
        'target_user': target_user,
        'profile': profile,
        'posts': posts,
        'total_likes': total_likes,
        'is_own_profile': request.user == target_user,
    })


@login_required
def profile_edit(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            updated = form.save(commit=False)
            if 'avatar' in request.FILES:
                compressed = _compress_image(request.FILES['avatar'], max_size=(400, 400), quality=85)
                if compressed:
                    _delete_file(profile.avatar)
                    updated.avatar = compressed
                else:
                    form.add_error('avatar', 'Could not process image.')
                    return render(request, 'blog/profile_edit.html', {'form': form})
            updated.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile', username=request.user.username)
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'blog/profile_edit.html', {'form': form})


# ---------------------------------------------------------------------------
# User management (super admin)
# ---------------------------------------------------------------------------

@login_required
def user_management(request):
    if not is_super_admin(request.user):
        return HttpResponseForbidden('Only super admins can manage users.')
    users = User.objects.select_related('profile').exclude(pk=request.user.pk).order_by('username')
    return render(request, 'blog/user_management.html', {'users': users})


@login_required
def user_change_role(request, pk):
    if not is_super_admin(request.user):
        return HttpResponseForbidden('Only super admins can change roles.')
    target_user = get_object_or_404(User, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    if request.method == 'POST':
        form = UserRoleForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f'Role updated for {target_user.username}.')
            return redirect('user_management')
    else:
        form = UserRoleForm(instance=profile)
    return render(request, 'blog/user_change_role.html', {'form': form, 'target_user': target_user})


@login_required
def user_delete(request, pk):
    if not is_super_admin(request.user):
        return HttpResponseForbidden('Only super admins can delete users.')
    target_user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        target_user.delete()
        messages.success(request, 'User deleted.')
        return redirect('user_management')
    return render(request, 'blog/user_confirm_delete.html', {'target_user': target_user})
