"""
Utilities để filter người có động tác tương tự golden template
"""
import numpy as np
import pickle
from typing import Dict, List, Tuple
from pathlib import Path
import src.config as config
from src.utils.geometry import cosine_similarity, calculate_distance


def calculate_motion_score(keypoints_sequence: np.ndarray) -> float:
    """
    Tính điểm chuyển động dựa trên variance của vị trí keypoints
    
    Args:
        keypoints_sequence: [n_frames, 17, 3]
        
    Returns:
        Motion score (variance tổng hợp)
    """
    # Kiểm tra edge cases
    if len(keypoints_sequence) == 0:
        return 0.0
    
    if len(keypoints_sequence) < 2:
        return 0.0
    
    # Kiểm tra shape hợp lệ
    if keypoints_sequence.ndim != 3 or keypoints_sequence.shape[1] == 0 or keypoints_sequence.shape[2] < 2:
        return 0.0
    
    # Tính variance của mỗi keypoint qua các frame
    variances = []
    for kp_idx in range(keypoints_sequence.shape[1]):
        # Lấy tọa độ x, y (bỏ qua confidence)
        coords = keypoints_sequence[:, kp_idx, :2]  # [n_frames, 2]
        
        # Chỉ tính cho keypoints có confidence > 0
        valid_mask = keypoints_sequence[:, kp_idx, 2] > 0
        if np.sum(valid_mask) < 2:
            continue
        
        valid_coords = coords[valid_mask]
        
        # Tính variance của x và y
        var_x = np.var(valid_coords[:, 0])
        var_y = np.var(valid_coords[:, 1])
        total_var = var_x + var_y
        variances.append(total_var)
    
    if len(variances) == 0:
        return 0.0
    
    # Trả về variance trung bình
    return float(np.mean(variances))


def calculate_similarity_with_golden(
    person_keypoints: np.ndarray,
    golden_keypoints: np.ndarray
) -> float:
    """
    Tính similarity score giữa person và golden template
    
    Args:
        person_keypoints: [n_frames, 17, 3]
        golden_keypoints: [n_frames_golden, 17, 3]
        
    Returns:
        Similarity score (0-1)
    """
    # Kiểm tra edge cases
    if len(person_keypoints) == 0 or len(golden_keypoints) == 0:
        return 0.0
    
    # Lấy một số frame mẫu từ golden để so sánh
    n_samples = min(10, len(golden_keypoints))
    if n_samples == 0:
        return 0.0
    
    stride_golden = max(1, len(golden_keypoints) // n_samples)
    golden_samples = golden_keypoints[::stride_golden][:n_samples]
    
    # Lấy một số frame từ person
    n_person_samples = min(10, len(person_keypoints))
    if n_person_samples == 0:
        return 0.0
    
    stride_person = max(1, len(person_keypoints) // n_person_samples)
    person_samples = person_keypoints[::stride_person][:n_person_samples]
    
    similarities = []
    
    for golden_frame in golden_samples:
        for person_frame in person_samples:
            # Tính similarity dựa trên cấu trúc skeleton
            sim = calculate_skeleton_similarity(golden_frame, person_frame)
            similarities.append(sim)
    
    if len(similarities) == 0:
        return 0.0
    
    return float(np.mean(similarities))


def calculate_skeleton_similarity(
    keypoints1: np.ndarray,
    keypoints2: np.ndarray
) -> float:
    """
    Tính similarity giữa 2 skeleton dựa trên:
    - Tỷ lệ chiều dài các đoạn xương
    - Góc giữa các đoạn xương
    """
    # Kiểm tra edge cases
    if keypoints1 is None or keypoints2 is None:
        return 0.0
    
    if (keypoints1.shape[0] < 17 or keypoints2.shape[0] < 17 or
        keypoints1.shape[1] < 2 or keypoints2.shape[1] < 2):
        return 0.0
    
    # Định nghĩa các đoạn xương quan trọng
    bone_pairs = [
        # Torso
        (config.KEYPOINT_INDICES["left_shoulder"], config.KEYPOINT_INDICES["left_hip"]),
        (config.KEYPOINT_INDICES["right_shoulder"], config.KEYPOINT_INDICES["right_hip"]),
        # Arms
        (config.KEYPOINT_INDICES["left_shoulder"], config.KEYPOINT_INDICES["left_elbow"]),
        (config.KEYPOINT_INDICES["left_elbow"], config.KEYPOINT_INDICES["left_wrist"]),
        (config.KEYPOINT_INDICES["right_shoulder"], config.KEYPOINT_INDICES["right_elbow"]),
        (config.KEYPOINT_INDICES["right_elbow"], config.KEYPOINT_INDICES["right_wrist"]),
        # Legs
        (config.KEYPOINT_INDICES["left_hip"], config.KEYPOINT_INDICES["left_knee"]),
        (config.KEYPOINT_INDICES["left_knee"], config.KEYPOINT_INDICES["left_ankle"]),
        (config.KEYPOINT_INDICES["right_hip"], config.KEYPOINT_INDICES["right_knee"]),
        (config.KEYPOINT_INDICES["right_knee"], config.KEYPOINT_INDICES["right_ankle"]),
    ]
    
    similarities = []
    
    for start_idx, end_idx in bone_pairs:
        # Kiểm tra keypoints có hợp lệ không
        if (keypoints1[start_idx, 2] == 0 or keypoints1[end_idx, 2] == 0 or
            keypoints2[start_idx, 2] == 0 or keypoints2[end_idx, 2] == 0):
            continue
        
        # Tính vector xương
        vec1 = keypoints1[end_idx, :2] - keypoints1[start_idx, :2]
        vec2 = keypoints2[end_idx, :2] - keypoints2[start_idx, :2]
        
        # Tính độ dài
        len1 = np.linalg.norm(vec1)
        len2 = np.linalg.norm(vec2)
        
        if len1 == 0 or len2 == 0:
            continue
        
        # Similarity dựa trên:
        # 1. Tỷ lệ độ dài
        length_ratio = min(len1, len2) / max(len1, len2)
        
        # 2. Góc giữa 2 vector (cosine similarity)
        angle_sim = cosine_similarity(vec1, vec2)
        
        # Kết hợp
        combined_sim = (length_ratio + angle_sim) / 2
        similarities.append(combined_sim)
    
    if len(similarities) == 0:
        return 0.0
    
    return float(np.mean(similarities))


def filter_people_by_motion(
    tracked_people: Dict[int, np.ndarray],
    golden_skeleton_path: Path = None
) -> Dict[int, np.ndarray]:
    """
    Filter người dựa trên motion và similarity với golden template
    
    Args:
        tracked_people: Dict {person_id: keypoints_sequence}
        golden_skeleton_path: Đường dẫn golden skeleton (optional)
        
    Returns:
        Dict chỉ chứa người có động tác tương tự golden
    """
    if not config.MOTION_FILTER_CONFIG["enabled"]:
        return tracked_people
    
    print("\nĐang filter người có động tác tương tự golden template...")
    
    # Load golden skeleton nếu có
    golden_keypoints = None
    if golden_skeleton_path and golden_skeleton_path.exists():
        with open(golden_skeleton_path, 'rb') as f:
            golden_data = pickle.load(f)
        golden_keypoints = np.array(golden_data['valid_skeletons'])
        print(f"Đã load golden template: {len(golden_keypoints)} frames")
    
    filtered_people = {}
    motion_scores = {}
    similarity_scores = {}
    
    for person_id, keypoints_sequence in tracked_people.items():
        # Kiểm tra edge cases
        if keypoints_sequence is None or len(keypoints_sequence) == 0:
            print(f"✗ Người {person_id}: Không có dữ liệu keypoints - BỊ LOẠI")
            continue
        
        # Tính motion score
        motion_score = calculate_motion_score(keypoints_sequence)
        motion_scores[person_id] = motion_score
        
        # Tính similarity với golden nếu có
        similarity_score = 0.5  # Default nếu không có golden
        if golden_keypoints is not None and len(golden_keypoints) > 0:
            similarity_score = calculate_similarity_with_golden(
                keypoints_sequence,
                golden_keypoints
            )
        similarity_scores[person_id] = similarity_score
        
        # Kiểm tra điều kiện
        min_motion = config.MOTION_FILTER_CONFIG["min_motion_variance"]
        min_similarity = config.MOTION_FILTER_CONFIG["min_similarity_score"]
        
        passed = True
        reasons = []
        
        if motion_score < min_motion:
            passed = False
            reasons.append(f"motion thấp ({motion_score:.1f} < {min_motion})")
        
        if similarity_score < min_similarity:
            passed = False
            reasons.append(f"similarity thấp ({similarity_score:.2f} < {min_similarity})")
        
        if passed:
            filtered_people[person_id] = keypoints_sequence
            print(f"✓ Người {person_id}: motion={motion_score:.1f}, similarity={similarity_score:.2f} - ĐÃ CHỌN")
        else:
            print(f"✗ Người {person_id}: motion={motion_score:.1f}, similarity={similarity_score:.2f} - BỊ LOẠI ({', '.join(reasons)})")
    
    print(f"\nKết quả filter: {len(filtered_people)}/{len(tracked_people)} người được chọn")
    
    return filtered_people

