from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from blog.models import Category, UserProfile

SEED_USERS = [
    {'username': 'admin',     'password': 'admin123',  'role': 'super_admin', 'is_staff': True, 'is_superuser': True},
    {'username': 'moderator', 'password': 'mod123',    'role': 'moderator'},
    {'username': 'usera',     'password': 'usera123',  'role': 'user'},
    {'username': 'userb',     'password': 'userb123',  'role': 'user'},
    {'username': 'userc',     'password': 'userc123',  'role': 'user'},
]

SEED_CATEGORIES = ['Technology', 'Design', 'Tutorial', 'News', 'Opinion', 'Project']


class Command(BaseCommand):
    help = 'Seed the database with test users and categories'

    def handle(self, *args, **options):
        for name in SEED_CATEGORIES:
            cat, created = Category.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  created category: {name}'))
            else:
                self.stdout.write(f'  skipped category (exists): {name}')

        for data in SEED_USERS:
            username = data['username']
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'  skipped user (exists): {username}')
                continue
            user = User.objects.create_user(
                username=username,
                password=data['password'],
                is_staff=data.get('is_staff', False),
                is_superuser=data.get('is_superuser', False),
            )
            UserProfile.objects.create(user=user, role=data['role'])
            self.stdout.write(self.style.SUCCESS(f'  created user: {username} ({data["role"]})'))

        self.stdout.write(self.style.SUCCESS('Seed complete.'))
