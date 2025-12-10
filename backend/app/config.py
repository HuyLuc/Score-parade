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
        "arm_angle": 2.0,  # Trừ điểm cho lỗi góc tay
        "leg_angle": 2.0,  # Trừ điểm cho lỗi góc chân
        "arm_height": 1.5,  # Trừ điểm cho lỗi độ cao tay
        "leg_height": 1.5,  # Trừ điểm cho lỗi độ cao chân
        "head_angle": 1.0,  # Trừ điểm cho lỗi góc đầu
        "torso_stability": 1.0,  # Trừ điểm cho lỗi ổn định thân
        "rhythm": 2.0,  # Trừ điểm cho lỗi nhịp
        "distance": 1.5,  # Trừ điểm cho lỗi khoảng cách
        "speed": 1.5,  # Trừ điểm cho lỗi tốc độ
    },
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

