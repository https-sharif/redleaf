import ssl
import urllib.request
import uuid
from io import BytesIO

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management.base import BaseCommand

from blog.models import Category, Comment, Like, Post, UserProfile

DEMO_PASSWORD = 'user123'

# picsum.photos/seed/<seed>/WxH  — deterministic, always the same image for the same seed
DEMO_USERS = [
    {
        'username': 'moderator1',
        'role': 'moderator',
        'bio': 'Keeping things civil around here.',
        'avatar_url': 'https://picsum.photos/seed/mod1/150/150',
    },
    {
        'username': 'user1',
        'role': 'user',
        'bio': 'Avid reader and occasional writer.',
        'avatar_url': 'https://picsum.photos/seed/usr1/150/150',
    },
    {
        'username': 'user2',
        'role': 'user',
        'bio': 'Loves design and coffee.',
        'avatar_url': 'https://picsum.photos/seed/usr2/150/150',
    },
    {
        'username': 'user3',
        'role': 'user',
        'bio': 'Just here to share ideas.',
        'avatar_url': 'https://picsum.photos/seed/usr3/150/150',
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
        'image_url': 'https://picsum.photos/seed/post1/900/400',
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
        'image_url': 'https://picsum.photos/seed/post2/900/400',
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
        'image_url': 'https://picsum.photos/seed/post3/900/400',
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
        'image_url': 'https://picsum.photos/seed/post4/900/400',
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


def _parse_seed_and_size(url):
    """Extract (seed, width, height) from a picsum URL like
    https://picsum.photos/seed/<seed>/<W>/<H>. Falls back to sane defaults."""
    parts = [p for p in url.split('/') if p]
    seed, width, height = url, 600, 400
    try:
        if 'seed' in parts:
            i = parts.index('seed')
            seed = parts[i + 1]
            width = int(parts[i + 2])
            height = int(parts[i + 3])
    except (ValueError, IndexError):
        pass
    return seed, width, height


def _color_from_seed(seed):
    """Deterministic, pleasant RGB color from a seed string (no randomness)."""
    h = 0
    for ch in seed:
        h = (h * 31 + ord(ch)) & 0xFFFFFF
    # keep channels in the mid range so text stays readable
    r = 60 + (h & 0x7F)
    g = 60 + ((h >> 8) & 0x7F)
    b = 60 + ((h >> 16) & 0x7F)
    return (r, g, b)


def _placeholder_image(url):
    """Generate a solid-color placeholder locally so seeding works without
    network access (e.g. PythonAnywhere free tier blocks picsum.photos)."""
    from PIL import Image, ImageDraw
    seed, width, height = _parse_seed_and_size(url)
    img = Image.new('RGB', (width, height), _color_from_seed(seed))
    draw = ImageDraw.Draw(img)
    label = seed[:18]
    # rough centering without needing a font file
    tw = len(label) * 6
    draw.text((max((width - tw) // 2, 4), height // 2 - 6), label, fill=(255, 255, 255))
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=82)
    buf.seek(0)
    name = f'{uuid.uuid4().hex}.jpg'
    return InMemoryUploadedFile(buf, 'ImageField', name, 'image/jpeg', buf.getbuffer().nbytes, None)


def _fetch_image(url, filename):
    """Download url and return an InMemoryUploadedFile. If the download fails
    (offline, or host blocks external sites), fall back to a locally generated
    placeholder so demo posts/avatars always have an image."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
            data = resp.read()
        buf = BytesIO(data)
        name = f'{uuid.uuid4().hex}.jpg'
        return InMemoryUploadedFile(buf, 'ImageField', name, 'image/jpeg', len(data), None)
    except Exception:
        try:
            return _placeholder_image(url)
        except Exception:
            return None


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
        for data in DEMO_USERS:
            user, created = User.objects.get_or_create(username=data['username'])
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                counts['users'] += 1

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = data['role']
            profile.bio = data['bio']

            if not profile.avatar:
                self.stdout.write(f'  fetching avatar for {user.username}...')
                img = _fetch_image(data['avatar_url'], 'avatar.jpg')
                if img:
                    profile.avatar = img
                    self.stdout.write(self.style.SUCCESS(f'  + avatar: {user.username}'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ! avatar fetch failed for {user.username}'))

            profile.save()
            user_objs[user.username] = user

        # ── categories ─────────────────────────────────────────────────────────
        cat_objs = {}
        for name in {p['category'] for p in DEMO_POSTS}:
            cat, _ = Category.objects.get_or_create(name=name)
            cat_objs[name] = cat

        # ── posts ──────────────────────────────────────────────────────────────
        post_objs = {}
        for data in DEMO_POSTS:
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
                self.stdout.write(f'  fetching image for "{post.title}"...')
                img = _fetch_image(data['image_url'], 'post.jpg')
                if img:
                    post.image = img
                    post.save()
                    self.stdout.write(self.style.SUCCESS(f'  + post: "{post.title}"'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ! image fetch failed for "{post.title}"'))

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
