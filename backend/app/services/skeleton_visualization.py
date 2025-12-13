"""
Utility functions for visualizing skeleton/keypoints on video frames
"""
import numpy as np
import cv2
from typing import List, Optional, Tuple

# COCO keypoint format (17 keypoints)
KEYPOINT_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
]

# Skeleton connections (pairs of keypoint indices)
SKELETON_CONNECTIONS = [
    # Head
    (0, 1), (0, 2), (1, 3), (2, 4),  # nose-eyes-ears
    # Torso
    (5, 6),  # shoulders
    (5, 11), (6, 12),  # shoulders to hips
    (11, 12),  # hips
    # Left arm
    (5, 7), (7, 9),  # left shoulder-elbow-wrist
    # Right arm
    (6, 8), (8, 10),  # right shoulder-elbow-wrist
    # Left leg
    (11, 13), (13, 15),  # left hip-knee-ankle
    # Right leg
    (12, 14), (14, 16),  # right hip-knee-ankle
]

# Colors for different body parts (BGR format for OpenCV)
KEYPOINT_COLORS = [
    (255, 0, 0),    # nose - red
    (255, 85, 0),   # left_eye - orange
    (255, 170, 0),  # right_eye - orange
    (255, 255, 0),  # left_ear - yellow
    (170, 255, 0),  # right_ear - yellow-green
    (85, 255, 0),   # left_shoulder - green
    (0, 255, 0),    # right_shoulder - green
    (0, 255, 85),   # left_elbow - green-cyan
    (0, 255, 170),  # right_elbow - cyan
    (0, 255, 255),  # left_wrist - cyan
    (0, 170, 255),  # right_wrist - light blue
    (0, 85, 255),   # left_hip - blue
    (0, 0, 255),    # right_hip - blue
    (85, 0, 255),   # left_knee - purple
    (170, 0, 255),  # right_knee - purple
    (255, 0, 255),  # left_ankle - magenta
    (255, 0, 170),  # right_ankle - pink
]

CONNECTION_COLORS = [
    (255, 0, 0),    # head connections - red
    (0, 255, 0),    # torso - green
    (0, 0, 255),    # left arm - blue
    (255, 255, 0),  # right arm - yellow
    (255, 0, 255),  # left leg - magenta
    (0, 255, 255),  # right leg - cyan
]


def draw_skeleton(
    frame: np.ndarray,
    keypoints: np.ndarray,
    confidence_threshold: float = 0.3,
    keypoint_radius: int = 5,
    connection_thickness: int = 2
) -> np.ndarray:
    """
    Vẽ skeleton lên frame
    
    Args:
        frame: Frame ảnh (BGR format)
        keypoints: Keypoints array [17, 3] với (x, y, confidence)
        confidence_threshold: Ngưỡng confidence để hiển thị keypoint
        keypoint_radius: Bán kính vẽ keypoint
        connection_thickness: Độ dày đường nối
        
    Returns:
        Frame đã được vẽ skeleton
    """
    if keypoints is None or len(keypoints) == 0:
        return frame
    
    # Ensure keypoints is 2D array
    if keypoints.ndim == 1:
        keypoints = keypoints.reshape(-1, 3)
    
    # Make a copy to avoid modifying original
    frame_copy = frame.copy()
    
    # Draw connections first (so they appear behind keypoints)
    for i, (start_idx, end_idx) in enumerate(SKELETON_CONNECTIONS):
        if start_idx >= len(keypoints) or end_idx >= len(keypoints):
            continue
            
        start_kpt = keypoints[start_idx]
        end_kpt = keypoints[end_idx]
        
        # Check confidence
        if (start_kpt[2] < confidence_threshold or 
            end_kpt[2] < confidence_threshold):
            continue
        
        # Get color for this connection
        # Group connections by body part
        if i < 4:  # Head
            color = CONNECTION_COLORS[0]
        elif i < 7:  # Torso
            color = CONNECTION_COLORS[1]
        elif i < 9:  # Left arm
            color = CONNECTION_COLORS[2]
        elif i < 11:  # Right arm
            color = CONNECTION_COLORS[3]
        elif i < 13:  # Left leg
            color = CONNECTION_COLORS[4]
        else:  # Right leg
            color = CONNECTION_COLORS[5]
        
        # Draw line
        pt1 = (int(start_kpt[0]), int(start_kpt[1]))
        pt2 = (int(end_kpt[0]), int(end_kpt[1]))
        cv2.line(frame_copy, pt1, pt2, color, connection_thickness)
    
    # Draw keypoints
    for i, kpt in enumerate(keypoints):
        if kpt[2] < confidence_threshold:
            continue
        
        x, y = int(kpt[0]), int(kpt[1])
        color = KEYPOINT_COLORS[i % len(KEYPOINT_COLORS)]
        
        # Draw filled circle
        cv2.circle(frame_copy, (x, y), keypoint_radius, color, -1)
        # Draw outline
        cv2.circle(frame_copy, (x, y), keypoint_radius, (255, 255, 255), 1)
    
    return frame_copy


def draw_skeletons_multiple_persons(
    frame: np.ndarray,
    keypoints_list: List[np.ndarray],
    confidence_threshold: float = 0.3,
    keypoint_radius: int = 5,
    connection_thickness: int = 2
) -> np.ndarray:
    """
    Vẽ nhiều skeletons (nhiều người) lên frame
    
    Args:
        frame: Frame ảnh (BGR format)
        keypoints_list: List các keypoints arrays, mỗi người một array [17, 3]
        confidence_threshold: Ngưỡng confidence
        keypoint_radius: Bán kính vẽ keypoint
        connection_thickness: Độ dày đường nối
        
    Returns:
        Frame đã được vẽ skeletons
    """
    frame_copy = frame.copy()
    
    for keypoints in keypoints_list:
        frame_copy = draw_skeleton(
            frame_copy,
            keypoints,
            confidence_threshold,
            keypoint_radius,
            connection_thickness
        )
    
    return frame_copy


def create_skeleton_video(
    input_video_path: str,
    output_video_path: str,
    pose_service,
    confidence_threshold: float = 0.3
) -> dict:
    """
    Tạo video mới với skeleton được vẽ lên
    
    Args:
        input_video_path: Đường dẫn video input
        output_video_path: Đường dẫn video output
        pose_service: PoseService instance để predict keypoints
        confidence_threshold: Ngưỡng confidence cho keypoints
        
    Returns:
        Dict với metadata về video đã tạo
    """
    from backend.app.services.video_utils import load_video, get_frames
    from pathlib import Path
    
    # Load video (convert string to Path if needed)
    video_path = Path(input_video_path) if isinstance(input_video_path, str) else input_video_path
    cap, metadata = load_video(video_path)
    fps = metadata.get('fps', 30.0)
    width = metadata.get('width', 640)
    height = metadata.get('height', 480)
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(
        str(output_video_path),
        fourcc,
        fps,
        (width, height)
    )
    
    frame_count = 0
    processed_frames = 0
    
    # Process each frame
    for frame in get_frames(cap):
        frame_count += 1
        
        # Predict keypoints
        keypoints_list = pose_service.predict(frame)
        
        # Draw skeleton if keypoints detected
        if len(keypoints_list) > 0:
            frame_with_skeleton = draw_skeletons_multiple_persons(
                frame,
                keypoints_list,
                confidence_threshold
            )
            processed_frames += 1
        else:
            frame_with_skeleton = frame
        
        # Write frame
        out.write(frame_with_skeleton)
    
    cap.release()
    out.release()
    
    return {
        'total_frames': frame_count,
        'processed_frames': processed_frames,
        'fps': fps,
        'width': width,
        'height': height,
        'output_path': str(output_video_path)
    }

