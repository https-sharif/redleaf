from django.urls import path
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/create/', views.post_create, name='post_create'),
    path('post/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('post/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('post/<int:pk>/like/', views.post_like, name='post_like'),
    path('comment/<int:pk>/delete/', views.comment_delete, name='comment_delete'),
    path('category/<slug:slug>/', views.category_view, name='category_view'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('users/', views.user_management, name='user_management'),
    path('users/<int:pk>/role/', views.user_change_role, name='user_change_role'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
]
