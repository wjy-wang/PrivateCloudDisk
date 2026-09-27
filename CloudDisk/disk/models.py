# disk/models.py
from django.db import models
from django.contrib.auth.models import User
import os

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    storage_used = models.BigIntegerField(default=0)
    storage_limit = models.BigIntegerField(default=5368709120)  # 5GB
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    def __str__(self):
        return self.user.username

class File(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    size = models.BigIntegerField()
    upload_time = models.DateTimeField(auto_now_add=True)
    file = models.CharField(max_length=255, default='')
    file_type = models.CharField(max_length=50, default='other')
    
    # 新增回收站相关字段
    is_deleted = models.BooleanField(default=False)  # 标记是否在回收站
    deleted_at = models.DateTimeField(null=True, blank=True)  # 删除时间
    original_path = models.CharField(max_length=500, blank=True)  # 原始路径（可选）
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # 自动设置文件类型
        if not self.file_type or self.file_type == 'other':
            self.file_type = self.get_file_type()
        super().save(*args, **kwargs)
    
    def get_file_type(self):
        """根据文件名获取文件类型"""
        name_lower = self.name.lower()
        
        # 图片类型
        image_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', 
            '.tiff', '.tif', '.svg', '.ico', '.raw', '.heic'
        ]
        # 文档类型
        document_extensions = [
            '.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx', 
            '.xls', '.xlsx', '.csv', '.md', '.rtf', '.odt', 
            '.ods', '.odp', '.pages', '.numbers', '.key'
        ]
        # 视频类型
        video_extensions = [
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', 
            '.webm', '.m4v', '.3gp', '.mpeg', '.mpg', '.rm', 
            '.rmvb', '.vob', '.asf'
        ]
        # 音频类型
        audio_extensions = [
            '.mp3', '.wav', '.aac', '.flac', '.ogg', '.wma', 
            '.m4a', '.ape', '.aiff', '.mid', '.midi', '.amr'
        ]
        
        # 检查图片
        for ext in image_extensions:
            if name_lower.endswith(ext):
                return 'image'
        
        # 检查文档
        for ext in document_extensions:
            if name_lower.endswith(ext):
                return 'document'
        
        # 检查视频
        for ext in video_extensions:
            if name_lower.endswith(ext):
                return 'video'
        
        # 检查音频
        for ext in audio_extensions:
            if name_lower.endswith(ext):
                return 'audio'
        
        return 'other'
    
    def soft_delete(self):
        """软删除 - 移动到回收站"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        """从回收站恢复"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()