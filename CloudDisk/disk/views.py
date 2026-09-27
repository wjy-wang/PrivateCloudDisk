# disk/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils import timezone
import os
from .models import File, UserProfile
from .swift_backend import SwiftStorage

#用户认证视图函数
def login_view(request):
    """登录视图"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, '登录成功！')
            return redirect('disk:home')
        else:
            messages.error(request, '用户名或密码错误！')
    
    return render(request, 'login.html')

def register_view(request):
    """注册视图"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # 基本验证
        if not username or not password:
            messages.error(request, '用户名和密码不能为空！')
            return render(request, 'register.html')
        
        if password != confirm_password:
            messages.error(request, '两次输入的密码不一致！')
            return render(request, 'register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在！')
            return render(request, 'register.html')
        
        # 创建用户
        try:
            user = User.objects.create_user(username=username, password=password)
            user.save()
            
            # 创建用户配置
            UserProfile.objects.create(user=user)
            
            messages.success(request, '注册成功！请登录。')
            return redirect('disk:login')
        except Exception as e:
            messages.error(request, f'注册失败：{str(e)}')
    
    return render(request, 'register.html')

def logout_view(request):
    """登出视图"""
    logout(request)
    messages.success(request, '已成功退出登录！')
    return redirect('disk:login')

def user_agreement_view(request):
    """用户协议视图"""
    return render(request, 'user_agreement.html')

def privacy_policy_view(request):
    """隐私政策视图"""
    return render(request, 'privacy_policy.html')

def forgot_password_view(request):
    """忘记密码视图"""
    if request.method == 'POST':
        username = request.POST.get('username')
        messages.info(request, f'如果用户"{username}"存在，重置密码链接已发送到注册邮箱。')
        return render(request, 'forgot_password.html')
    
    return render(request, 'forgot_password.html')

@login_required
def home_view(request):
    """首页 - 显示未删除的文件"""
    # 只显示未删除的文件
    files = File.objects.filter(user=request.user, is_deleted=False).order_by('-upload_time')
    
    # 文件统计（不包括回收站中的文件）
    file_stats = {
        'all': File.objects.filter(user=request.user, is_deleted=False).count(),
        'image': File.objects.filter(user=request.user, file_type='image', is_deleted=False).count(),
        'document': File.objects.filter(user=request.user, file_type='document', is_deleted=False).count(),
        'video': File.objects.filter(user=request.user, file_type='video', is_deleted=False).count(),
        'audio': File.objects.filter(user=request.user, file_type='audio', is_deleted=False).count(),
        'other': File.objects.filter(user=request.user, file_type='other', is_deleted=False).count(),
        'trash': File.objects.filter(user=request.user, is_deleted=True).count()  # 回收站文件数量
    }
    
    # 计算存储使用情况
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    storage_used = user_profile.storage_used
    storage_limit = user_profile.storage_limit
    storage_percent = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
    
    context = {
        'user': request.user,
        'files': files,
        'file_stats': file_stats,
        'storage_used': storage_used,
        'storage_limit': storage_limit,
        'storage_percent': storage_percent,
        'current_type': 'all'
    }
    return render(request, 'home.html', context)

@login_required
def trash_view(request):
    """回收站页面"""
    # 只显示已删除的文件
    deleted_files = File.objects.filter(user=request.user, is_deleted=True).order_by('-deleted_at')
    
    # 文件统计
    file_stats = {
        'all': File.objects.filter(user=request.user, is_deleted=False).count(),
        'image': File.objects.filter(user=request.user, file_type='image', is_deleted=False).count(),
        'document': File.objects.filter(user=request.user, file_type='document', is_deleted=False).count(),
        'video': File.objects.filter(user=request.user, file_type='video', is_deleted=False).count(),
        'audio': File.objects.filter(user=request.user, file_type='audio', is_deleted=False).count(),
        'other': File.objects.filter(user=request.user, file_type='other', is_deleted=False).count(),
        'trash': deleted_files.count()  # 回收站文件数量
    }
    
    # 计算存储使用情况
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    storage_used = user_profile.storage_used
    storage_limit = user_profile.storage_limit
    storage_percent = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
    
    context = {
        'user': request.user,
        'files': deleted_files,
        'file_stats': file_stats,
        'storage_used': storage_used,
        'storage_limit': storage_limit,
        'storage_percent': storage_percent,
        'current_type': 'trash'
    }
    return render(request, 'trash.html', context)

@login_required
def upload_file(request):
    """上传文件"""
     # 检查文件大小限制
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        if user_profile.storage_used + uploaded_file.size > user_profile.storage_limit:
            messages.error(request, '存储空间不足，无法上传文件！')
            return redirect('disk:home')
        try:
            # 保存到Swift存储
            storage = SwiftStorage(user=request.user)
            file_name = uploaded_file.name

            # 处理重名文件
            base_name, extension = os.path.splitext(file_name)
            counter = 1
            while File.objects.filter(user=request.user, name=file_name, is_deleted=False).exists():
                file_name = f"{base_name}({counter}){extension}"
                counter += 1

            # 保存到Swift
            storage._save(file_name, uploaded_file)

            # 创建文件记录
            file_obj = File.objects.create(
                user=request.user,
                name=file_name,
                size=uploaded_file.size,
                file=file_name
            )

            # 更新用户存储使用量
            user_profile.storage_used += uploaded_file.size
            user_profile.save()

            messages.success(request, f'文件 "{file_name}" 上传成功！')
        except Exception as e:
            messages.error(request, f'文件上传失败：{str(e)}')
    return redirect('disk:home')

@login_required
def download_file(request, file_id):
    """下载文件"""
    file_obj = get_object_or_404(File, id=file_id, user=request.user, is_deleted=False)
    
    try:
        storage = SwiftStorage(user=request.user)
        file_content = storage._open(file_obj.name)
        
        if file_content:
            response = HttpResponse(file_content, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
            return response
        else:
            messages.error(request, '文件下载失败！')
    except Exception as e:
        messages.error(request, f'文件下载失败：{str(e)}')
    
    return redirect('disk:home')

@login_required
def delete_file(request, file_id):
    """删除文件 - 移动到回收站（软删除）"""
    file_obj = get_object_or_404(File, id=file_id, user=request.user, is_deleted=False)
    
    try:
        # 软删除 - 标记为已删除，但不从存储中删除
        file_obj.is_deleted = True
        file_obj.deleted_at = timezone.now()
        file_obj.save()
        
        messages.success(request, f'文件 "{file_obj.name}" 已移动到回收站')
    except Exception as e:
        messages.error(request, f'删除文件失败：{str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'disk:home'))

@login_required
def restore_file(request, file_id):
    """从回收站恢复文件"""
    file_obj = get_object_or_404(File, id=file_id, user=request.user, is_deleted=True)
    
    try:
        # 恢复文件
        file_obj.is_deleted = False
        file_obj.deleted_at = None
        file_obj.save()
        
        messages.success(request, f'文件 "{file_obj.name}" 已恢复')
    except Exception as e:
        messages.error(request, f'恢复文件失败：{str(e)}')
    
    return redirect('disk:trash')

@login_required
def permanent_delete_file(request, file_id):
    """永久删除文件 - 从Swift存储和数据库中删除"""
    file_obj = get_object_or_404(File, id=file_id, user=request.user, is_deleted=True)
    
    try:
        # 从Swift存储中删除文件
        storage = SwiftStorage(user=request.user)
        if storage.exists(file_obj.name):
            storage.delete(file_obj.name)
        
        # 更新用户存储使用量
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.storage_used = max(0, user_profile.storage_used - file_obj.size)
        user_profile.save()
        
        # 从数据库中删除文件记录
        file_name = file_obj.name
        file_obj.delete()
        
        messages.success(request, f'文件 "{file_name}" 已永久删除')
    except Exception as e:
        messages.error(request, f'永久删除文件失败：{str(e)}')
    
    return redirect('disk:trash')

@login_required
def empty_trash(request):
    """清空回收站"""
    if request.method == 'POST':
        deleted_files = File.objects.filter(user=request.user, is_deleted=True)
        total_size = 0
        deleted_count = 0
        
        try:
            storage = SwiftStorage(user=request.user)
            
            for file_obj in deleted_files:
                # 从Swift存储中删除文件
                if storage.exists(file_obj.name):
                    storage.delete(file_obj.name)
                
                total_size += file_obj.size
                deleted_count += 1
            
            # 批量删除数据库记录
            deleted_files.delete()
            
            # 更新用户存储使用量
            user_profile = UserProfile.objects.get(user=request.user)
            user_profile.storage_used = max(0, user_profile.storage_used - total_size)
            user_profile.save()
            
            messages.success(request, f'回收站已清空，共删除 {deleted_count} 个文件')
        except Exception as e:
            messages.error(request, f'清空回收站失败：{str(e)}')
    
    return redirect('disk:trash')

@login_required
def images_view(request):
    """图片文件视图"""
    files = File.objects.filter(user=request.user, file_type='image', is_deleted=False).order_by('-upload_time')
    
    # 文件统计
    file_stats = {
        'all': File.objects.filter(user=request.user, is_deleted=False).count(),
        'image': files.count(),
        'document': File.objects.filter(user=request.user, file_type='document', is_deleted=False).count(),
        'video': File.objects.filter(user=request.user, file_type='video', is_deleted=False).count(),
        'audio': File.objects.filter(user=request.user, file_type='audio', is_deleted=False).count(),
        'other': File.objects.filter(user=request.user, file_type='other', is_deleted=False).count(),
        'trash': File.objects.filter(user=request.user, is_deleted=True).count()
    }
    
    # 计算存储使用情况
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    storage_used = user_profile.storage_used
    storage_limit = user_profile.storage_limit
    storage_percent = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
    
    context = {
        'user': request.user,
        'files': files,
        'file_stats': file_stats,
        'storage_used': storage_used,
        'storage_limit': storage_limit,
        'storage_percent': storage_percent,
        'current_type': 'image'
    }
    return render(request, 'home.html', context)

@login_required
def documents_view(request):
    """文档文件视图"""
    files = File.objects.filter(user=request.user, file_type='document', is_deleted=False).order_by('-upload_time')
    
    # 文件统计
    file_stats = {
        'all': File.objects.filter(user=request.user, is_deleted=False).count(),
        'image': File.objects.filter(user=request.user, file_type='image', is_deleted=False).count(),
        'document': files.count(),
        'video': File.objects.filter(user=request.user, file_type='video', is_deleted=False).count(),
        'audio': File.objects.filter(user=request.user, file_type='audio', is_deleted=False).count(),
        'other': File.objects.filter(user=request.user, file_type='other', is_deleted=False).count(),
        'trash': File.objects.filter(user=request.user, is_deleted=True).count()
    }
    
    # 计算存储使用情况
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    storage_used = user_profile.storage_used
    storage_limit = user_profile.storage_limit
    storage_percent = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
    
    context = {
        'user': request.user,
        'files': files,
        'file_stats': file_stats,
        'storage_used': storage_used,
        'storage_limit': storage_limit,
        'storage_percent': storage_percent,
        'current_type': 'document'
    }
    return render(request, 'home.html', context)

@login_required
def videos_view(request):
    """视频文件视图"""
    files = File.objects.filter(user=request.user, file_type='video', is_deleted=False).order_by('-upload_time')
    
    # 文件统计
    file_stats = {
        'all': File.objects.filter(user=request.user, is_deleted=False).count(),
        'image': File.objects.filter(user=request.user, file_type='image', is_deleted=False).count(),
        'document': File.objects.filter(user=request.user, file_type='document', is_deleted=False).count(),
        'video': files.count(),
        'audio': File.objects.filter(user=request.user, file_type='audio', is_deleted=False).count(),
        'other': File.objects.filter(user=request.user, file_type='other', is_deleted=False).count(),
        'trash': File.objects.filter(user=request.user, is_deleted=True).count()
    }
    
    # 计算存储使用情况
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    storage_used = user_profile.storage_used
    storage_limit = user_profile.storage_limit
    storage_percent = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
    
    context = {
        'user': request.user,
        'files': files,
        'file_stats': file_stats,
        'storage_used': storage_used,
        'storage_limit': storage_limit,
        'storage_percent': storage_percent,
        'current_type': 'video'
    }
    return render(request, 'home.html', context)

@login_required
def audios_view(request):
    """音频文件视图"""
    files = File.objects.filter(user=request.user, file_type='audio', is_deleted=False).order_by('-upload_time')
    
    # 文件统计
    file_stats = {
        'all': File.objects.filter(user=request.user, is_deleted=False).count(),
        'image': File.objects.filter(user=request.user, file_type='image', is_deleted=False).count(),
        'document': File.objects.filter(user=request.user, file_type='document', is_deleted=False).count(),
        'video': File.objects.filter(user=request.user, file_type='video', is_deleted=False).count(),
        'audio': files.count(),
        'other': File.objects.filter(user=request.user, file_type='other', is_deleted=False).count(),
        'trash': File.objects.filter(user=request.user, is_deleted=True).count()
    }
    
    # 计算存储使用情况
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    storage_used = user_profile.storage_used
    storage_limit = user_profile.storage_limit
    storage_percent = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
    
    context = {
        'user': request.user,
        'files': files,
        'file_stats': file_stats,
        'storage_used': storage_used,
        'storage_limit': storage_limit,
        'storage_percent': storage_percent,
        'current_type': 'audio'
    }
    return render(request, 'home.html', context)

@login_required
def others_view(request):
    """其他文件视图"""
    files = File.objects.filter(user=request.user, file_type='other', is_deleted=False).order_by('-upload_time')
    
    # 文件统计
    file_stats = {
        'all': File.objects.filter(user=request.user, is_deleted=False).count(),
        'image': File.objects.filter(user=request.user, file_type='image', is_deleted=False).count(),
        'document': File.objects.filter(user=request.user, file_type='document', is_deleted=False).count(),
        'video': File.objects.filter(user=request.user, file_type='video', is_deleted=False).count(),
        'audio': File.objects.filter(user=request.user, file_type='audio', is_deleted=False).count(),
        'other': files.count(),
        'trash': File.objects.filter(user=request.user, is_deleted=True).count()
    }
    
    # 计算存储使用情况
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    storage_used = user_profile.storage_used
    storage_limit = user_profile.storage_limit
    storage_percent = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
    
    context = {
        'user': request.user,
        'files': files,
        'file_stats': file_stats,
        'storage_used': storage_used,
        'storage_limit': storage_limit,
        'storage_percent': storage_percent,
        'current_type': 'other'
    }
    return render(request, 'home.html', context)
    """清空回收站"""
    deleted_files = File.objects.filter(user=request.user, is_deleted=True)
    total_size = 0
    deleted_count = 0
    
    try:
        storage = SwiftStorage(user=request.user)
        
        for file in deleted_files:
            # 从Swift存储中删除文件
            if storage.exists(file.name):
                storage.delete(file.name)
            
            total_size += file.size
            deleted_count += 1
        
        # 批量删除数据库记录
        deleted_files.delete()
        
        # 更新用户存储使用量
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.storage_used = max(0, user_profile.storage_used - total_size)
        user_profile.save()
        
        messages.success(request, f'回收站已清空，共删除 {deleted_count} 个文件')
    except Exception as e:
        messages.error(request, f'清空回收站失败: {str(e)}')
    
    return redirect('disk:trash')