"""
Script đơn giản để chạy chấm điểm video điều lệnh
Không cần Docker, không cần đăng nhập

Cách sử dụng:
1. Tạo golden template:
   python run_scoring.py create_golden "data/golden_template/golden_video.mp4"

2. Đánh giá video test:
   python run_scoring.py evaluate "data/input_videos/video1.mp4"
"""
import sys
import os
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import từ score_video.py
from score_video import create_golden_template, evaluate_video

def main():
    if len(sys.argv) < 3:
        print("=" * 60)
        print("CHAM DIEM VIDEO DIEU LENH")
        print("=" * 60)
        print("\nCach su dung:")
        print("1. Tao golden template:")
        print('   python run_scoring.py create_golden "duong/dan/video_golden.mp4"')
        print("\n2. Danh gia video test:")
        print('   python run_scoring.py evaluate "duong/dan/video_test.mp4"')
        print("\nVi du:")
        print('   python run_scoring.py create_golden "data/golden_template/golden_video.mp4"')
        print('   python run_scoring.py evaluate "data/input_videos/video1.mp4"')
        print("=" * 60)
        sys.exit(1)
    
    mode = sys.argv[1]
    video_path = Path(sys.argv[2])
    
    if not video_path.exists():
        print(f"❌ Video khong ton tai: {video_path}")
        sys.exit(1)
    
    if mode == "create_golden":
        print("\n" + "=" * 60)
        print("TAO GOLDEN TEMPLATE")
        print("=" * 60)
        create_golden_template(video_path)
        print("\n✅ Hoan tat!")
        
    elif mode == "evaluate":
        print("\n" + "=" * 60)
        print("DANH GIA VIDEO TEST")
        print("=" * 60)
        evaluate_video(video_path)
        print("\n✅ Hoan tat!")
        
    else:
        print(f"❌ Mode khong hop le: {mode}")
        print("   Su dung: create_golden hoac evaluate")
        sys.exit(1)

if __name__ == "__main__":
    main()

