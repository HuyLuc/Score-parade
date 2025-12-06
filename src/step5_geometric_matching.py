"""
BƯỚC 5: SO SÁNH HÌNH HỌC (GEOMETRIC MATCHING)

Đo sai lệch giữa động tác thực tế và mẫu chuẩn.
"""
import pickle
import json
import numpy as np
from pathlib import Path
from typing import Dict, List
import src.config as config
from src.utils.geometry import (
    calculate_arm_angle,
    calculate_leg_angle,
    calculate_arm_height,
    calculate_leg_height,
    calculate_head_angle,
    calculate_torso_stability,
    cosine_similarity
)


def compare_with_golden(
    golden_profile_path: Path,
    aligned_skeleton_path: Path,
    golden_skeleton_path: Path,
    output_path: Path = None
) -> Dict:
    """
    So sánh skeleton đã align với golden template
    
    Args:
        golden_profile_path: Đường dẫn profile chuẩn (từ step2)
        aligned_skeleton_path: Đường dẫn skeleton đã align (từ step4)
        golden_skeleton_path: Đường dẫn skeleton golden (từ step1)
        output_path: Đường dẫn lưu error metrics
        
    Returns:
        Dict chứa error metrics
    """
    # Load golden profile
    with open(golden_profile_path, 'r', encoding='utf-8') as f:
        golden_profile = json.load(f)
    
    # Load aligned skeleton
    with open(aligned_skeleton_path, 'rb') as f:
        aligned_data = pickle.load(f)
    aligned_keypoints = aligned_data['aligned_keypoints']  # [n_frames, 17, 3]
    
    # Load golden skeleton để so sánh frame-by-frame
    with open(golden_skeleton_path, 'rb') as f:
        golden_data = pickle.load(f)
    golden_keypoints = np.array(golden_data['valid_skeletons'])  # [n_frames, 17, 3]
    
    # Đảm bảo cùng độ dài
    min_length = min(len(aligned_keypoints), len(golden_keypoints))
    aligned_keypoints = aligned_keypoints[:min_length]
    golden_keypoints = golden_keypoints[:min_length]
    
    print(f"Đang so sánh {min_length} frames...")
    
    # Tính errors cho từng frame
    errors_per_frame = []
    
    for frame_idx in range(min_length):
        frame_errors = calculate_frame_errors(
            aligned_keypoints[frame_idx],
            golden_keypoints[frame_idx],
            golden_profile,
            frame_idx
        )
        errors_per_frame.append(frame_errors)
    
    # Tính tổng hợp errors
    summary_errors = calculate_summary_errors(errors_per_frame)
    
    # Lưu kết quả
    if output_path is None:
        output_dir = aligned_skeleton_path.parent
        person_id = aligned_data['person_id']
        output_path = output_dir / f"person_{person_id}_errors.json"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    result = {
        'person_id': aligned_data['person_id'],
        'num_frames': min_length,
        'errors_per_frame': errors_per_frame,
        'summary': summary_errors
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Đã lưu error metrics: {output_path}")
    
    return result


def calculate_frame_errors(
    person_keypoints: np.ndarray,
    golden_keypoints: np.ndarray,
    golden_profile: Dict,
    frame_idx: int
) -> Dict:
    """
    Tính errors cho một frame
    """
    errors = {
        'frame_idx': frame_idx,
        'arm_angle_error': {},
        'leg_angle_error': {},
        'arm_height_error': {},
        'leg_height_error': {},
        'head_angle_error': None,
        'torso_stability_error': None,
    }
    
    # Góc tay
    person_left_arm = calculate_arm_angle(person_keypoints, "left")
    person_right_arm = calculate_arm_angle(person_keypoints, "right")
    golden_left_arm = calculate_arm_angle(golden_keypoints, "left")
    golden_right_arm = calculate_arm_angle(golden_keypoints, "right")
    
    if person_left_arm and golden_left_arm:
        errors['arm_angle_error']['left'] = abs(person_left_arm - golden_left_arm)
    if person_right_arm and golden_right_arm:
        errors['arm_angle_error']['right'] = abs(person_right_arm - golden_right_arm)
    
    # Góc chân
    person_left_leg = calculate_leg_angle(person_keypoints, "left")
    person_right_leg = calculate_leg_angle(person_keypoints, "right")
    golden_left_leg = calculate_leg_angle(golden_keypoints, "left")
    golden_right_leg = calculate_leg_angle(golden_keypoints, "right")
    
    if person_left_leg and golden_left_leg:
        errors['leg_angle_error']['left'] = abs(person_left_leg - golden_left_leg)
    if person_right_leg and golden_right_leg:
        errors['leg_angle_error']['right'] = abs(person_right_leg - golden_right_leg)
    
    # Độ cao tay
    person_left_arm_h = calculate_arm_height(person_keypoints, "left")
    person_right_arm_h = calculate_arm_height(person_keypoints, "right")
    golden_left_arm_h = calculate_arm_height(golden_keypoints, "left")
    golden_right_arm_h = calculate_arm_height(golden_keypoints, "right")
    
    if person_left_arm_h and golden_left_arm_h:
        errors['arm_height_error']['left'] = abs(person_left_arm_h - golden_left_arm_h)
    if person_right_arm_h and golden_right_arm_h:
        errors['arm_height_error']['right'] = abs(person_right_arm_h - golden_right_arm_h)
    
    # Độ cao chân
    person_left_leg_h = calculate_leg_height(person_keypoints, "left")
    person_right_leg_h = calculate_leg_height(person_keypoints, "right")
    golden_left_leg_h = calculate_leg_height(golden_keypoints, "left")
    golden_right_leg_h = calculate_leg_height(golden_keypoints, "right")
    
    if person_left_leg_h and golden_left_leg_h:
        errors['leg_height_error']['left'] = abs(person_left_leg_h - golden_left_leg_h)
    if person_right_leg_h and golden_right_leg_h:
        errors['leg_height_error']['right'] = abs(person_right_leg_h - golden_right_leg_h)
    
    # Góc đầu
    person_head = calculate_head_angle(person_keypoints)
    golden_head = calculate_head_angle(golden_keypoints)
    
    if person_head and golden_head:
        errors['head_angle_error'] = abs(person_head - golden_head)
    
    return errors


def calculate_summary_errors(errors_per_frame: List[Dict]) -> Dict:
    """
    Tính tổng hợp errors qua tất cả frames
    """
    summary = {
        'arm_angle': {'left': [], 'right': []},
        'leg_angle': {'left': [], 'right': []},
        'arm_height': {'left': [], 'right': []},
        'leg_height': {'left': [], 'right': []},
        'head_angle': [],
    }
    
    for frame_errors in errors_per_frame:
        # Arm angle
        if 'left' in frame_errors['arm_angle_error']:
            summary['arm_angle']['left'].append(frame_errors['arm_angle_error']['left'])
        if 'right' in frame_errors['arm_angle_error']:
            summary['arm_angle']['right'].append(frame_errors['arm_angle_error']['right'])
        
        # Leg angle
        if 'left' in frame_errors['leg_angle_error']:
            summary['leg_angle']['left'].append(frame_errors['leg_angle_error']['left'])
        if 'right' in frame_errors['leg_angle_error']:
            summary['leg_angle']['right'].append(frame_errors['leg_angle_error']['right'])
        
        # Arm height
        if 'left' in frame_errors['arm_height_error']:
            summary['arm_height']['left'].append(frame_errors['arm_height_error']['left'])
        if 'right' in frame_errors['arm_height_error']:
            summary['arm_height']['right'].append(frame_errors['arm_height_error']['right'])
        
        # Leg height
        if 'left' in frame_errors['leg_height_error']:
            summary['leg_height']['left'].append(frame_errors['leg_height_error']['left'])
        if 'right' in frame_errors['leg_height_error']:
            summary['leg_height']['right'].append(frame_errors['leg_height_error']['right'])
        
        # Head angle
        if frame_errors['head_angle_error'] is not None:
            summary['head_angle'].append(frame_errors['head_angle_error'])
    
    # Tính thống kê
    result = {}
    
    for key, value in summary.items():
        if isinstance(value, dict):
            result[key] = {}
            for side, errors in value.items():
                if errors:
                    result[key][side] = {
                        'mean': float(np.mean(errors)),
                        'std': float(np.std(errors)),
                        'max': float(np.max(errors)),
                        'min': float(np.min(errors))
                    }
        else:
            if value:
                result[key] = {
                    'mean': float(np.mean(value)),
                    'std': float(np.std(value)),
                    'max': float(np.max(value)),
                    'min': float(np.min(value))
                }
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python step5_geometric_matching.py <golden_profile> <aligned_skeleton> <golden_skeleton>")
        sys.exit(1)
    
    golden_profile_path = Path(sys.argv[1])
    aligned_skeleton_path = Path(sys.argv[2])
    golden_skeleton_path = Path(sys.argv[3])
    
    # Default paths
    if not golden_profile_path.exists():
        golden_profile_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_PROFILE_NAME
    if not golden_skeleton_path.exists():
        golden_skeleton_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_SKELETON_NAME
    
    if not aligned_skeleton_path.exists():
        print(f"Không tìm thấy aligned skeleton: {aligned_skeleton_path}")
        sys.exit(1)
    
    try:
        result = compare_with_golden(
            golden_profile_path,
            aligned_skeleton_path,
            golden_skeleton_path
        )
        print(f"\n✅ Hoàn thành Bước 5!")
        print(f"\nTổng hợp lỗi:")
        if 'arm_angle' in result['summary']:
            print(f"  - Góc tay trung bình: {result['summary']['arm_angle']['left'].get('mean', 0):.2f}°")
        if 'leg_angle' in result['summary']:
            print(f"  - Góc chân trung bình: {result['summary']['leg_angle']['left'].get('mean', 0):.2f}°")
        if 'head_angle' in result['summary']:
            print(f"  - Góc đầu trung bình: {result['summary']['head_angle'].get('mean', 0):.2f}°")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

