"""
Cấu hình toàn dự án cho hệ thống đánh giá điều lệnh quân đội
"""
import os
from pathlib import Path

# Đường dẫn gốc của dự án
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Đường dẫn dữ liệu
DATA_DIR = PROJECT_ROOT / "data"
GOLDEN_TEMPLATE_DIR = DATA_DIR / "golden_template"
INPUT_VIDEOS_DIR = DATA_DIR / "input_videos"
OUTPUT_DIR = DATA_DIR / "output"
MODELS_DIR = DATA_DIR / "models"

# Tên file golden template
GOLDEN_VIDEO_NAME = "golden_video.mp4"
GOLDEN_SKELETON_NAME = "golden_skeleton.pkl"
GOLDEN_PROFILE_NAME = "golden_profile.json"
GOLDEN_VIS_NAME = "golden_skeleton_vis.mp4"

# Cấu hình video
VIDEO_CONFIG = {
    "min_resolution": (1280, 720),  # 720p minimum
    "min_fps": 24,  # Giảm xuống 24fps để linh hoạt hơn (24fps là chuẩn phim, 25fps là PAL)
    "strict_validation": False,  # True = reject nếu không đạt, False = chỉ cảnh báo
    "supported_formats": [".mp4", ".avi", ".mov", ".mkv"],
}

# Cấu hình golden template (hỗ trợ nhiều người và góc quay)
GOLDEN_TEMPLATE_CONFIG = {
    "support_multi_person": True,  # Hỗ trợ nhiều người trong một video
    "max_people_per_template": 3,  # Số người tối đa
    "supported_camera_angles": ["front", "side", "back", "diagonal"],  # Các góc quay hỗ trợ
    "auto_select_profile": True,  # Tự động chọn profile phù hợp khi so sánh
    "create_combined_profile": True,  # Tạo profile tổng hợp (trung bình)
    "default_camera_angle": "front",  # Góc quay mặc định
}

# Cấu hình pose estimation
POSE_CONFIG = {
    "model_type": "yolov8",  # rtmpose hoặc yolov8
    "model_path": None,  # Đường dẫn model (None = tự động download)
    "yolov8_model": "yolov8n-pose.pt",  # Tên model YOLOv8 (sẽ tự download)
    "device": "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu",
    "conf_threshold": 0.25,  # Confidence threshold
}

# Cấu hình tracking
TRACKING_CONFIG = {
    "method": "simple",  # simple, oc_sort, byte_track
    "max_age": 30,  # Số frame tối đa để giữ track khi mất detection
    "min_hits": 3,  # Số detection tối thiểu để bắt đầu track
    "iou_threshold": 0.3,  # IoU threshold để match detections
}

# Cấu hình motion filter
MOTION_FILTER_CONFIG = {
    "enabled": True,
    "min_motion_variance": 50.0,  # Variance tối thiểu của vị trí keypoints (pixel^2)
    "min_similarity_score": 0.3,  # Similarity score tối thiểu với golden template (0-1)
    "motion_check_frames": 30,  # Số frame để kiểm tra motion
}

# Cấu hình temporal alignment
ALIGNMENT_CONFIG = {
    "method": "dtw",  # dtw, linear, dynamic
    "warp_window": 10,  # Window size cho DTW
    "smooth_window": 5,  # Window size cho smoothing
}

# Cấu hình scoring
SCORING_CONFIG = {
    "initial_score": 100,  # Điểm ban đầu
    "fail_threshold": 50,  # Điểm tối thiểu để đạt
    "error_weights": {
        "arm_angle": 1.0,  # Giảm từ 2.0 → 1.0 (giảm 50%)
        "leg_angle": 1.0,  # Giảm từ 2.0 → 1.0
        "arm_height": 0.8,  # Giảm từ 1.5 → 0.8
        "leg_height": 0.8,  # Giảm từ 1.5 → 0.8
        "head_angle": 0.5,  # Giảm từ 1.0 → 0.5 (QUAN TRỌNG - giảm 50%)
        "torso_stability": 0.5,  # Giảm từ 1.0 → 0.5
        "rhythm": 1.0,  # Giảm từ 2.0 → 1.0
        "distance": 0.8,  # Giảm từ 1.5 → 0.8
        "speed": 0.8,  # Giảm từ 1.5 → 0.8
    },
}

# Ngưỡng sai lệch mặc định (dùng khi không có std từ golden)
ERROR_THRESHOLDS = {
    "arm_angle": 50.0,  # Tăng từ 30.0 → 50.0 (tăng 67%)
    "leg_angle": 45.0,  # Tăng từ 25.0 → 45.0 (tăng 80%)
    "arm_height": 50.0,  # Tăng từ 30.0 → 50.0
    "leg_height": 45.0,  # Tăng từ 25.0 → 45.0
    "head_angle": 30.0,  # Tăng từ 15.0 → 30.0 (GẤP ĐÔI - QUAN TRỌNG!)
    "torso_stability": 0.85,  # Tăng từ 0.7 → 0.85
    "rhythm": 0.15,  # Rhythm tolerance: 150ms (0.15 seconds)
    "distance": 50.0,  # Tăng từ 30.0 → 50.0
    "speed": 80.0,  # Tăng từ 50.0 → 80.0
}

# Cấu hình database
DATABASE_CONFIG = {
    "url": os.getenv("DATABASE_URL", "postgresql://user:password@localhost/score_parade"),
    "echo": False,  # Log SQL queries
    "pool_size": 5,
    "max_overflow": 10,
}

# Cấu hình API
API_CONFIG = {
    "title": "Score Parade API",
    "version": "1.0.0",
    "docs_url": "/docs",
    "redoc_url": "/redoc",
}

# Cấu hình camera
CAMERA_CONFIG = {
    "max_cameras": 2,
    "default_resolution": (1920, 1080),
    "default_fps": 30,
    "snapshot_interval": 1.0,  # Giây
    "video_chunk_duration": 5.0,  # Giây
}

# Cấu hình motion detection cho Global Mode
MOTION_DETECTION_CONFIG = {
    "step_threshold_y": 20,  # Threshold for ankle Y movement (pixels)
    "step_threshold_x": 15,  # Threshold for ankle X movement (pixels)
    "arm_threshold": 30,     # Threshold for wrist movement (pixels)
    "confidence_threshold": 0.5,  # Minimum confidence for keypoints
    "batch_size": 10,        # Number of motion events before batch processing
}

# Cấu hình normalization cho keypoints
NORMALIZATION_CONFIG = {
    "enabled": True,  # Bật/tắt normalization
    "method": "relative",  # "relative" hoặc "absolute"
    "reference_torso_length": 100.0,  # Chiều dài torso chuẩn (pixels) cho absolute method
    "min_torso_length": 10.0,  # Torso tối thiểu để coi là hợp lệ
    "min_confidence": 0.5,  # Confidence tối thiểu cho keypoints vai/hông
}

# Cấu hình temporal smoothing cho noise reduction
TEMPORAL_SMOOTHING_CONFIG = {
    "enabled": True,  # Bật/tắt temporal smoothing
    # Tăng nhẹ window để giảm nhiễu frame đơn lẻ (giảm false positive giữa A→C)
    "window_size": 7,  # 7 frames @ 30fps ~ 233ms latency
    "method": "moving_average",  # "moving_average" hoặc "median"
    "smooth_keypoints": True,  # Làm mượt keypoint coordinates
    "smooth_metrics": True,  # Làm mượt các metric (góc, chiều cao)
}

# Cấu hình adaptive thresholds dựa trên golden template statistics
ADAPTIVE_THRESHOLD_CONFIG = {
    "enabled": True,  # Bật/tắt adaptive thresholds
    "multiplier": 3.0,  # N-sigma multiplier (3.0 = 99.7% confidence interval)
    "min_ratio": 0.3,   # Minimum threshold = 30% of default
    "max_ratio": 2.0,   # Maximum threshold = 200% of default
    "cache_thresholds": True,  # Cache computed thresholds per session
}

# Cấu hình DTW (Dynamic Time Warping) cho xử lý tempo variation
DTW_CONFIG = {
    "enabled": False,  # Bật/tắt DTW alignment (default: False để tránh ảnh hưởng hệ thống hiện tại)
    "window_size": 50,  # Window size cho DTW alignment
    "distance_metric": "euclidean",  # Distance metric: "euclidean", "manhattan", "cosine"
}

# Sequence Comparison configuration for grouping consecutive errors
SEQUENCE_COMPARISON_CONFIG = {
    "enabled": True,  # Enable/disable sequence-based error detection
    # Yêu cầu lỗi phải kéo dài lâu hơn để tránh phạt vì 1 frame trung gian
    "min_sequence_length": 5,  # Minimum frames to form a sequence
    # Cho phép thiếu 1-2 frame nhưng vẫn coi là cùng sequence (giảm false positive do frame rớt)
    "max_gap_frames": 2,  # Frames gap allowed inside a sequence
    # Dùng median để giảm ảnh hưởng của frame outlier
    "severity_aggregation": "median",  # "mean", "max", "median"
}

# Error Grouping configuration - Nhóm các lỗi liên tiếp để tránh phạt trùng lặp
ERROR_GROUPING_CONFIG = {
    "enabled": True,  # Bật/tắt error grouping
    "min_sequence_length": 5,  # Số frames tối thiểu để coi là một sequence lỗi (default: 5)
    "max_gap_frames": 3,  # Số frames tối đa giữa các lỗi để vẫn coi là cùng sequence (default: 3)
    "severity_aggregation": "mean",  # Cách tính severity: "mean", "max", "median"
    "sequence_deduction": 1.0,  # Điểm trừ cho mỗi sequence lỗi (thay vì trừ từng frame)
    "max_deduction_per_error_type": 10.0,  # Điểm trừ tối đa cho mỗi loại lỗi trong toàn bộ video
}

# Multi-Person Tracking configuration
MULTI_PERSON_CONFIG = {
    "enabled": False,  # Enable/disable multi-person mode (default: False for backward compatibility)
    "max_persons": 10,  # Maximum number of persons to track
    "max_disappeared": 30,  # Max frames before person considered disappeared
    "iou_threshold": 0.5,  # IoU threshold for tracking (0.0-1.0)
    "similarity_threshold": 0.6,  # Pose similarity threshold for matching (0.0-1.0)
    "enable_visualization": True,  # Draw tracking boxes and IDs
    "batch_size": 8,  # Batch size for multi-person detection
}

# Visualization configuration for multi-person tracking
VISUALIZATION_CONFIG = {
    "enabled": True,  # Enable/disable visualization
    "enable_skeleton": True,  # Draw skeleton overlay
    "enable_bbox": True,  # Draw bounding boxes
    "enable_trajectories": True,  # Draw movement trajectories
    "save_visualizations": True,  # Save visualization videos to disk
    "trajectory_length": 30,  # Number of frames to keep in trajectory
}

# Performance optimization configuration
PERFORMANCE_CONFIG = {
    "enable_batch_processing": True,  # Enable batch processing for multi-person
    "batch_size": 8,  # Number of frames to process at once
    "enable_gpu": True,  # Use GPU acceleration if available
    "enable_caching": True,  # Enable result caching
    "num_workers": 4,  # Number of worker threads for parallel processing
}

# Error recovery configuration for tracking
ERROR_RECOVERY_CONFIG = {
    "enable_reidentification": True,  # Enable person re-identification
    "reid_similarity_threshold": 0.7,  # Similarity threshold for re-identification
    "max_disappeared_frames": 60,  # Maximum frames before giving up on re-identification
    "reid_check_interval": 5,  # Check for re-identification every N frames
    "spatial_distance_weight": 0.3,  # Weight for spatial proximity (0-1)
    "pose_similarity_weight": 0.7,  # Weight for pose similarity (0-1)
}

# Video validation configuration
VIDEO_VALIDATION_CONFIG = {
    "enable_validation": True,  # Enable video validation
    "min_resolution": (640, 480),  # Minimum resolution (width, height)
    "min_fps": 15,  # Minimum frames per second
    "max_duration": 600,  # Maximum duration in seconds (10 minutes)
    "check_lighting": True,  # Check lighting quality
    "check_blur": True,  # Check for motion blur
    "check_noise": True,  # Check for noise levels
    "lighting_threshold": 50,  # Minimum average brightness (0-255)
    "blur_threshold": 100,  # Maximum acceptable blur (Laplacian variance)
}

# Progress tracking configuration
PROGRESS_TRACKING_CONFIG = {
    "enable_progress_bar": True,  # Show progress bar
    "show_eta": True,  # Show estimated time remaining
    "show_fps": True,  # Show processing speed
    "update_interval": 1.0,  # Update progress every N seconds
    "bar_length": 50,  # Progress bar length in characters
}

# Caching configuration
CACHING_CONFIG = {
    "enabled": True,  # Enable caching
    "cache_keypoints": True,  # Cache extracted keypoints
    "cache_templates": True,  # Cache golden templates
    "cache_dir": DATA_DIR / "cache",  # Cache directory
    "max_cache_size_mb": 500,  # Maximum cache size in MB
    "cache_expiry_days": 7,  # Cache expiry in days
}

# Định nghĩa keypoints (theo COCO format)
KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]

KEYPOINT_INDICES = {
    "nose": 0,
    "left_eye": 1, "right_eye": 2,
    "left_ear": 3, "right_ear": 4,
    "left_shoulder": 5, "right_shoulder": 6,
    "left_elbow": 7, "right_elbow": 8,
    "left_wrist": 9, "right_wrist": 10,
    "left_hip": 11, "right_hip": 12,
    "left_knee": 13, "right_knee": 14,
    "left_ankle": 15, "right_ankle": 16,
}

