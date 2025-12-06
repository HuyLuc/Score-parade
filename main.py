"""
Workflow tổng thể cho hệ thống đánh giá điều lệnh quân đội

Chạy tất cả các bước từ 1-7 hoặc chỉ các bước cần thiết.
"""
import sys
from pathlib import Path
import argparse
import src.config as config


def run_step1(video_path: Path):
    """Bước 1: Tạo golden template"""
    print("\n" + "="*50)
    print("BƯỚC 1: TẠO VIDEO MẪU CHUẨN")
    print("="*50)
    from src.step1_golden_template import create_golden_template
    return create_golden_template(video_path)


def run_step2():
    """Bước 2: Trích xuất đặc điểm hình học"""
    print("\n" + "="*50)
    print("BƯỚC 2: TRÍCH XUẤT ĐẶC ĐIỂM HÌNH HỌC")
    print("="*50)
    import pickle
    from src.step2_feature_extraction import extract_features_from_skeleton
    
    skeleton_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_SKELETON_NAME
    with open(skeleton_path, 'rb') as f:
        skeleton_data = pickle.load(f)
    
    return extract_features_from_skeleton(skeleton_data)


def run_step3(video_path: Path):
    """Bước 3: Xử lý video mới"""
    print("\n" + "="*50)
    print("BƯỚC 3: XỬ LÝ VIDEO MỚI")
    print("="*50)
    from src.step3_process_video import process_video
    return process_video(video_path)


def run_step4(video_name: str, person_id: int):
    """Bước 4: Căn chỉnh thời gian"""
    print("\n" + "="*50)
    print("BƯỚC 4: CĂN CHỈNH THỜI GIAN")
    print("="*50)
    from src.step4_temporal_alignment import align_temporal
    
    golden_skeleton_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_SKELETON_NAME
    person_skeleton_path = config.OUTPUT_DIR / video_name / f"person_{person_id}_skeleton.pkl"
    
    return align_temporal(golden_skeleton_path, person_skeleton_path)


def run_step5(video_name: str, person_id: int):
    """Bước 5: So sánh hình học"""
    print("\n" + "="*50)
    print("BƯỚC 5: SO SÁNH HÌNH HỌC")
    print("="*50)
    from src.step5_geometric_matching import compare_with_golden
    
    golden_profile_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_PROFILE_NAME
    aligned_skeleton_path = config.OUTPUT_DIR / video_name / f"person_{person_id}_aligned.pkl"
    golden_skeleton_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_SKELETON_NAME
    
    return compare_with_golden(
        golden_profile_path,
        aligned_skeleton_path,
        golden_skeleton_path
    )


def run_step6(video_name: str, person_id: int):
    """Bước 6: Tính điểm"""
    print("\n" + "="*50)
    print("BƯỚC 6: TÍNH ĐIỂM")
    print("="*50)
    from src.step6_scoring import calculate_score
    
    errors_path = config.OUTPUT_DIR / video_name / f"person_{person_id}_errors.json"
    return calculate_score(errors_path)


def run_step7(video_path: Path, video_name: str, person_id: int):
    """Bước 7: Xuất lỗi và báo cáo"""
    print("\n" + "="*50)
    print("BƯỚC 7: XUẤT LỖI VÀ BÁO CÁO")
    print("="*50)
    from src.step7_visualization import create_visualization
    
    aligned_skeleton_path = config.OUTPUT_DIR / video_name / f"person_{person_id}_aligned.pkl"
    errors_path = config.OUTPUT_DIR / video_name / f"person_{person_id}_errors.json"
    score_path = config.OUTPUT_DIR / video_name / f"person_{person_id}_score.json"
    golden_skeleton_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_SKELETON_NAME
    
    return create_visualization(
        video_path,
        aligned_skeleton_path,
        errors_path,
        score_path,
        golden_skeleton_path
    )


def run_full_pipeline(input_video_path: Path, golden_video_path: Path = None):
    """
    Chạy toàn bộ pipeline
    
    Args:
        input_video_path: Đường dẫn video cần đánh giá
        golden_video_path: Đường dẫn video mẫu chuẩn (nếu chưa có)
    """
    print("\n" + "="*70)
    print("HỆ THỐNG ĐÁNH GIÁ ĐIỀU LỆNH QUÂN ĐỘI")
    print("="*70)
    
    # Kiểm tra golden template đã có chưa
    golden_skeleton_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_SKELETON_NAME
    golden_profile_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_PROFILE_NAME
    
    if not golden_skeleton_path.exists() or not golden_profile_path.exists():
        if golden_video_path is None:
            print("\n❌ Chưa có golden template!")
            print("Vui lòng cung cấp video mẫu chuẩn hoặc chạy step1 và step2 trước.")
            return
        
        # Tạo golden template
        print("\nTạo golden template từ video mẫu...")
        run_step1(golden_video_path)
        run_step2()
    
    # Xử lý video đầu vào
    result_step3 = run_step3(input_video_path)
    video_name = result_step3['video_name']
    person_ids = result_step3['person_ids']
    
    # Xử lý từng người
    for person_id in person_ids:
        print(f"\n{'='*70}")
        print(f"XỬ LÝ NGƯỜI {person_id}")
        print(f"{'='*70}")
        
        # Bước 4: Temporal alignment
        run_step4(video_name, person_id)
        
        # Bước 5: Geometric matching
        run_step5(video_name, person_id)
        
        # Bước 6: Scoring
        run_step6(video_name, person_id)
        
        # Bước 7: Visualization
        run_step7(input_video_path, video_name, person_id)
    
    print("\n" + "="*70)
    print("✅ HOÀN THÀNH TẤT CẢ CÁC BƯỚC!")
    print("="*70)
    print(f"\nKết quả được lưu tại: {config.OUTPUT_DIR / video_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Hệ thống đánh giá điều lệnh quân đội"
    )
    
    parser.add_argument(
        '--mode',
        choices=['full', 'step1', 'step2', 'step3', 'step4', 'step5', 'step6', 'step7'],
        default='full',
        help='Chế độ chạy'
    )
    
    parser.add_argument(
        '--input-video',
        type=str,
        help='Đường dẫn video đầu vào (cho step3 hoặc full)'
    )
    
    parser.add_argument(
        '--golden-video',
        type=str,
        help='Đường dẫn video mẫu chuẩn (cho step1 hoặc full)'
    )
    
    parser.add_argument(
        '--video-name',
        type=str,
        help='Tên video (cho step4-7)'
    )
    
    parser.add_argument(
        '--person-id',
        type=int,
        help='ID người (cho step4-7)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'full':
            if not args.input_video:
                print("❌ Cần --input-video cho mode full")
                sys.exit(1)
            run_full_pipeline(
                Path(args.input_video),
                Path(args.golden_video) if args.golden_video else None
            )
        
        elif args.mode == 'step1':
            if not args.golden_video:
                print("❌ Cần --golden-video cho step1")
                sys.exit(1)
            run_step1(Path(args.golden_video))
        
        elif args.mode == 'step2':
            run_step2()
        
        elif args.mode == 'step3':
            if not args.input_video:
                print("❌ Cần --input-video cho step3")
                sys.exit(1)
            run_step3(Path(args.input_video))
        
        elif args.mode == 'step4':
            if not args.video_name or args.person_id is None:
                print("❌ Cần --video-name và --person-id cho step4")
                sys.exit(1)
            run_step4(args.video_name, args.person_id)
        
        elif args.mode == 'step5':
            if not args.video_name or args.person_id is None:
                print("❌ Cần --video-name và --person-id cho step5")
                sys.exit(1)
            run_step5(args.video_name, args.person_id)
        
        elif args.mode == 'step6':
            if not args.video_name or args.person_id is None:
                print("❌ Cần --video-name và --person-id cho step6")
                sys.exit(1)
            run_step6(args.video_name, args.person_id)
        
        elif args.mode == 'step7':
            if not args.input_video or not args.video_name or args.person_id is None:
                print("❌ Cần --input-video, --video-name và --person-id cho step7")
                sys.exit(1)
            run_step7(Path(args.input_video), args.video_name, args.person_id)
    
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

