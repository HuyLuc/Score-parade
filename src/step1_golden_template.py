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
from src.utils.tracking import track_people_in_video


def create_golden_template(
    video_path: Path,
    output_dir: Path = None,
    template_name: str = "default",
    camera_angle: str = None,
    multi_person: bool = None
) -> dict:
    """
    Tạo golden template từ video mẫu (hỗ trợ nhiều người và góc quay)
    
    Args:
        video_path: Đường dẫn đến video mẫu chuẩn
        output_dir: Thư mục output (mặc định: data/golden_template)
        template_name: Tên template (mặc định: "default")
        camera_angle: Góc quay (front, side, back, diagonal) - mặc định từ config
        multi_person: Có xử lý nhiều người không (mặc định từ config)
        
    Returns:
        Dict chứa thông tin về golden template
    """
    # Sử dụng config mặc định nếu không chỉ định
    if multi_person is None:
        multi_person = config.GOLDEN_TEMPLATE_CONFIG["support_multi_person"]
    if camera_angle is None:
        camera_angle = config.GOLDEN_TEMPLATE_CONFIG["default_camera_angle"]
    
    # Tạo thư mục template riêng nếu có tên
    if template_name != "default":
        template_dir = config.GOLDEN_TEMPLATE_DIR / template_name
    else:
        template_dir = config.GOLDEN_TEMPLATE_DIR
    
    if output_dir is None:
        output_dir = template_dir
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Kiểm tra video hợp lệ
    is_valid, error_msg = validate_video(video_path)
    if not is_valid:
        raise ValueError(f"Video không hợp lệ: {error_msg}")
    
    print(f"Đang xử lý video mẫu: {video_path}")
    print(f"Template: {template_name}, Góc quay: {camera_angle}, Nhiều người: {multi_person}")
    
    # Khởi tạo pose estimator
    estimator = PoseEstimator()
    
    # Load video
    cap, metadata = load_video(video_path)
    
    # Trích xuất skeleton cho từng frame
    skeletons_per_frame = []
    frames = []
    
    print("Đang trích xuất skeleton...")
    for frame in tqdm(get_frames(cap), total=metadata["frame_count"]):
        frames.append(frame.copy())
        
        # Dự đoán pose cho tất cả người trong frame
        keypoints_list = estimator.predict(frame)
        skeletons_per_frame.append(keypoints_list)
    
    cap.release()
    
    # Xử lý theo chế độ: nhiều người hoặc một người
    if multi_person:
        # Tracking để phân biệt từng người
        print("Đang tracking nhiều người...")
        tracked_people = track_people_in_video(skeletons_per_frame)
        
        print(f"Đã track được {len(tracked_people)} người")
        
        # Tạo mapping: frame -> person_id để visualization
        frame_to_person = {}  # {frame_idx: person_id}
        for person_id, keypoints_sequence in tracked_people.items():
            # Tìm frame tương ứng (cần track lại để biết mapping chính xác)
            # Tạm thời: giả sử keypoints_sequence có cùng thứ tự với frames
            for frame_idx in range(len(keypoints_sequence)):
                if frame_idx not in frame_to_person:
                    frame_to_person[frame_idx] = person_id
        
        # Lưu skeleton cho từng người
        result = {
            'template_name': template_name,
            'camera_angle': camera_angle,
            'metadata': metadata,
            'video_path': str(video_path),
            'people': {}
        }
        
        for person_id, keypoints_sequence in tracked_people.items():
            person_dir = output_dir / f"person_{person_id}"
            person_dir.mkdir(parents=True, exist_ok=True)
            
            # Lưu skeleton cho người này
            skeleton_path = person_dir / f"skeleton.pkl"
            with open(skeleton_path, 'wb') as f:
                pickle.dump({
                    'person_id': person_id,
                    'keypoints': keypoints_sequence,
                    'metadata': metadata,
                    'camera_angle': camera_angle,
                    'template_name': template_name
                }, f)
            
            # Tạo visualization cho người này
            vis_path = person_dir / f"visualization.mp4"
            create_visualization_video_single_person(
                frames, skeletons_per_frame, person_id, 
                tracked_people, vis_path, metadata
            )
            
            result['people'][person_id] = {
                'skeleton_path': str(skeleton_path),
                'vis_path': str(vis_path),
                'num_frames': len(keypoints_sequence)
            }
            
            print(f"  ✓ Người {person_id}: {len(keypoints_sequence)} frames")
        
        # Lưu metadata tổng hợp
        metadata_path = output_dir / "metadata.json"
        import json
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\nĐã lưu metadata: {metadata_path}")
        
    else:
        # Chế độ cũ: chỉ lấy người đầu tiên
        skeletons = []
        for keypoints_list in skeletons_per_frame:
            if len(keypoints_list) > 0:
                skeletons.append(keypoints_list[0])
            else:
                skeletons.append(None)
        
        # Lọc bỏ các frame không có skeleton
        valid_skeletons = [s for s in skeletons if s is not None]
        if len(valid_skeletons) == 0:
            raise ValueError("Không tìm thấy skeleton nào trong video!")
        
        # Lưu skeleton data (format cũ để tương thích)
        skeleton_path = output_dir / config.GOLDEN_SKELETON_NAME
        with open(skeleton_path, 'wb') as f:
            pickle.dump({
                'skeletons': skeletons,
                'valid_skeletons': valid_skeletons,
                'metadata': metadata,
                'video_path': str(video_path),
                'camera_angle': camera_angle
            }, f)
        
        print(f"Đã lưu skeleton data: {skeleton_path}")
        
        # Tạo visualization video
        vis_path = output_dir / config.GOLDEN_VIS_NAME
        create_visualization_video(frames, skeletons, vis_path, metadata)
        print(f"Đã tạo visualization video: {vis_path}")
        
        result = {
            'skeleton_path': skeleton_path,
            'vis_path': vis_path,
            'metadata': metadata,
            'num_frames': len(skeletons),
            'num_valid_frames': len(valid_skeletons),
            'camera_angle': camera_angle
        }
    
    return result


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


def create_visualization_video_single_person(
    frames: list,
    skeletons_per_frame: list,
    person_id: int,
    tracked_people: dict,
    output_path: Path,
    metadata: dict
):
    """
    Tạo video visualization cho một người cụ thể
    """
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(
        str(output_path),
        fourcc,
        metadata['fps'],
        (metadata['width'], metadata['height'])
    )
    
    connections = [
        (0, 1), (0, 2), (1, 3), (2, 4),
        (5, 6),
        (5, 7), (7, 9),
        (6, 8), (8, 10),
        (5, 11), (6, 12),
        (11, 12),
        (11, 13), (13, 15),
        (12, 14), (14, 16),
    ]
    
    # Lấy keypoints sequence của person này
    if person_id not in tracked_people:
        print(f"⚠️  Không tìm thấy person_id {person_id} trong tracked_people")
        out.release()
        return
    
    person_keypoints = tracked_people[person_id]
    
    # Vẽ skeleton của người này qua các frame
    for frame_idx, frame in enumerate(frames):
        vis_frame = frame.copy()
        
        # Lấy keypoints của person này tại frame này (nếu có)
        if frame_idx < len(person_keypoints):
            skeleton = person_keypoints[frame_idx]
            
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
                
                # Vẽ label
                if len(skeleton) > 0 and skeleton[0][2] > 0:
                    cv2.putText(vis_frame, f"Person {person_id}", 
                              (int(skeleton[0][0]) + 10, int(skeleton[0][1]) - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        out.write(vis_frame)
    
    out.release()


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Tạo golden template")
    parser.add_argument('video_path', type=str, help='Đường dẫn video')
    parser.add_argument('--template-name', type=str, default='default', 
                       help='Tên template (mặc định: default)')
    parser.add_argument('--camera-angle', type=str, 
                       choices=['front', 'side', 'back', 'diagonal'],
                       default=None, help='Góc quay camera')
    parser.add_argument('--multi-person', action='store_true',
                       help='Xử lý nhiều người trong video')
    parser.add_argument('--single-person', action='store_true',
                       help='Chỉ lấy người đầu tiên (chế độ cũ)')
    
    args = parser.parse_args()
    
    video_path = Path(args.video_path)
    if not video_path.exists():
        # Thử tìm trong golden_template directory
        video_path = config.GOLDEN_TEMPLATE_DIR / args.video_path
        if not video_path.exists():
            print(f"Không tìm thấy video: {args.video_path}")
            sys.exit(1)
    
    multi_person = None
    if args.multi_person:
        multi_person = True
    elif args.single_person:
        multi_person = False
    
    try:
        result = create_golden_template(
            video_path,
            template_name=args.template_name,
            camera_angle=args.camera_angle,
            multi_person=multi_person
        )
        print("\n✅ Hoàn thành Bước 1!")
        
        if 'people' in result:
            print(f"\nTemplate: {result['template_name']}")
            print(f"Góc quay: {result['camera_angle']}")
            print(f"Số người: {len(result['people'])}")
            for person_id, info in result['people'].items():
                print(f"  - Người {person_id}: {info['num_frames']} frames")
        else:
            print(f"Skeleton data: {result['skeleton_path']}")
            print(f"Visualization: {result['vis_path']}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

