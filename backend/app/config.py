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
    "conf_threshold": 0.15,  # Giảm từ 0.20 xuống 0.15 để phát hiện tốt hơn
    # Ngưỡng cho từng keypoint và số lượng keypoint tối thiểu để chấp nhận một người
    "keypoint_confidence_threshold": 0.20,  # Giảm từ 0.25 xuống 0.20
    "min_valid_keypoints": 4,  # Giảm từ 5 xuống 4 để linh hoạt hơn
}

# Cấu hình Confidence-Based Filtering - Lọc keypoints có confidence thấp
CONFIDENCE_FILTERING_CONFIG = {
    "enabled": True,  # Bật/tắt confidence filtering
    "threshold": 0.5,  # Ngưỡng confidence tối thiểu để chấm lỗi (keypoints có confidence < threshold sẽ bị mask)
    # Không chấm lỗi trên keypoints có confidence < threshold để tránh false positives
}

# Cấu hình Confidence-Based Filtering - Lọc keypoints có confidence thấp
CONFIDENCE_FILTERING_CONFIG = {
    "enabled": True,  # Bật/tắt confidence filtering
    "threshold": 0.5,  # Ngưỡng confidence tối thiểu để chấm lỗi (keypoints có confidence < threshold sẽ bị mask)
    # Không chấm lỗi trên keypoints có confidence < threshold để tránh false positives
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
    # Ngưỡng đạt/trượt theo chế độ
    "fail_thresholds": {
        "testing": 50.0,     # Thi / kiểm tra: dưới 50 điểm = trượt
        "practising": 0.0,   # Luyện tập: luôn coi là để học, không trượt
        "default": 50.0,     # Dự phòng cho các nơi cũ chưa truyền mode
    },
    # Chế độ khắt khe (easy/medium/hard)
    "difficulty_level": "medium",  # 'easy', 'medium', 'hard'
    # Tiêu chí chấm (đi đều hay đi nghiêm)
    "scoring_criterion": "di_deu",  # 'di_deu' hoặc 'di_nghiem'
    # Chế độ hoạt động (dev/release)
    "app_mode": "release",  # 'dev' hoặc 'release'
    # Bật/tắt chấm đa người (frontend có thể điều chỉnh)
    "multi_person_enabled": True,
    "error_weights": {
        "arm_angle": 1.0,
        "leg_angle": 1.0,
        "arm_height": 0.8,
        "leg_height": 0.8,
        # Đầu / head quan trọng ngang tay/chân trong điều lệnh
        "head_angle": 1.0,
        "neck_angle": 0.9,  # Cổ quan trọng nhưng ít hơn đầu một chút
        "torso_stability": 0.8,
        "rhythm": 1.0,
        "distance": 0.8,
        "speed": 0.8,
    },
}

# Ngưỡng sai lệch mặc định (dùng khi không có std từ golden)
ERROR_THRESHOLDS = {
    "arm_angle": 50.0,  # Tăng từ 30.0 → 50.0 (tăng 67%)
    "leg_angle": 45.0,  # Tăng từ 25.0 → 45.0 (tăng 80%)
    "arm_height": 50.0,  # Tăng từ 30.0 → 50.0
    "leg_height": 45.0,  # Tăng từ 25.0 → 45.0
    "head_angle": 30.0,  # Tăng từ 15.0 → 30.0 (GẤP ĐÔI - QUAN TRỌNG!)
    "neck_angle": 25.0,  # Ngưỡng cho góc cổ (tương tự head nhưng lỏng hơn một chút)
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
    # Tăng window size để giảm nhiễu từ YOLOv8 jitter
    "window_size": 7,  # 7 frames @ 30fps ~ 233ms latency (tối ưu: 7-9 frames)
    # Phương pháp smoothing:
    # - "moving_average": Đơn giản, nhanh (mặc định)
    # - "median": Chống nhiễu tốt, loại bỏ outliers
    # - "gaussian": Mượt mà, giữ được xu hướng (khuyến nghị)
    # - "savitzky_golay": Tốt nhất cho giữ nguyên đặc điểm động tác (khuyến nghị cho chính xác cao)
    "method": "gaussian",  # "moving_average", "median", "gaussian", "savitzky_golay"
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
    "enabled": True,  # Bật/tắt DTW alignment - Enable để xử lý tempo variations (người thực hiện nhanh/chậm hơn golden template)
    "window_size": 50,  # Window size cho DTW alignment (giới hạn warping path)
    "distance_metric": "euclidean",  # Distance metric: "euclidean", "manhattan", "cosine"
}

# Cấu hình Attention Mechanism - Thêm attention weights cho từng body part theo context
# Giúp tăng độ chính xác bằng cách tập trung vào các body part quan trọng nhất trong từng động tác
CONTEXT_ATTENTION = {
    "nghiem": {
        "arm": 1.5,      # Tay quan trọng nhất trong động tác "Nghiêm"
        "leg": 0.5,      # Chân ít quan trọng hơn
        "head": 1.2,     # Đầu quan trọng
        "neck": 1.0,     # Cổ bình thường
        "rhythm": 0.8,   # Timing ít quan trọng hơn trong nghiêm
    },
    "di_deu": {
        "leg": 1.5,      # Chân quan trọng nhất trong động tác "Đi đều bước"
        "arm": 1.0,      # Tay bình thường
        "head": 1.0,     # Đầu bình thường
        "neck": 1.0,     # Cổ bình thường
        "rhythm": 1.8,   # Timing rất quan trọng trong đi đều
    },
    "default": {
        "arm": 1.0,      # Mặc định: tất cả body parts đều quan trọng như nhau
        "leg": 1.0,
        "head": 1.0,
        "neck": 1.0,
        "rhythm": 1.0,
    }
}

# Cấu hình MinIO cho lưu trữ skeleton video
MINIO_CONFIG = {
    "enabled": True,  # Bật/tắt lưu skeleton video lên MinIO (nếu False sẽ dùng filesystem data/output như cũ)
    "endpoint": os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
    "access_key": os.getenv("MINIO_ACCESS_KEY", "admin"),
    "secret_key": os.getenv("MINIO_SECRET_KEY", "admin123"),
    "bucket": os.getenv("MINIO_BUCKET", "skeleton-videos"),
    # Nếu bạn cấu hình MinIO với HTTPS, chuyển secure=True
    "secure": os.getenv("MINIO_SECURE", "false").lower() == "true",
}

# Cấu hình Attention Mechanism - Thêm attention weights cho từng body part theo context
# Giúp tăng độ chính xác bằng cách tập trung vào các body part quan trọng nhất trong từng động tác
CONTEXT_ATTENTION = {
    "nghiem": {
        "arm": 1.5,      # Tay quan trọng nhất trong động tác "Nghiêm"
        "leg": 0.5,      # Chân ít quan trọng hơn
        "head": 1.2,     # Đầu quan trọng
        "neck": 1.0,     # Cổ bình thường
        "rhythm": 0.8,   # Timing ít quan trọng hơn trong nghiêm
    },
    "di_deu": {
        "leg": 1.5,      # Chân quan trọng nhất trong động tác "Đi đều bước"
        "arm": 1.0,      # Tay bình thường
        "head": 1.0,     # Đầu bình thường
        "neck": 1.0,     # Cổ bình thường
        "rhythm": 1.8,   # Timing rất quan trọng trong đi đều
    },
    "default": {
        "arm": 1.0,      # Mặc định: tất cả body parts đều quan trọng như nhau
        "leg": 1.0,
        "head": 1.0,
        "neck": 1.0,
        "rhythm": 1.0,
    }
}

# Sequence Comparison configuration for grouping consecutive errors
SEQUENCE_COMPARISON_CONFIG = {
    "enabled": True,  # Enable/disable sequence-based error detection
    # Gộp từ 5 frame liên tiếp trở lên thành 1 lỗi để chỉ trừ điểm một lần
    # Tăng từ 2 → 5 để tránh nhóm các lỗi ngắn không liên quan
    "min_sequence_length": 5,  # Minimum frames to form a sequence (tối ưu: 5-7 frames)
    # Cho phép hụt tối đa 3 frames giữa chuỗi (tăng từ 1 → 3)
    # Để xử lý transition frames và lỗi cách nhau 2-3 frames vẫn được nhóm
    "max_gap_frames": 3,  # Frames gap allowed inside a sequence (tối ưu: 3-5 frames)
    # Dùng median để giảm ảnh hưởng của frame outlier (tốt hơn mean)
    "severity_aggregation": "median",  # "mean", "max", "median" (khuyến nghị: "median")
}

# Error Grouping configuration - Nhóm các lỗi liên tiếp để tránh phạt trùng lặp
ERROR_GROUPING_CONFIG = {
    "enabled": True,  # Bật/tắt error grouping
    "min_sequence_length": 2,  # Gộp từ 2 frame liên tiếp thành 1 sequence lỗi
    "max_gap_frames": 1,  # Cho phép hụt 1 frame giữa chuỗi
    "severity_aggregation": "mean",  # Cách tính severity: "mean", "max", "median"
    "sequence_deduction": 1.0,  # Điểm trừ cho mỗi sequence lỗi (thay vì trừ từng frame)
    # Không giới hạn trần trừ điểm theo loại lỗi để cho phép rớt dưới 50 đúng yêu cầu
}

# Multi-Person Tracking configuration
MULTI_PERSON_CONFIG = {
    "enabled": True,  # Enable/disable multi-person mode
    # Tracking method: "sort", "bytetrack", "legacy"
    "tracking_method": "bytetrack",  # ByteTrack cho độ chính xác cao nhất
    # Giới hạn số người tối đa để tránh sinh quá nhiều ID ảo từ noise
    "max_persons": 5,  # Tăng từ 3 lên 5 để hỗ trợ nhiều người hơn
    # Cho phép một người "mất dấu" lâu hơn trước khi tạo ID mới
    # Tăng từ 60 → 90 frames (~3s @30fps) để giảm track loss khi người bị che khuất
    "max_disappeared": 90,  # Tăng từ 60 → 90 để xử lý occlusion tốt hơn
    # Giảm IoU threshold để cùng một người vẫn được match dù bbox hơi dao động
    # Giảm từ 0.5 → 0.4 để nhạy hơn, tránh ID switching khi người giao nhau
    "iou_threshold": 0.4,  # Giảm từ 0.5 → 0.4 để theo dõi tốt hơn
    # Lọc track ngắn (ghost detections) - chỉ giữ track có >= 30 frames
    "min_track_length": 30,  # Minimum frames để track được coi là hợp lệ (lọc ghost detections)
    # Enable ReID features để cải thiện re-identification sau occlusion
    "reid_features": True,  # Enable person re-identification features
    "similarity_threshold": 0.6,  # Pose similarity threshold for matching (0.0-1.0)
    "enable_visualization": True,  # Draw tracking boxes and IDs
    "batch_size": 8,  # Batch size for multi-person detection
    
    # ByteTrack specific parameters
    "bytetrack": {
        "track_thresh": 0.25,      # Detection threshold for tracking (giảm từ 0.35 → 0.25 để tránh tạo ID mới)
        "track_buffer": 90,        # Frames to keep lost tracks (tăng từ 50 → 90 = 3s @ 30fps)
        "match_thresh": 0.6,       # IOU threshold for matching (giảm từ 0.7 → 0.6 để match dễ hơn)
        "high_thresh": 0.35,       # High confidence threshold (giảm từ 0.45 → 0.35)
        "low_thresh": 0.05,        # Low confidence threshold (giảm từ 0.1 → 0.05)
        # Adaptive Kalman Filter configuration
        "use_adaptive_kalman": True,  # Use AdaptiveKalmanFilter instead of simple KalmanFilter
        "adaptive_kalman": {
            "adaptive_enabled": True,  # Enable adaptive noise adjustment
            "base_process_noise": 0.1,  # Base process noise (Q) - tuned for better tracking
            "base_measurement_noise": 1.0,  # Base measurement noise (R) - tuned for better tracking
            "motion_history_size": 10,  # Number of frames to keep for motion analysis
            "keypoint_prediction_enabled": True,  # Enable keypoint prediction (not just bbox)
        }
    },
    # ReID configuration (appearance embedding)
    "reid": {
        "enabled": True,               # Bật/tắt ReID
        "similarity_threshold": 0.7,   # Ngưỡng cosine similarity để coi là cùng người
        "alpha": 0.5,                  # Trọng số kết hợp IOU và similarity (0.5 = cân bằng)
        "method": "osnet_fallback_pose"  # osnet_fallback_pose: ưu tiên OSNet, fallback pose embedding
    }
}

# Post-Processing Filters configuration for multi-person tracking
# Giảm false positives, ID switching, và cải thiện tracking accuracy
POST_PROCESSING_FILTERS_CONFIG = {
    "enabled": True,  # Enable/disable all post-processing filters
    
    # Spatial Consistency Filter - Lọc detections không hợp lý về mặt không gian
    "spatial_enabled": True,
    "min_height": 50.0,  # Minimum bbox height in pixels
    "max_height_ratio": 0.9,  # Maximum height as ratio of frame height
    "min_aspect_ratio": 0.3,  # Minimum width/height ratio (person standing)
    "max_aspect_ratio": 0.7,  # Maximum width/height ratio
    "edge_margin_ratio": 0.1,  # Margin from edges (10% margin)
    
    # Keypoint Geometric Consistency Filter - Kiểm tra anatomical constraints
    "geometric_enabled": True,
    "min_torso_leg_ratio": 0.4,  # Minimum torso length / leg length ratio
    "max_torso_leg_ratio": 0.6,  # Maximum torso length / leg length ratio
    "max_head_shoulder_ratio": 0.3,  # Maximum head height above shoulders / person height
    "min_symmetry_score": 0.7,  # Minimum left-right symmetry score (0-1)
    "min_confidence": 0.3,  # Minimum keypoint confidence to consider
    
    # Velocity-Based Filter - Lọc tracks có vận tốc bất thường
    "velocity_enabled": True,
    "max_velocity": 50.0,  # Maximum allowed velocity (pixels/frame @ 30fps)
    "max_jump_distance": 100.0,  # Maximum allowed position jump in one frame (ID switching detection)
    "min_track_length": 5,  # Minimum track length to apply velocity check
    
    # Occlusion Detection and Handling
    "occlusion_enabled": True,
    "occlusion_threshold": 0.5,  # Minimum visible ratio to consider as occlusion
    "interpolation_window": 5,  # Frames to use for keypoint interpolation
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

