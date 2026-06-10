import uuid
from pathlib import Path

from django.core.files import File
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from blog.models import Category, Comment, Like, Post, UserProfile

# Real demo images bundled with the repo so seeding works on any host
# (PythonAnywhere's free tier blocks downloads from external image sites).
ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / 'seed_assets'

DEMO_PASSWORD = 'user123'

# Bundled image filenames, assigned to demo users/posts by position.
AVATAR_FILES = ['avatar1.jpg', 'avatar2.jpg', 'avatar3.jpg', 'avatar4.jpg']
POST_FILES = ['post1.jpg', 'post2.jpg', 'post3.jpg', 'post4.jpg']

DEMO_USERS = [
    {
        'username': 'moderator1',
        'role': 'moderator',
        'bio': 'Keeping things civil around here.',
    },
    {
        'username': 'user1',
        'role': 'user',
        'bio': 'Avid reader and occasional writer.',
    },
    {
        'username': 'user2',
        'role': 'user',
        'bio': 'Loves design and coffee.',
    },
    {
        'username': 'user3',
        'role': 'user',
        'bio': 'Just here to share ideas.',
    },
]

DEMO_POSTS = [
    {
        'author': 'user1',
        'category': 'Technology',
        'title': 'Getting Started with Django',
        'body': (
            'Django is a high-level Python web framework that encourages rapid development '
            'and clean, pragmatic design. It takes care of much of the hassle of web '
            'development so you can focus on writing your app without needing to reinvent '
            'the wheel.\n\n'
            'In this post I want to share some tips that helped me when I was first learning '
            'Django: read the official tutorial all the way through, understand the ORM before '
            'reaching for raw SQL, and lean on class-based views once you are comfortable with '
            'function-based ones.'
        ),
    },
    {
        'author': 'user1',
        'category': 'Tutorial',
        'title': 'Understanding Django ORM Querysets',
        'body': (
            'Querysets are one of Django\'s most powerful features. They are lazy — meaning '
            'the database is not actually hit until you evaluate the queryset by iterating '
            'over it, slicing it, or calling methods like list() or len().\n\n'
            'Some quick tips:\n'
            '- Use select_related() for ForeignKey lookups to avoid N+1 queries.\n'
            '- Use prefetch_related() for ManyToMany or reverse FK relationships.\n'
            '- Use annotate() + Count() instead of Python-level loops for aggregates.'
        ),
    },
    {
        'author': 'user2',
        'category': 'Design',
        'title': 'Why Minimalist UI Works',
        'body': (
            'There is a reason nearly every major product redesign over the last decade has '
            'moved toward minimalism. Fewer distractions mean users accomplish their goals '
            'faster and with less frustration.\n\n'
            'Minimalism is not about removing features — it is about presenting the right '
            'features clearly. White space, consistent typography, and a restrained colour '
            'palette do most of the heavy lifting. The hardest part is deciding what to leave out.'
        ),
    },
    {
        'author': 'user3',
        'category': 'Opinion',
        'title': 'Open Source Changed How I Think About Software',
        'body': (
            'Before I started contributing to open source I thought of software as a product '
            'you downloaded and used. After my first pull request was merged I started seeing '
            'it as a living conversation between people who care about the same problems.\n\n'
            'Reading other people\'s code is the fastest way I have found to level up. You see '
            'patterns you would never have invented yourself, and you start to understand the '
            'trade-offs that experienced engineers make every day.'
        ),
    },
]

# No moderator comments. Moderator role exists but they do not post here.
DEMO_COMMENTS = [
    # user2 and user3 on user1's posts
    {'post_title': 'Getting Started with Django',        'author': 'user2', 'body': 'Great intro! The tip about reading the tutorial end-to-end really resonates.'},
    {'post_title': 'Getting Started with Django',        'author': 'user3', 'body': 'Saved me hours of confusion when I was starting out. Thanks for writing this up.'},
    {'post_title': 'Understanding Django ORM Querysets', 'author': 'user2', 'body': 'The select_related vs prefetch_related distinction tripped me up for weeks. Wish I had read this sooner.'},
    {'post_title': 'Understanding Django ORM Querysets', 'author': 'user3', 'body': 'annotate + Count is a game changer for dashboards. Good call including that.'},
    # user1 and user3 on user2's post
    {'post_title': 'Why Minimalist UI Works',            'author': 'user1', 'body': 'Deciding what to leave out is genuinely the hardest part. Great way to put it.'},
    {'post_title': 'Why Minimalist UI Works',            'author': 'user3', 'body': 'I have been burned by feature creep too many times. Minimalism as a discipline, not just aesthetics.'},
    # user1 and user2 on user3's post
    {'post_title': 'Open Source Changed How I Think About Software', 'author': 'user1', 'body': 'That feeling when your first PR is merged is unforgettable. Totally agree.'},
    {'post_title': 'Open Source Changed How I Think About Software', 'author': 'user2', 'body': 'Reading others\' code taught me more than any course I have taken.'},
]

# (liker, post_title)
DEMO_LIKES = [
    ('user2', 'Getting Started with Django'),
    ('user3', 'Getting Started with Django'),
    ('user1', 'Why Minimalist UI Works'),
    ('user3', 'Why Minimalist UI Works'),
    ('user1', 'Open Source Changed How I Think About Software'),
    ('user2', 'Open Source Changed How I Think About Software'),
    ('user3', 'Understanding Django ORM Querysets'),
]


def _load_asset(filename):
    """Open a bundled demo image and return a (django File, save_name) pair,
    or (None, None) if the file is missing."""
    src = ASSETS_DIR / filename
    if not src.exists():
        return None, None
    return File(open(src, 'rb')), f'{uuid.uuid4().hex}.jpg'


class Command(BaseCommand):
    help = 'Populate the blog with demo users, posts, comments, and likes (safe to re-run)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo data before seeding',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self._reset()

        counts = {'users': 0, 'posts': 0, 'comments': 0, 'likes': 0}

        # ── users ──────────────────────────────────────────────────────────────
        user_objs = {}
        for i, data in enumerate(DEMO_USERS):
            user, created = User.objects.get_or_create(username=data['username'])
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                counts['users'] += 1

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = data['role']
            profile.bio = data['bio']

            if not profile.avatar:
                fh, name = _load_asset(AVATAR_FILES[i % len(AVATAR_FILES)])
                if fh:
                    profile.avatar.save(name, fh, save=False)
                    fh.close()
                    self.stdout.write(self.style.SUCCESS(f'  + avatar: {user.username}'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ! avatar asset missing for {user.username}'))

            profile.save()
            user_objs[user.username] = user

        # ── categories ─────────────────────────────────────────────────────────
        cat_objs = {}
        for name in {p['category'] for p in DEMO_POSTS}:
            cat, _ = Category.objects.get_or_create(name=name)
            cat_objs[name] = cat

        # ── posts ──────────────────────────────────────────────────────────────
        post_objs = {}
        for i, data in enumerate(DEMO_POSTS):
            author = user_objs.get(data['author']) or User.objects.filter(username=data['author']).first()
            if not author:
                self.stdout.write(self.style.WARNING(f'  ! author not found: {data["author"]}, skipping'))
                continue

            post, created = Post.objects.get_or_create(
                title=data['title'],
                author=author,
                defaults={
                    'body': data['body'],
                    'category': cat_objs.get(data['category']),
                },
            )

            if created:
                counts['posts'] += 1
                fh, name = _load_asset(POST_FILES[i % len(POST_FILES)])
                if fh:
                    post.image.save(name, fh, save=True)
                    fh.close()
                    self.stdout.write(self.style.SUCCESS(f'  + post: "{post.title}"'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ! image asset missing for "{post.title}"'))

            post_objs[post.title] = post

        # ── comments ───────────────────────────────────────────────────────────
        for data in DEMO_COMMENTS:
            post = post_objs.get(data['post_title']) or Post.objects.filter(title=data['post_title']).first()
            author = user_objs.get(data['author']) or User.objects.filter(username=data['author']).first()
            if not post or not author:
                continue
            _, created = Comment.objects.get_or_create(post=post, author=author, body=data['body'])
            if created:
                counts['comments'] += 1

        # ── likes ──────────────────────────────────────────────────────────────
        for liker_name, post_title in DEMO_LIKES:
            liker = user_objs.get(liker_name) or User.objects.filter(username=liker_name).first()
            post = post_objs.get(post_title) or Post.objects.filter(title=post_title).first()
            if not liker or not post:
                continue
            _, created = Like.objects.get_or_create(user=liker, post=post)
            if created:
                counts['likes'] += 1

        # ── summary ────────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo data seed complete:'))
        self.stdout.write(f'  users created    : {counts["users"]}')
        self.stdout.write(f'  posts created    : {counts["posts"]}')
        self.stdout.write(f'  comments created : {counts["comments"]}')
        self.stdout.write(f'  likes created    : {counts["likes"]}')

    def _reset(self):
        demo_usernames = [d['username'] for d in DEMO_USERS]
        demo_titles    = [d['title']    for d in DEMO_POSTS]
        Like.objects.filter(post__title__in=demo_titles).delete()
        Comment.objects.filter(post__title__in=demo_titles).delete()
        Post.objects.filter(title__in=demo_titles).delete()
        User.objects.filter(username__in=demo_usernames).delete()
        self.stdout.write(self.style.WARNING('  Demo data cleared.'))
