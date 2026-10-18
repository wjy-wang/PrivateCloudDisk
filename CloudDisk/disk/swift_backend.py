# disk/swift_backend.py
import swiftclient
from django.core.files.storage import Storage
from django.conf import settings
import os

class SwiftStorage(Storage):
    """支持延迟连接的Swift对象存储后端"""
    
    def __init__(self, user=None, option=None):
        if not option:
            option = getattr(settings, 'SWIFT_OPTIONS', {})
        
        # 基础配置
        self.auth_url = option.get('AUTH_URL')
        self.username = option.get('USERNAME') 
        self.password = option.get('PASSWORD')
        self.project_name = option.get('PROJECT_NAME', 'admin')
        self.region_name = option.get('REGION_NAME', 'RegionOne')
        self.auth_version = option.get('AUTH_VERSION', '3')
        
        print(f"🔧 Swift配置: auth_url={self.auth_url}, user={self.username}")
        
        # 用户特定容器
        self.user = user
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            self.container_name = f"{option.get('CONTAINER_PREFIX', 'user_container')}_{user.id}"
        else:
            self.container_name = option.get('CONTAINER_NAME', 'default')
        
        print(f"🔧 容器名称: {self.container_name}")
        
        # 延迟连接
        self.conn = None
        self._container_created = False
    
    def _ensure_connection(self):
        """确保连接已建立"""
        if self.conn is None:
            try:
                self.conn = swiftclient.Connection(
                    authurl=self.auth_url,
                    user=self.username,
                    key=self.password,
                    auth_version=self.auth_version,
                    tenant_name=self.project_name,
                    os_options={
                        'region_name': self.region_name,
                        'user_domain_name': 'Default',
                        'project_domain_name': 'Default'
                    }
                )
                print(f"✅ Swift连接成功: {self.auth_url}")
                
            except Exception as e:
                print(f"❌ Swift连接失败: {e}")
                raise
        
        if not self._container_created:
            self._ensure_container()
    
    def _ensure_container(self):
        """确保用户容器存在"""
        try:
            # 检查容器是否存在
            self.conn.head_container(self.container_name)
            print(f"✅ 容器已存在: {self.container_name}")
            self._container_created = True
        except swiftclient.ClientException as e:
            # 容器不存在，创建它
            try:
                print(f"🔄 创建新容器: {self.container_name}")
                self.conn.put_container(self.container_name)
                print(f"✅ 容器创建成功: {self.container_name}")
                self._container_created = True
            except Exception as e:
                print(f"❌ 创建容器失败: {e}")
                raise

    def _open(self, name, mode='rb'):
        """打开文件"""
        self._ensure_connection()
        try:
            _, contents = self.conn.get_object(self.container_name, name)
            print(f"✅ 文件打开成功: {name}")
            return contents
        except Exception as e:
            print(f"❌ 打开文件失败: {name}, 错误: {e}")
            return None
    
    def _save(self, name, content):
        """保存文件"""
        self._ensure_connection()
        try:
            # 确保内容是指针位置正确的字节流
            if hasattr(content, 'read'):
                content_data = content.read()
            else:
                content_data = content
            
            self.conn.put_object(
                self.container_name,
                name,
                contents=content_data,
                content_type='application/octet-stream'
            )
            print(f"✅ 文件保存成功: {name}, 大小: {len(content_data)} 字节")
            return name
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            raise IOError(f"无法保存文件 {name}: {str(e)}")
    
    def delete(self, name):
        """删除文件"""
        self._ensure_connection()
        try:
            self.conn.delete_object(self.container_name, name)
            print(f"✅ 文件删除成功: {name}")
        except Exception as e:
            print(f"❌ 删除文件失败: {e}")
            raise IOError(f"无法删除文件 {name}: {str(e)}")
    
    def exists(self, name):
        """检查文件是否存在"""
        self._ensure_connection()
        try:
            self.conn.head_object(self.container_name, name)
            return True
        except swiftclient.ClientException:
            return False
    
    def listdir(self, path=''):
        """列出用户容器中的文件"""
        self._ensure_connection()
        try:
            print(f"🔍 列出容器 '{self.container_name}' 中的文件...")
            _, objects = self.conn.get_container(self.container_name, prefix=path)
            files = []
            for obj in objects:
                file_info = {
                    'name': obj['name'],
                    'size': int(obj['bytes']),
                    'last_modified': obj['last_modified']
                }
                files.append(file_info)
                print(f"📄 找到文件: {file_info}")
            
            print(f"✅ 共找到 {len(files)} 个文件")
            return files
        except Exception as e:
            print(f"❌ 列出文件失败: {e}")
            return []
    
    def size(self, name):
        """获取文件大小"""
        self._ensure_connection()
        try:
            headers = self.conn.head_object(self.container_name, name)
            size = int(headers.get('content-length', 0))
            print(f"📏 文件 {name} 大小: {size} 字节")
            return size
        except Exception as e:
            print(f"❌ 获取文件大小失败: {e}")
            return 0