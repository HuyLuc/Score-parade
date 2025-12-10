"""
Utilities cho tính toán hình học: góc, vector, khoảng cách
"""
import numpy as np
from typing import Tuple, List, Optional
import backend.app.config as config


def calculate_angle(
    point1: np.ndarray,
    point2: np.ndarray,
    point3: np.ndarray
) -> float:
    """
    Tính góc tại point2 giữa vector (point2->point1) và (point2->point3)
    
    Args:
        point1: Điểm đầu (numpy array [x, y])
        point2: Điểm giữa (đỉnh góc)
        point3: Điểm cuối
        
    Returns:
        Góc tính bằng độ (0-180)
    """
    # Vector từ point2 đến point1 và point3
    vec1 = point1 - point2
    vec2 = point3 - point2
    
    # Tính góc bằng dot product
    cos_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-8)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Tránh lỗi numerical
    
    angle_rad = np.arccos(cos_angle)
    angle_deg = np.degrees(angle_rad)
    
    return angle_deg


def calculate_distance(point1: np.ndarray, point2: np.ndarray) -> float:
    """
    Tính khoảng cách Euclidean giữa 2 điểm
    
    Args:
        point1: Điểm 1 [x, y]
        point2: Điểm 2 [x, y]
        
    Returns:
        Khoảng cách (pixel)
    """
    return np.linalg.norm(point1 - point2)


def calculate_vector(point1: np.ndarray, point2: np.ndarray) -> np.ndarray:
    """
    Tính vector từ point1 đến point2
    
    Args:
        point1: Điểm đầu
        point2: Điểm cuối
        
    Returns:
        Vector [dx, dy]
    """
    return point2 - point1


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Tính cosine similarity giữa 2 vector
    
    Args:
        vec1: Vector 1
        vec2: Vector 2
        
    Returns:
        Cosine similarity (-1 đến 1)
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def calculate_arm_angle(
    keypoints: np.ndarray,
    side: str = "left"
) -> Optional[float]:
    """
    Tính góc tay (shoulder-elbow-wrist)
    
    Args:
        keypoints: Array keypoints [17, 2] hoặc [17, 3]
        side: "left" hoặc "right"
        
    Returns:
        Góc tay (độ) hoặc None nếu thiếu keypoint
    """
    if side == "left":
        shoulder_idx = config.KEYPOINT_INDICES["left_shoulder"]
        elbow_idx = config.KEYPOINT_INDICES["left_elbow"]
        wrist_idx = config.KEYPOINT_INDICES["left_wrist"]
    else:
        shoulder_idx = config.KEYPOINT_INDICES["right_shoulder"]
        elbow_idx = config.KEYPOINT_INDICES["right_elbow"]
        wrist_idx = config.KEYPOINT_INDICES["right_wrist"]
    
    # Lấy tọa độ (chỉ lấy x, y)
    shoulder = keypoints[shoulder_idx, :2]
    elbow = keypoints[elbow_idx, :2]
    wrist = keypoints[wrist_idx, :2]
    
    # Kiểm tra keypoint có hợp lệ không (confidence > 0)
    if keypoints.shape[1] > 2:
        if (keypoints[shoulder_idx, 2] == 0 or 
            keypoints[elbow_idx, 2] == 0 or 
            keypoints[wrist_idx, 2] == 0):
            return None
    
    return calculate_angle(shoulder, elbow, wrist)


def calculate_leg_angle(
    keypoints: np.ndarray,
    side: str = "left"
) -> Optional[float]:
    """
    Tính góc chân (hip-knee-ankle)
    
    Args:
        keypoints: Array keypoints [17, 2] hoặc [17, 3]
        side: "left" hoặc "right"
        
    Returns:
        Góc chân (độ) hoặc None nếu thiếu keypoint
    """
    if side == "left":
        hip_idx = config.KEYPOINT_INDICES["left_hip"]
        knee_idx = config.KEYPOINT_INDICES["left_knee"]
        ankle_idx = config.KEYPOINT_INDICES["left_ankle"]
    else:
        hip_idx = config.KEYPOINT_INDICES["right_hip"]
        knee_idx = config.KEYPOINT_INDICES["right_knee"]
        ankle_idx = config.KEYPOINT_INDICES["right_ankle"]
    
    hip = keypoints[hip_idx, :2]
    knee = keypoints[knee_idx, :2]
    ankle = keypoints[ankle_idx, :2]
    
    # Kiểm tra keypoint có hợp lệ không
    if keypoints.shape[1] > 2:
        if (keypoints[hip_idx, 2] == 0 or 
            keypoints[knee_idx, 2] == 0 or 
            keypoints[ankle_idx, 2] == 0):
            return None
    
    return calculate_angle(hip, knee, ankle)


def calculate_arm_height(
    keypoints: np.ndarray,
    side: str = "left",
    reference_point: Optional[np.ndarray] = None
) -> Optional[float]:
    """
    Tính độ cao tay so với điểm tham chiếu (thường là vai)
    
    Args:
        keypoints: Array keypoints
        side: "left" hoặc "right"
        reference_point: Điểm tham chiếu [x, y], nếu None thì dùng vai
        
    Returns:
        Độ cao (pixel, có thể âm nếu thấp hơn tham chiếu)
    """
    if side == "left":
        shoulder_idx = config.KEYPOINT_INDICES["left_shoulder"]
        wrist_idx = config.KEYPOINT_INDICES["left_wrist"]
    else:
        shoulder_idx = config.KEYPOINT_INDICES["right_shoulder"]
        wrist_idx = config.KEYPOINT_INDICES["right_wrist"]
    
    shoulder = keypoints[shoulder_idx, :2]
    wrist = keypoints[wrist_idx, :2]
    
    if keypoints.shape[1] > 2:
        if keypoints[shoulder_idx, 2] == 0 or keypoints[wrist_idx, 2] == 0:
            return None
    
    ref = reference_point if reference_point is not None else shoulder
    height = ref[1] - wrist[1]  # Y tăng xuống dưới, nên trừ
    
    return height


def calculate_leg_height(
    keypoints: np.ndarray,
    side: str = "left",
    ground_level: Optional[float] = None
) -> Optional[float]:
    """
    Tính độ cao chân so với mặt đất
    
    Args:
        keypoints: Array keypoints
        side: "left" hoặc "right"
        ground_level: Mức mặt đất (y coordinate), nếu None thì dùng mắt cá chân thấp hơn
        
    Returns:
        Độ cao (pixel)
    """
    if side == "left":
        ankle_idx = config.KEYPOINT_INDICES["left_ankle"]
    else:
        ankle_idx = config.KEYPOINT_INDICES["right_ankle"]
    
    ankle = keypoints[ankle_idx, :2]
    
    if keypoints.shape[1] > 2:
        if keypoints[ankle_idx, 2] == 0:
            return None
    
    # Nếu không có ground_level, dùng mắt cá chân thấp hơn làm tham chiếu
    if ground_level is None:
        left_ankle = keypoints[config.KEYPOINT_INDICES["left_ankle"], 1]
        right_ankle = keypoints[config.KEYPOINT_INDICES["right_ankle"], 1]
        ground_level = max(left_ankle, right_ankle)
    
    height = ground_level - ankle[1]
    return max(0, height)  # Không âm


def calculate_head_angle(keypoints: np.ndarray) -> Optional[float]:
    """
    Tính góc nghiêng đầu (dựa trên vector từ cổ đến mũi)
    
    Args:
        keypoints: Array keypoints
        
    Returns:
        Góc nghiêng đầu (độ, 0 = thẳng đứng)
    """
    nose_idx = config.KEYPOINT_INDICES["nose"]
    left_shoulder_idx = config.KEYPOINT_INDICES["left_shoulder"]
    right_shoulder_idx = config.KEYPOINT_INDICES["right_shoulder"]
    
    nose = keypoints[nose_idx, :2]
    left_shoulder = keypoints[left_shoulder_idx, :2]
    right_shoulder = keypoints[right_shoulder_idx, :2]
    
    if keypoints.shape[1] > 2:
        if (keypoints[nose_idx, 2] == 0 or 
            keypoints[left_shoulder_idx, 2] == 0 or 
            keypoints[right_shoulder_idx, 2] == 0):
            return None
    
    # Điểm giữa 2 vai
    neck = (left_shoulder + right_shoulder) / 2
    
    # Vector từ cổ đến mũi
    vec = nose - neck
    
    # Góc so với trục thẳng đứng (0, -1)
    vertical = np.array([0, -1])
    angle = np.degrees(np.arccos(np.clip(
        np.dot(vec, vertical) / (np.linalg.norm(vec) + 1e-8),
        -1.0, 1.0
    )))
    
    return angle


def calculate_torso_stability(
    keypoints_sequence: np.ndarray
) -> float:
    """
    Tính độ ổn định thân người (variance của vị trí hông)
    
    Args:
        keypoints_sequence: Array [n_frames, 17, 2] hoặc [n_frames, 17, 3]
        
    Returns:
        Variance của vị trí hông (pixel^2)
    """
    left_hip_idx = config.KEYPOINT_INDICES["left_hip"]
    right_hip_idx = config.KEYPOINT_INDICES["right_hip"]
    
    # Lấy tọa độ hông trung bình qua các frame
    hip_positions = []
    for frame_keypoints in keypoints_sequence:
        left_hip = frame_keypoints[left_hip_idx, :2]
        right_hip = frame_keypoints[right_hip_idx, :2]
        center_hip = (left_hip + right_hip) / 2
        hip_positions.append(center_hip)
    
    hip_positions = np.array(hip_positions)
    
    # Tính variance
    variance = np.var(hip_positions, axis=0)
    total_variance = np.sum(variance)
    
    return total_variance

