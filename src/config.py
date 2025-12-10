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

# Cấu hình golden template (hỗ trợ nhiều người và góc quay)
GOLDEN_TEMPLATE_CONFIG = {
    "support_multi_person": True,  # Hỗ trợ nhiều người trong một video
    "max_people_per_template": 3,  # Số người tối đa
    "supported_camera_angles": ["front", "side", "back", "diagonal"],  # Các góc quay hỗ trợ
    "auto_select_profile": True,  # Tự động chọn profile phù hợp khi so sánh
    "create_combined_profile": True,  # Tạo profile tổng hợp (trung bình)
    "default_camera_angle": "front",  # Góc quay mặc định
}

# Cấu hình video
VIDEO_CONFIG = {
    "min_resolution": (1280, 720),  # 720p minimum
    "min_fps": 24,  # Giảm xuống 24fps để linh hoạt hơn (24fps là chuẩn phim, 25fps là PAL)
    "strict_validation": False,  # True = reject nếu không đạt, False = chỉ cảnh báo
    "supported_formats": [".mp4", ".avi", ".mov", ".mkv"],
}

# Cấu hình pose estimation
POSE_CONFIG = {
    "model_type": "yolov8",  # "rtmpose" or "yolov8" - mặc định dùng yolov8 (đơn giản hơn)
    "rtmpose_model": "rtmpose-m_8xb256-420e_aic-coco-256x192",  # RTMPose model name
    "yolov8_model": "yolov8s-pose.pt",  # YOLOv8-Pose model (n=nano, s=small, m=medium, l=large, x=xlarge) - NÂNG CẤP LÊN S
    "confidence_threshold": 0.5,  # Tăng lên 0.5 để chỉ lấy detections chất lượng cao
    "keypoint_confidence_threshold": 0.3,  # Tăng lên 0.3 để keypoints chính xác hơn
    "device": "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu",
    "batch_size": 8,  # Số frame xử lý cùng lúc (nếu GPU đủ mạnh)
}

# Cấu hình tracking
TRACKING_CONFIG = {
    "max_age": 50,  # Giảm xuống 50 frames để loại bỏ track cũ nhanh hơn
    "min_hits": 3,  # Tăng lên 3 để chỉ confirm track ổn định (giảm false positives)
    "iou_threshold": 0.3,  # Tăng lên 0.3 để matching chặt chẽ hơn
    "pose_similarity_threshold": 0.4,  # Tăng lên 0.4 để yêu cầu pose giống nhau hơn
    "pose_weight": 0.8,  # Tăng lên 80% - ưu tiên pose nhiều hơn (quan trọng cho điều lệnh)
    "max_people": 20,  # Số người tối đa trong một video
    "use_kalman": True,  # Sử dụng Kalman filter để dự đoán vị trí
    "merge_similar_tracks": True,  # Merge các track giống nhau
    "merge_threshold": 0.7,  # Tăng lên 0.7 để merge chặt chẽ hơn (tránh merge nhầm)
}

# Cấu hình filter động tác (để chỉ đánh giá người có động tác tương tự golden)
MOTION_FILTER_CONFIG = {
    "enabled": False,  # Tắt filter động tác - đánh giá tất cả người được phát hiện
    "min_motion_variance": 50.0,  # Variance tối thiểu của vị trí keypoints (pixel^2)
    "min_similarity_score": 0.3,  # Similarity score tối thiểu với golden template (0-1)
    "motion_check_frames": 30,  # Số frame để kiểm tra motion
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
# Ngưỡng cao hơn = dễ đạt điểm cao hơn, ngưỡng thấp = khắt khe hơn
ERROR_THRESHOLDS = {
    "arm_angle": 30.0,  # Độ - Tăng lên 30° để chấp nhận sai lệch tracking
    "leg_angle": 25.0,  # Độ - Tăng lên 25° vì chân di chuyển nhiều
    "arm_height": 30.0,  # cm - Tăng lên vì height không đáng tin cậy
    "leg_height": 25.0,  # cm - Tăng lên vì height thay đổi nhiều
    "head_angle": 15.0,  # Độ - Tăng lên vì đầu có góc quay khác nhau
    "torso_stability": 20.0,  # cm - Tăng lên vì thân người di chuyển tự nhiên
    "step_rhythm": 0.25,  # 25% sai lệch nhịp - Cho phép linh hoạt hơn
}

# Trọng số tính điểm - Cải thiện để phản ánh tầm quan trọng thực tế
# CHỈ DÙNG GÓC, BỎ QUA HEIGHT (không bất biến với góc quay camera)
SCORING_WEIGHTS = {
    "arm_technique": 0.40,  # Kỹ thuật tay: 40% (CHỈ từ arm_angle, bỏ arm_height)
    "leg_technique": 0.40,  # Kỹ thuật chân: 40% (CHỈ từ leg_angle, bỏ leg_height)
    "step_rhythm": 0.10,    # Nhịp bước: 10% (giảm xuống vì ít quan trọng hơn)
    "torso_stability": 0.10 # Ổn định thân người: 10% (dùng head_angle)
}

# Công thức tính điểm
SCORING_FORMULA = "exponential"  # "exponential" - Điểm giảm từ từ, không bị 0 ngay
SCORING_MAX_POINTS = 10.0
SCORING_DECAY_RATE = 0.5  # Tốc độ giảm điểm (càng nhỏ càng từ từ)
# Với exponential: điểm = max_points * exp(-error * decay_rate / threshold)
# Lợi ích: Lỗi nhỏ vẫn được điểm cao, lỗi lớn vẫn có điểm (không bị 0)

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

