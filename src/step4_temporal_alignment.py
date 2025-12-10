"""
BƯỚC 4: CĂN CHỈNH THỜI GIAN (TEMPORAL ALIGNMENT)

Khớp nhịp và pha chuyển động giữa video mẫu và video mới bằng DTW.
CẢI TIẾN: Dùng GÓC thay vì tọa độ để detect pha động tác
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
    person_frame_indices = person_data.get('frame_indices', None)
    
    print(f"Golden template: {len(golden_skeletons)} frames")
    print(f"Person video: {len(person_keypoints)} frames")
    
    # Trích xuất features để so sánh - DÙNG GÓC
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
            'frame_indices': person_frame_indices,
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
    Trích xuất features để so sánh temporal - DÙNG GÓC thay vì tọa độ
    
    Lý do: Góc bất biến với camera, giúp DTW nhận diện đúng pha động tác
    
    Args:
        keypoints_sequence: [n_frames, 17, 3]
        
    Returns:
        Features [n_frames, n_features]
    """
    from src.utils.geometry import calculate_arm_angle, calculate_leg_angle, calculate_head_angle
    
    features = []
    
    for frame_keypoints in keypoints_sequence:
        frame_features = []
        
        # GÓC TAY trái và phải (phát hiện pha đánh tay, giơ tay, etc.)
        left_arm_angle = calculate_arm_angle(frame_keypoints, "left")
        right_arm_angle = calculate_arm_angle(frame_keypoints, "right")
        if left_arm_angle is not None:
            frame_features.append(left_arm_angle)
        else:
            frame_features.append(0)
        if right_arm_angle is not None:
            frame_features.append(right_arm_angle)
        else:
            frame_features.append(0)
        
        # GÓC CHÂN trái và phải (phát hiện pha bước chân, duỗi/gập)
        left_leg_angle = calculate_leg_angle(frame_keypoints, "left")
        right_leg_angle = calculate_leg_angle(frame_keypoints, "right")
        if left_leg_angle is not None:
            frame_features.append(left_leg_angle)
        else:
            frame_features.append(0)
        if right_leg_angle is not None:
            frame_features.append(right_leg_angle)
        else:
            frame_features.append(0)
        
        # GÓC ĐẦU (phát hiện pha ngẩng/cúi đầu)
        head_angle = calculate_head_angle(frame_keypoints)
        if head_angle is not None:
            frame_features.append(head_angle)
        else:
            frame_features.append(0)
        
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
        if g_idx not in mapping:
            mapping[g_idx] = p_idx
    
    # Đảm bảo tất cả golden frames đều có mapping
    for g_idx in range(golden_length):
        if g_idx not in mapping:
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
