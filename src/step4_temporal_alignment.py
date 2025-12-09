"""
BƯỚC 4: CĂN CHỈNH THỜI GIAN (TEMPORAL ALIGNMENT)

Khớp nhịp và pha chuyển động giữa video mẫu và video mới bằng DTW.
"""
import pickle
import json
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import src.config as config
from dtw import dtw


def align_temporal(
    golden_skeleton_path: Path,
    person_skeleton_path: Path,
    output_path: Path = None
) -> Dict:
    """
    Căn chỉnh thời gian giữa golden template và video mới
    
    Args:
        golden_skeleton_path: Đường dẫn skeleton golden template
        person_skeleton_path: Đường dẫn skeleton của một người
        output_path: Đường dẫn lưu kết quả alignment
        
    Returns:
        Dict chứa mapping và aligned sequences
    """
    # Load golden skeleton
    with open(golden_skeleton_path, 'rb') as f:
        golden_data = pickle.load(f)
    golden_skeletons = np.array(golden_data['valid_skeletons'])
    
    # Load person skeleton
    with open(person_skeleton_path, 'rb') as f:
        person_data = pickle.load(f)
    person_keypoints = person_data['keypoints']  # [n_frames, 17, 3]
    person_frame_indices = person_data.get('frame_indices', None)  # Lấy frame indices nếu có
    
    print(f"Golden template: {len(golden_skeletons)} frames")
    print(f"Person video: {len(person_keypoints)} frames")
    
    # Trích xuất features để so sánh (ví dụ: vị trí hông)
    golden_features = extract_temporal_features(golden_skeletons)
    person_features = extract_temporal_features(person_keypoints)
    
    # Tính DTW
    print("Đang tính DTW alignment...")
    alignment = dtw(
        golden_features,
        person_features,
        distance_only=False,
        step_pattern='symmetric2'
    )
    
    # Tạo mapping: frame_golden -> frame_person
    mapping = create_frame_mapping(alignment, len(golden_skeletons), len(person_keypoints))
    
    # Tạo aligned person sequence (cùng độ dài với golden)
    aligned_person_keypoints = align_sequence(person_keypoints, mapping)
    
    # Lưu kết quả
    if output_path is None:
        output_dir = person_skeleton_path.parent
        person_id = person_data['person_id']
        output_path = output_dir / f"person_{person_id}_aligned.pkl"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        pickle.dump({
            'person_id': person_data['person_id'],
            'mapping': mapping,
            'aligned_keypoints': aligned_person_keypoints,
            'frame_indices': person_frame_indices,  # QUAN TRỌNG: Truyền frame indices
            'dtw_distance': alignment.distance,
            'dtw_normalized_distance': alignment.normalizedDistance,
            'golden_length': len(golden_skeletons),
            'original_length': len(person_keypoints),
            'aligned_length': len(aligned_person_keypoints)
        }, f)

    
    print(f"Đã lưu alignment: {output_path}")
    print(f"DTW distance: {alignment.distance:.2f}")
    print(f"Normalized distance: {alignment.normalizedDistance:.4f}")
    
    return {
        'alignment_path': output_path,
        'mapping': mapping,
        'aligned_keypoints': aligned_person_keypoints,
        'dtw_distance': alignment.distance,
        'dtw_normalized_distance': alignment.normalizedDistance
    }


def extract_temporal_features(keypoints_sequence: np.ndarray) -> np.ndarray:
    """
    Trích xuất features để so sánh temporal (ví dụ: vị trí hông, độ cao chân)
    
    Args:
        keypoints_sequence: [n_frames, 17, 3]
        
    Returns:
        Features [n_frames, n_features]
    """
    features = []
    
    for frame_keypoints in keypoints_sequence:
        frame_features = []
        
        # Vị trí hông (trung bình 2 hông)
        left_hip = frame_keypoints[config.KEYPOINT_INDICES["left_hip"], :2]
        right_hip = frame_keypoints[config.KEYPOINT_INDICES["right_hip"], :2]
        center_hip = (left_hip + right_hip) / 2
        frame_features.extend(center_hip.tolist())
        
        # Độ cao chân (mắt cá chân thấp hơn)
        left_ankle_y = frame_keypoints[config.KEYPOINT_INDICES["left_ankle"], 1]
        right_ankle_y = frame_keypoints[config.KEYPOINT_INDICES["right_ankle"], 1]
        min_ankle_y = min(left_ankle_y, right_ankle_y)
        frame_features.append(min_ankle_y)
        
        # Độ cao tay (cổ tay cao hơn)
        left_wrist_y = frame_keypoints[config.KEYPOINT_INDICES["left_wrist"], 1]
        right_wrist_y = frame_keypoints[config.KEYPOINT_INDICES["right_wrist"], 1]
        max_wrist_y = max(left_wrist_y, right_wrist_y)
        frame_features.append(max_wrist_y)
        
        features.append(frame_features)
    
    return np.array(features)


def create_frame_mapping(
    alignment,
    golden_length: int,
    person_length: int
) -> Dict[int, int]:
    """
    Tạo mapping từ frame golden sang frame person
    
    Args:
        alignment: DTW alignment result
        golden_length: Số frame golden
        person_length: Số frame person
        
    Returns:
        Dict {golden_frame_idx: person_frame_idx}
    """
    mapping = {}
    
    # alignment.index1: indices của golden sequence
    # alignment.index2: indices của person sequence
    for i, (g_idx, p_idx) in enumerate(zip(alignment.index1, alignment.index2)):
        # Có thể có nhiều golden frame map tới cùng person frame
        # Lấy mapping đầu tiên hoặc trung bình
        if g_idx not in mapping:
            mapping[g_idx] = p_idx
    
    # Đảm bảo tất cả golden frames đều có mapping
    for g_idx in range(golden_length):
        if g_idx not in mapping:
            # Tìm frame person gần nhất
            if g_idx == 0:
                mapping[g_idx] = 0
            elif g_idx == golden_length - 1:
                mapping[g_idx] = person_length - 1
            else:
                # Interpolate
                prev_g = max([k for k in mapping.keys() if k < g_idx], default=0)
                next_g = min([k for k in mapping.keys() if k > g_idx], default=golden_length-1)
                prev_p = mapping[prev_g]
                next_p = mapping[next_g]
                # Linear interpolation
                ratio = (g_idx - prev_g) / (next_g - prev_g) if next_g != prev_g else 0
                mapping[g_idx] = int(prev_p + ratio * (next_p - prev_p))
    
    return mapping


def align_sequence(
    person_keypoints: np.ndarray,
    mapping: Dict[int, int]
) -> np.ndarray:
    """
    Tạo aligned sequence dựa trên mapping
    
    Args:
        person_keypoints: [n_frames, 17, 3]
        mapping: {golden_frame_idx: person_frame_idx}
        
    Returns:
        Aligned keypoints [n_golden_frames, 17, 3]
    """
    aligned = []
    golden_length = max(mapping.keys()) + 1
    
    for g_idx in range(golden_length):
        p_idx = mapping[g_idx]
        # Clamp index
        p_idx = max(0, min(p_idx, len(person_keypoints) - 1))
        aligned.append(person_keypoints[p_idx])
    
    return np.array(aligned)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python step4_temporal_alignment.py <golden_skeleton_path> <person_skeleton_path>")
        sys.exit(1)
    
    golden_path = Path(sys.argv[1])
    person_path = Path(sys.argv[2])
    
    if not golden_path.exists():
        # Thử dùng default
        golden_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_SKELETON_NAME
        if not golden_path.exists():
            print(f"Không tìm thấy golden skeleton: {sys.argv[1]}")
            sys.exit(1)
    
    if not person_path.exists():
        print(f"Không tìm thấy person skeleton: {person_path}")
        sys.exit(1)
    
    try:
        result = align_temporal(golden_path, person_path)
        print(f"\n✅ Hoàn thành Bước 4!")
        print(f"Alignment saved: {result['alignment_path']}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

