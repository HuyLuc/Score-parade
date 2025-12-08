"""
BƯỚC 3: XỬ LÝ VIDEO MỚI (TÂN BINH / NHÓM)

Xử lý video đầu vào, trích skeleton cho nhiều người và tracking.
"""
import pickle
import numpy as np
from pathlib import Path
from tqdm import tqdm
import src.config as config
from src.utils.video_utils import load_video, get_frames, validate_video
from src.utils.pose_estimation import PoseEstimator
from src.utils.tracking import track_people_in_video
from src.utils.smoothing import smooth_keypoints_sequence
from src.utils.motion_filter import filter_people_by_motion


def process_video(
    video_path: Path,
    output_dir: Path = None
) -> dict:
    """
    Xử lý video mới, trích skeleton và tracking cho nhiều người
    
    Args:
        video_path: Đường dẫn video đầu vào
        output_dir: Thư mục output (mặc định: data/output/{video_name})
        
    Returns:
        Dict chứa thông tin về kết quả xử lý
    """
    # Kiểm tra video hợp lệ
    is_valid, error_msg = validate_video(video_path)
    if not is_valid:
        raise ValueError(f"Video không hợp lệ: {error_msg}")
    
    # Tạo output directory
    video_name = video_path.stem
    if output_dir is None:
        output_dir = config.OUTPUT_DIR / video_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Đang xử lý video: {video_path}")
    print(f"Output directory: {output_dir}")
    
    # Khởi tạo pose estimator
    estimator = PoseEstimator()
    
    # Load video
    cap, metadata = load_video(video_path)
    
    # Trích xuất skeleton cho từng frame
    skeletons_per_frame = []
    
    print("Đang trích xuất skeleton...")
    for frame in tqdm(get_frames(cap), total=metadata["frame_count"]):
        keypoints_list = estimator.predict(frame)
        skeletons_per_frame.append(keypoints_list)
    
    cap.release()
    
    print(f"Đã trích xuất skeleton cho {len(skeletons_per_frame)} frames")
    
    # Tracking nhiều người
    print("Đang tracking nhiều người...")
    tracked_people = track_people_in_video(skeletons_per_frame)
    
    print(f"Đã track được {len(tracked_people)} người")
    
    # Filter người có động tác tương tự golden template
    golden_skeleton_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_SKELETON_NAME
    tracked_people = filter_people_by_motion(tracked_people, golden_skeleton_path)
    
    if len(tracked_people) == 0:
        print("\n⚠️  Cảnh báo: Không có người nào có động tác tương tự golden template!")
        print("Có thể cần điều chỉnh MOTION_FILTER_CONFIG trong config.py")
    
    # Làm mượt skeleton cho từng người
    print("Đang làm mượt skeleton...")
    smoothed_people = {}
    for person_id, keypoints_sequence in tracked_people.items():
        # keypoints_sequence: [n_frames, 17, 3]
        smoothed = smooth_keypoints_sequence(keypoints_sequence)
        smoothed_people[person_id] = smoothed
    
    # Lưu skeleton data cho từng người
    saved_files = {}
    for person_id, smoothed_keypoints in smoothed_people.items():
        output_file = output_dir / f"person_{person_id}_skeleton.pkl"
        with open(output_file, 'wb') as f:
            pickle.dump({
                'person_id': person_id,
                'keypoints': smoothed_keypoints,
                'metadata': metadata,
                'video_path': str(video_path)
            }, f)
        saved_files[person_id] = output_file
        print(f"Đã lưu skeleton cho người {person_id}: {output_file}")
    
    # Lưu metadata tổng hợp
    summary = {
        'video_path': str(video_path),
        'video_name': video_name,
        'metadata': metadata,
        'num_people': len(tracked_people),
        'person_ids': list(tracked_people.keys()),
        'skeleton_files': {str(k): str(v) for k, v in saved_files.items()}
    }
    
    summary_path = output_dir / "processing_summary.json"
    import json
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Hoàn thành Bước 3!")
    print(f"Đã xử lý {len(tracked_people)} người")
    print(f"Summary: {summary_path}")
    
    return summary


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python step3_process_video.py <video_path>")
        print(f"Hoặc đặt video vào: {config.INPUT_VIDEOS_DIR}")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        # Thử tìm trong input_videos directory
        video_path = config.INPUT_VIDEOS_DIR / sys.argv[1]
        if not video_path.exists():
            print(f"Không tìm thấy video: {sys.argv[1]}")
            sys.exit(1)
    
    try:
        result = process_video(video_path)
        print(f"\nKết quả:")
        for person_id in result['person_ids']:
            print(f"  - Người {person_id}: {result['skeleton_files'][str(person_id)]}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

