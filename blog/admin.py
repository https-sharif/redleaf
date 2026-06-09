from django.contrib import admin
from .models import Category, Comment, Like, Post, UserProfile

admin.site.register(Category)
admin.site.register(UserProfile)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Like)
