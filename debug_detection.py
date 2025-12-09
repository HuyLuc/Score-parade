"""
Script debug để kiểm tra pose detection
"""
import cv2
import numpy as np
from pathlib import Path
from src.utils.pose_estimation import PoseEstimator
from src.utils.video_utils import load_video, get_frames
from tqdm import tqdm

video_path = Path("data/input_videos/video1.mp4")
estimator = PoseEstimator()

cap, metadata = load_video(video_path)

detections_per_frame = []
frames_with_detection = 0
frames_without_detection = 0

print("Đang kiểm tra detection cho từng frame...")
print(f"Total frames: {metadata['frame_count']}")

for frame_idx, frame in enumerate(tqdm(get_frames(cap), total=metadata["frame_count"])):
    keypoints_list = estimator.predict(frame)
    
    if len(keypoints_list) > 0:
        frames_with_detection += 1
        detections_per_frame.append((frame_idx, len(keypoints_list), keypoints_list))
    else:
        frames_without_detection += 1

cap.release()

print(f"\n=== KẾT QUẢ ===")
print(f"Frames CÓ detection: {frames_with_detection} ({frames_with_detection/metadata['frame_count']*100:.1f}%)")
print(f"Frames KHÔNG có detection: {frames_without_detection} ({frames_without_detection/metadata['frame_count']*100:.1f}%)")

if frames_with_detection > 0:
    print(f"\nFrames đầu tiên có detection:")
    for frame_idx, n_people, _ in detections_per_frame[:10]:
        print(f"  Frame {frame_idx}: {n_people} người")
    
    print(f"\nFrames cuối cùng có detection:")
    for frame_idx, n_people, _ in detections_per_frame[-10:]:
        print(f"  Frame {frame_idx}: {n_people} người")
