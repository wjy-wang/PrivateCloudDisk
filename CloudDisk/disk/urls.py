"""
URL configuration for CloudDisk project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# disk/urls.py
from django.urls import path
from . import views

app_name = 'disk'

urlpatterns = [
    #用户认证路由
    path('', views.login_view, name='login'),
    path('home/', views.home_view, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('user-agreement/', views.user_agreement_view, name='user_agreement'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    
    
    # 文件操作路由
    path('upload/', views.upload_file, name='upload'),
    path('download/<int:file_id>/', views.download_file, name='download'),
    path('delete/<int:file_id>/', views.delete_file, name='delete'),
    
    # 回收站相关路由
    path('trash/', views.trash_view, name='trash'),
    path('restore/<int:file_id>/', views.restore_file, name='restore_file'),
    path('permanent-delete/<int:file_id>/', views.permanent_delete_file, name='permanent_delete_file'),
    path('empty-trash/', views.empty_trash, name='empty_trash'),
    
    # 分类路由
    path('images/', views.images_view, name='images'),
    path('documents/', views.documents_view, name='documents'),
    path('videos/', views.videos_view, name='videos'),
    path('audios/', views.audios_view, name='audios'),
    path('others/', views.others_view, name='others'),
]