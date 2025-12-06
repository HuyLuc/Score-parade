"""
Cấu hình toàn dự án cho hệ thống đánh giá điều lệnh quân đội
"""
import os
from pathlib import Path

# Đường dẫn gốc của dự án
PROJECT_ROOT = Path(__file__).parent.parent

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
    "min_fps": 30,
    "supported_formats": [".mp4", ".avi", ".mov", ".mkv"],
}

# Cấu hình pose estimation
POSE_CONFIG = {
    "model_type": "yolov8",  # "rtmpose" or "yolov8" - mặc định dùng yolov8 (đơn giản hơn)
    "rtmpose_model": "rtmpose-m_8xb256-420e_aic-coco-256x192",  # RTMPose model name
    "yolov8_model": "yolov8n-pose.pt",  # YOLOv8-Pose model (n=nanos, s=small, m=medium, l=large, x=xlarge)
    "confidence_threshold": 0.5,
    "device": "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu",
}

# Cấu hình tracking
TRACKING_CONFIG = {
    "max_age": 30,  # Số frame tối đa một track có thể bị mất
    "min_hits": 3,  # Số frame tối đa để xác nhận một track mới
    "iou_threshold": 0.3,  # Ngưỡng IoU cho matching
    "max_people": 20,  # Số người tối đa trong một video
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

# Các điểm khớp quan trọng cho điều lệnh
IMPORTANT_JOINTS = {
    "arms": {
        "left": ["left_shoulder", "left_elbow", "left_wrist"],
        "right": ["right_shoulder", "right_elbow", "right_wrist"],
    },
    "legs": {
        "left": ["left_hip", "left_knee", "left_ankle"],
        "right": ["right_hip", "right_knee", "right_ankle"],
    },
    "torso": ["left_shoulder", "right_shoulder", "left_hip", "right_hip"],
    "head": ["nose", "left_ear", "right_ear"],
}

# Cấu hình smoothing
SMOOTHING_CONFIG = {
    "method": "savgol",  # "savgol" (Savitzky-Golay) or "moving_average"
    "window_length": 11,  # Độ dài cửa sổ (phải là số lẻ)
    "polyorder": 3,  # Bậc đa thức cho Savitzky-Golay
}

# Ngưỡng sai lệch (cần điều chỉnh dựa trên thực tế)
ERROR_THRESHOLDS = {
    "arm_angle": 5.0,  # Độ
    "leg_angle": 3.0,  # Độ
    "arm_height": 10.0,  # cm (cần scale từ pixel)
    "leg_height": 5.0,  # cm
    "head_angle": 2.0,  # Độ
    "torso_stability": 5.0,  # cm (variance của vị trí hông)
    "step_rhythm": 0.1,  # 10% sai lệch nhịp
}

# Trọng số tính điểm
SCORING_WEIGHTS = {
    "arm_technique": 0.30,  # Kỹ thuật tay: 30%
    "leg_technique": 0.30,  # Kỹ thuật chân: 30%
    "step_rhythm": 0.20,  # Nhịp bước: 20%
    "torso_stability": 0.20,  # Ổn định thân người: 20%
}

# Công thức tính điểm
SCORING_FORMULA = "exponential"  # "linear" or "exponential"
SCORING_MAX_POINTS = 10.0

# Cấu hình visualization
VIS_CONFIG = {
    "skeleton_color": (0, 255, 0),  # Màu xanh lá cho skeleton
    "error_colors": {
        "severe": (0, 0, 255),  # Đỏ - lỗi nghiêm trọng
        "moderate": (0, 165, 255),  # Cam - lỗi vừa
        "minor": (0, 255, 255),  # Vàng - lỗi nhẹ
        "good": (0, 255, 0),  # Xanh lá - đúng chuẩn
    },
    "line_thickness": 2,
    "circle_radius": 5,
    "font_scale": 0.6,
    "font_thickness": 2,
}

# Cấu hình DTW (Dynamic Time Warping)
DTW_CONFIG = {
    "distance_metric": "euclidean",  # "euclidean" or "cosine"
    "step_pattern": "symmetric2",  # Step pattern cho DTW
    "window_size": None,  # None = no window, hoặc số frame
}

# Tạo thư mục nếu chưa tồn tại
for dir_path in [DATA_DIR, GOLDEN_TEMPLATE_DIR, INPUT_VIDEOS_DIR, OUTPUT_DIR, MODELS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

