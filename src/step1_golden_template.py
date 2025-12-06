"""
BƯỚC 1: TẠO VIDEO MẪU CHUẨN (GOLDEN TEMPLATE)

Trích xuất skeleton từ video mẫu chuẩn và lưu lại để dùng làm template.
"""
import pickle
import numpy as np
import cv2
from pathlib import Path
from tqdm import tqdm
import src.config as config
from src.utils.video_utils import load_video, get_frames, save_video, validate_video
from src.utils.pose_estimation import PoseEstimator


def create_golden_template(
    video_path: Path,
    output_dir: Path = None
) -> dict:
    """
    Tạo golden template từ video mẫu
    
    Args:
        video_path: Đường dẫn đến video mẫu chuẩn
        output_dir: Thư mục output (mặc định: data/golden_template)
        
    Returns:
        Dict chứa thông tin về golden template
    """
    if output_dir is None:
        output_dir = config.GOLDEN_TEMPLATE_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Kiểm tra video hợp lệ
    is_valid, error_msg = validate_video(video_path)
    if not is_valid:
        raise ValueError(f"Video không hợp lệ: {error_msg}")
    
    print(f"Đang xử lý video mẫu: {video_path}")
    
    # Khởi tạo pose estimator
    estimator = PoseEstimator()
    
    # Load video
    cap, metadata = load_video(video_path)
    
    # Trích xuất skeleton cho từng frame
    skeletons = []
    frames = []
    
    print("Đang trích xuất skeleton...")
    for frame in tqdm(get_frames(cap), total=metadata["frame_count"]):
        frames.append(frame.copy())
        
        # Dự đoán pose (chỉ lấy người đầu tiên nếu có nhiều người)
        keypoints_list = estimator.predict(frame)
        
        if len(keypoints_list) > 0:
            # Lấy người đầu tiên làm mẫu chuẩn
            keypoints = keypoints_list[0]
            skeletons.append(keypoints)
        else:
            # Nếu không detect được, thêm None
            skeletons.append(None)
    
    cap.release()
    
    # Lọc bỏ các frame không có skeleton
    valid_skeletons = [s for s in skeletons if s is not None]
    if len(valid_skeletons) == 0:
        raise ValueError("Không tìm thấy skeleton nào trong video!")
    
    # Lấy skeleton trung bình hoặc skeleton ở frame giữa làm đại diện
    # Hoặc có thể chọn frame có skeleton tốt nhất
    skeleton_array = np.array(valid_skeletons)
    
    # Lưu skeleton data
    skeleton_path = output_dir / config.GOLDEN_SKELETON_NAME
    with open(skeleton_path, 'wb') as f:
        pickle.dump({
            'skeletons': skeletons,
            'valid_skeletons': valid_skeletons,
            'metadata': metadata,
            'video_path': str(video_path)
        }, f)
    
    print(f"Đã lưu skeleton data: {skeleton_path}")
    
    # Tạo visualization video
    vis_path = output_dir / config.GOLDEN_VIS_NAME
    create_visualization_video(frames, skeletons, vis_path, metadata)
    print(f"Đã tạo visualization video: {vis_path}")
    
    return {
        'skeleton_path': skeleton_path,
        'vis_path': vis_path,
        'metadata': metadata,
        'num_frames': len(skeletons),
        'num_valid_frames': len(valid_skeletons)
    }


def create_visualization_video(
    frames: list,
    skeletons: list,
    output_path: Path,
    metadata: dict
):
    """
    Tạo video visualization với skeleton được vẽ lên
    """
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(
        str(output_path),
        fourcc,
        metadata['fps'],
        (metadata['width'], metadata['height'])
    )
    
    # Định nghĩa connections giữa các keypoints (COCO format)
    connections = [
        (0, 1), (0, 2), (1, 3), (2, 4),  # Head
        (5, 6),  # Shoulders
        (5, 7), (7, 9),  # Left arm
        (6, 8), (8, 10),  # Right arm
        (5, 11), (6, 12),  # Torso
        (11, 12),  # Hips
        (11, 13), (13, 15),  # Left leg
        (12, 14), (14, 16),  # Right leg
    ]
    
    for frame, skeleton in zip(frames, skeletons):
        vis_frame = frame.copy()
        
        if skeleton is not None:
            # Vẽ keypoints
            for i, kpt in enumerate(skeleton):
                if kpt[2] > 0:  # Confidence > 0
                    x, y = int(kpt[0]), int(kpt[1])
                    cv2.circle(vis_frame, (x, y), 5, (0, 255, 0), -1)
            
            # Vẽ connections
            for start_idx, end_idx in connections:
                if (start_idx < len(skeleton) and end_idx < len(skeleton) and
                    skeleton[start_idx][2] > 0 and skeleton[end_idx][2] > 0):
                    pt1 = (int(skeleton[start_idx][0]), int(skeleton[start_idx][1]))
                    pt2 = (int(skeleton[end_idx][0]), int(skeleton[end_idx][1]))
                    cv2.line(vis_frame, pt1, pt2, (0, 255, 0), 2)
        
        out.write(vis_frame)
    
    out.release()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python step1_golden_template.py <video_path>")
        print(f"Hoặc đặt video vào: {config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_VIDEO_NAME}")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        # Thử tìm trong golden_template directory
        video_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_VIDEO_NAME
        if not video_path.exists():
            print(f"Không tìm thấy video: {sys.argv[1]}")
            sys.exit(1)
    
    try:
        result = create_golden_template(video_path)
        print("\n✅ Hoàn thành Bước 1!")
        print(f"Skeleton data: {result['skeleton_path']}")
        print(f"Visualization: {result['vis_path']}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

