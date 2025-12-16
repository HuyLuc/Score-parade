"""
Script đơn giản để debug detection của YOLOv8
"""
import cv2
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.app.services.pose_estimation import PoseEstimator
from backend.app.config import POSE_CONFIG, MULTI_PERSON_CONFIG


def debug_yolov8_detection(video_path: str, num_frames: int = 100):
    """
    Debug YOLOv8 detection trực tiếp
    """
    print(f"Debugging YOLOv8 on: {video_path}")
    print(f"Config:")
    print(f"  - conf_threshold: {POSE_CONFIG.get('conf_threshold')}")
    print(f"  - keypoint_confidence_threshold: {POSE_CONFIG.get('keypoint_confidence_threshold')}")
    print(f"  - min_valid_keypoints: {POSE_CONFIG.get('min_valid_keypoints')}")
    print(f"  - max_persons: {MULTI_PERSON_CONFIG.get('max_persons')}")
    print("=" * 60)
    
    # Khởi tạo estimator
    estimator = PoseEstimator(model_type="yolov8")
    
    # Mở video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video {video_path}")
        return
    
    frame_num = 0
    detection_counts = []
    
    while frame_num < num_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_num += 1
        
        # Detect
        keypoints_list = estimator.predict(frame)
        detection_counts.append(len(keypoints_list))
        
        if frame_num % 10 == 0 or len(keypoints_list) > 0:
            print(f"Frame {frame_num}: Detected {len(keypoints_list)} persons")
            
            # Show details
            for i, kpts in enumerate(keypoints_list):
                valid_count = (kpts[:, 2] > 0).sum()
                avg_conf = kpts[kpts[:, 2] > 0, 2].mean() if valid_count > 0 else 0
                print(f"  Person {i}: {valid_count} valid keypoints, avg conf: {avg_conf:.3f}")
    
    cap.release()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if detection_counts:
        print(f"Total frames processed: {len(detection_counts)}")
        print(f"Frames with detections: {sum(1 for c in detection_counts if c > 0)}")
        print(f"Average detections per frame: {sum(detection_counts) / len(detection_counts):.2f}")
        print(f"Max detections in a frame: {max(detection_counts)}")
        
        # Histogram
        from collections import Counter
        count_dist = Counter(detection_counts)
        print("\nDetection distribution:")
        for count in sorted(count_dist.keys()):
            print(f"  {count} persons: {count_dist[count]} frames")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_yolov8.py <video_path> [num_frames]")
        print("Example: python debug_yolov8.py ../data/input_videos/test.mp4 100")
        sys.exit(1)
    
    video_path = sys.argv[1]
    num_frames = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    debug_yolov8_detection(video_path, num_frames)
