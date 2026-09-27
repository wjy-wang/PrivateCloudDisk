# disk/test_swift_connection.py
from django.conf import settings
from .swift_backend import SwiftStorage
from django.contrib.auth.models import User

def test_swift_connection():
    """测试Swift连接和容器操作"""
    print("=== 开始Swift连接测试 ===")
    
    try:
        # 获取测试用户
        user = User.objects.first()
        if not user:
            print("❌ 没有找到用户，请先创建用户")
            return
        
        print(f"测试用户: {user.username} (ID: {user.id})")
        
        # 创建存储实例
        storage = SwiftStorage(user=user)
        print("✅ SwiftStorage实例创建成功")
        
        # 测试连接
        storage._ensure_connection()
        print("✅ Swift连接成功")
        
        # 测试容器
        storage._ensure_container()
        print(f"✅ 容器 '{storage.container_name}' 准备就绪")
        
        # 列出当前文件
        files = storage.listdir()
        print(f"📁 容器中的文件数量: {len(files)}")
        
        for file in files:
            print(f"  - {file['name']} ({file['size']} bytes)")
            
        # 测试文件上传（可选）
        test_filename = f"test_file_{user.id}.txt"
        test_content = b"This is a test file content."
        
        try:
            storage._save(test_filename, test_content)
            print(f"✅ 测试文件 '{test_filename}' 上传成功")
            
            # 验证文件存在
            if storage.exists(test_filename):
                print(f"✅ 测试文件存在性验证成功")
            
            # 清理测试文件
            storage.delete(test_filename)
            print(f"✅ 测试文件清理成功")
            
        except Exception as e:
            print(f"⚠️ 测试文件操作失败: {e}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_swift_connection()