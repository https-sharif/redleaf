from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Post, Comment, UserProfile, Category

_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


def _validate_image_file(image):
    if image and hasattr(image, 'size'):
        if image.size > _MAX_IMAGE_BYTES:
            raise forms.ValidationError('Image must be under 10 MB.')
        from PIL import Image
        try:
            img = Image.open(image)
            img.verify()
            image.seek(0)
        except Exception:
            raise forms.ValidationError('Invalid or unsupported image file.')


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control form-control-sm'})


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'category', 'body', 'image')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'category': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'body': forms.Textarea(attrs={'rows': 8, 'class': 'form-control form-control-sm'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm', 'accept': 'image/*'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        _validate_image_file(image)
        return image


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Write a comment...',
                'class': 'form-control form-control-sm',
            }),
        }
        labels = {'body': ''}


class UserRoleForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('role',)
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control form-control-sm'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm', 'accept': 'image/*'}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        _validate_image_file(avatar)
        return avatar
