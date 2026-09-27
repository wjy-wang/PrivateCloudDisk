# disk/debug_files.py
from disk.models import File

def debug_file_types():
    """调试文件类型分类"""
    print("=== 文件类型调试 ===")
    
    files = File.objects.all()
    print(f"总文件数: {files.count()}")
    
    type_count = {
        'image': 0,
        'document': 0,
        'video': 0,
        'audio': 0,
        'other': 0
    }
    
    for file in files:
        print(f"文件: {file.name} -> 类型: {file.file_type}")
        if file.file_type in type_count:
            type_count[file.file_type] += 1
    
    print("\n=== 类型统计 ===")
    for file_type, count in type_count.items():
        print(f"{file_type}: {count}")

if __name__ == "__main__":
    debug_file_types()