"""
Script kiểm tra tính tương thích giữa golden template và video test
"""
import cv2
import json
from pathlib import Path

print("="*70)
print("KIỂM TRA TÍNH TƯƠNG THÍCH GOLDEN TEMPLATE VÀ VIDEO TEST")
print("="*70)

# Đọc golden profile
golden_profile_path = Path('data/golden_template/golden_profile.json')
if golden_profile_path.exists():
    with open(golden_profile_path, 'r', encoding='utf-8') as f:
        golden_profile = json.load(f)
    
    print("\n📹 GOLDEN TEMPLATE:")
    print(f"   Resolution: {golden_profile['metadata']['width']}x{golden_profile['metadata']['height']}")
    print(f"   FPS: {golden_profile['metadata']['fps']}")
    print(f"   Duration: {golden_profile['metadata']['duration']:.1f}s")
    print(f"   Frames: {golden_profile['num_frames']}")
    print(f"\n   Arm height (left): {golden_profile['statistics']['arm_height']['left']['mean']:.1f} px")
    print(f"   Arm height (right): {golden_profile['statistics']['arm_height']['right']['mean']:.1f} px")
    print(f"   Arm angle (left): {golden_profile['statistics']['arm_angle']['left']['mean']:.1f}°")
    print(f"   Arm angle (right): {golden_profile['statistics']['arm_angle']['right']['mean']:.1f}°")
else:
    print("\n❌ Không tìm thấy golden profile!")

# Đọc test video info
test_summary_path = Path('data/output/video1/processing_summary.json')
if test_summary_path.exists():
    with open(test_summary_path, 'r', encoding='utf-8') as f:
        test_summary = json.load(f)
    
    print("\n📹 VIDEO TEST:")
    print(f"   Resolution: {test_summary['metadata']['width']}x{test_summary['metadata']['height']}")
    print(f"   FPS: {test_summary['metadata']['fps']}")
    print(f"   Duration: {test_summary['metadata']['duration']:.1f}s")
    print(f"   Frames: {test_summary['metadata']['frame_count']}")
else:
    print("\n❌ Không tìm thấy test summary!")

# Đọc errors
errors_path = Path('data/output/video1/person_0_errors.json')
if errors_path.exists():
    with open(errors_path, 'r', encoding='utf-8') as f:
        errors_data = json.load(f)
    
    summary = errors_data['summary']
    print(f"\n   Arm height (left): {summary['arm_height']['left']['mean']:.1f} px")
    print(f"   Arm height (right): {summary['arm_height']['right']['mean']:.1f} px")
    print(f"   Arm angle (left): {summary['arm_angle']['left']['mean']:.1f}°")
    print(f"   Arm angle (right): {summary['arm_angle']['right']['mean']:.1f}°")
    
    # Phân tích sai lệch
    print("\n" + "="*70)
    print("⚠️  PHÂN TÍCH SAI LỆCH")
    print("="*70)
    
    if golden_profile_path.exists():
        golden_arm_height_left = golden_profile['statistics']['arm_height']['left']['mean']
        test_arm_height_left = summary['arm_height']['left']['mean']
        diff_arm_height = abs(test_arm_height_left - golden_arm_height_left)
        
        golden_arm_angle_left = golden_profile['statistics']['arm_angle']['left']['mean']
        test_arm_angle_left = summary['arm_angle']['left']['mean']
        diff_arm_angle = abs(test_arm_angle_left - golden_arm_angle_left)
        
        print(f"\nArm Height (Left):")
        print(f"   Golden: {golden_arm_height_left:.1f} px")
        print(f"   Test: {test_arm_height_left:.1f} px")
        print(f"   → Sai lệch: {diff_arm_height:.1f} px")
        
        if diff_arm_height > 100:
            print(f"   ❌ SAI LỆCH QUÁ LỚN! (>{100}px)")
            print(f"   → 2 video có thể quay ở góc độ hoàn toàn khác nhau!")
        elif diff_arm_height > 50:
            print(f"   ⚠️  Sai lệch khá lớn (>50px)")
        else:
            print(f"   ✅ OK")
        
        print(f"\nArm Angle (Left):")
        print(f"   Golden: {golden_arm_angle_left:.1f}°")
        print(f"   Test: {test_arm_angle_left:.1f}°")
        print(f"   → Sai lệch: {diff_arm_angle:.1f}°")
        
        if diff_arm_angle > 30:
            print(f"   ❌ SAI LỆCH QUÁ LỚN! (>30°)")
            print(f"   → 2 video có thể là 2 loại điều lệnh khác nhau!")
        elif diff_arm_angle > 15:
            print(f"   ⚠️  Sai lệch khá lớn (>15°)")
        else:
            print(f"   ✅ OK")

# Kết luận
print("\n" + "="*70)
print("📊 KẾT LUẬN")
print("="*70)

if diff_arm_height > 100 or diff_arm_angle > 30:
    print("\n❌ GOLDEN TEMPLATE VÀ VIDEO TEST KHÔNG TƯƠNG THÍCH!")
    print("\n💡 GIẢI PHÁP:")
    print("   1. Kiểm tra xem 2 video có CÙNG LOẠI điều lệnh không")
    print("   2. Kiểm tra xem 2 video có quay ở CÙNG GÓC ĐỘ không")
    print("   3. Nếu khác → TẠO LẠI golden template từ video cùng loại!")
    print("\n   Chạy:")
    print("   python main.py --mode step1 --golden-video data/golden_template/golden_video.mp4")
    print("   python main.py --mode step2")
elif diff_arm_height > 50 or diff_arm_angle > 15:
    print("\n⚠️  GOLDEN TEMPLATE VÀ VIDEO TEST CÓ SAI LỆCH")
    print("\n💡 KHUYẾN NGHỊ:")
    print("   - Kiểm tra lại chất lượng video")
    print("   - Có thể cần tạo lại golden template chính xác hơn")
else:
    print("\n✅ GOLDEN TEMPLATE VÀ VIDEO TEST TƯƠNG THÍCH TỐT!")
    print("\n   Nếu điểm vẫn thấp, có thể do:")
    print("   - Video test thực hiện chưa tốt")
    print("   - Cần điều chỉnh ngưỡng trong config.py")

print("\n" + "="*70)
