# disk/update_file_types.py
from disk.models import File

def update_existing_file_types():
    """更新现有文件的文件类型"""
    files = File.objects.all()
    updated_count = 0
    
    for file in files:
        old_type = file.file_type
        new_type = file.get_file_type()
        
        if old_type != new_type:
            file.file_type = new_type
            file.save()
            updated_count += 1
            print(f"更新文件: {file.name} - {old_type} -> {new_type}")
    
    print(f"共更新了 {updated_count} 个文件的类型")

if __name__ == "__main__":
    update_existing_file_types()