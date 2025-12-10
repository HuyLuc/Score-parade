"""
Script helper để quản lý golden templates (nhiều người, nhiều góc quay)
"""
import json
import argparse
from pathlib import Path
import src.config as config


def list_templates():
    """Liệt kê tất cả templates"""
    template_dir = config.GOLDEN_TEMPLATE_DIR
    
    # Tìm các template (có metadata.json)
    templates = []
    for item in template_dir.iterdir():
        if item.is_dir():
            metadata_path = item / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                templates.append({
                    'name': item.name,
                    'path': item,
                    'metadata': metadata
                })
    
    # Template cũ (format cũ)
    old_skeleton = template_dir / config.GOLDEN_SKELETON_NAME
    if old_skeleton.exists():
        templates.append({
            'name': 'default (old format)',
            'path': template_dir,
            'metadata': {'type': 'old_format'}
        })
    
    return templates


def show_template_info(template_name: str):
    """Hiển thị thông tin template"""
    if template_name == "default" or template_name == "old":
        template_dir = config.GOLDEN_TEMPLATE_DIR
        skeleton_path = template_dir / config.GOLDEN_SKELETON_NAME
        profile_path = template_dir / config.GOLDEN_PROFILE_NAME
        
        print(f"Template: default (format cũ)")
        print(f"Skeleton: {skeleton_path.exists()}")
        print(f"Profile: {profile_path.exists()}")
    else:
        template_dir = config.GOLDEN_TEMPLATE_DIR / template_name
        metadata_path = template_dir / "metadata.json"
        
        if not metadata_path.exists():
            print(f"❌ Không tìm thấy template: {template_name}")
            return
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        print(f"Template: {metadata.get('template_name', template_name)}")
        print(f"Góc quay: {metadata.get('camera_angle', 'unknown')}")
        print(f"Số người: {len(metadata.get('people', {}))}")
        
        for person_id, person_info in metadata.get('people', {}).items():
            print(f"\n  Người {person_id}:")
            print(f"    - Frames: {person_info.get('num_frames', 0)}")
            print(f"    - Skeleton: {person_info.get('skeleton_path', 'N/A')}")
            print(f"    - Profile: {Path(person_info.get('skeleton_path', '')).parent / 'profile.json'}")


def main():
    parser = argparse.ArgumentParser(description="Quản lý golden templates")
    parser.add_argument('command', choices=['list', 'info', 'delete'],
                       help='Lệnh: list, info, delete')
    parser.add_argument('--template', type=str, default=None,
                       help='Tên template (cho info/delete)')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        templates = list_templates()
        print(f"\nTìm thấy {len(templates)} template(s):\n")
        for template in templates:
            print(f"  - {template['name']}")
            if 'people' in template.get('metadata', {}):
                print(f"    Số người: {len(template['metadata']['people'])}")
                print(f"    Góc quay: {template['metadata'].get('camera_angle', 'unknown')}")
    
    elif args.command == 'info':
        if not args.template:
            print("❌ Cần chỉ định --template")
            return
        show_template_info(args.template)
    
    elif args.command == 'delete':
        if not args.template:
            print("❌ Cần chỉ định --template")
            return
        if args.template == "default" or args.template == "old":
            print("⚠️  Không thể xóa template mặc định")
            return
        
        template_dir = config.GOLDEN_TEMPLATE_DIR / args.template
        if not template_dir.exists():
            print(f"❌ Không tìm thấy template: {args.template}")
            return
        
        confirm = input(f"Bạn có chắc muốn xóa template '{args.template}'? (yes/no): ")
        if confirm.lower() == 'yes':
            import shutil
            shutil.rmtree(template_dir)
            print(f"✅ Đã xóa template: {args.template}")
        else:
            print("Đã hủy")


if __name__ == "__main__":
    main()

