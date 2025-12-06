"""
BƯỚC 2: TRÍCH XUẤT ĐẶC ĐIỂM HÌNH HỌC (FEATURE EXTRACTION)

Tính toán các đặc điểm hình học từ skeleton mẫu chuẩn.
"""
import pickle
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import src.config as config
from src.utils.geometry import (
    calculate_arm_angle,
    calculate_leg_angle,
    calculate_arm_height,
    calculate_leg_height,
    calculate_head_angle,
    calculate_torso_stability
)
from src.utils.smoothing import smooth_keypoints_sequence


def extract_features_from_skeleton(
    skeleton_data: Dict,
    output_path: Path = None
) -> Dict:
    """
    Trích xuất đặc điểm hình học từ skeleton
    
    Args:
        skeleton_data: Dict chứa skeletons từ step1
        output_path: Đường dẫn lưu profile (mặc định: golden_template/golden_profile.json)
        
    Returns:
        Dict chứa profile chuẩn
    """
    if output_path is None:
        output_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_PROFILE_NAME
    
    skeletons = skeleton_data['valid_skeletons']
    metadata = skeleton_data['metadata']
    
    # Chuyển thành numpy array [n_frames, 17, 3]
    skeleton_array = np.array(skeletons)
    
    # Làm mượt skeleton
    print("Đang làm mượt skeleton...")
    smoothed_skeletons = smooth_keypoints_sequence(skeleton_array)
    
    # Tính các đặc điểm cho từng frame
    features_per_frame = []
    
    print("Đang tính toán đặc điểm hình học...")
    for frame_idx, skeleton in enumerate(smoothed_skeletons):
        features = calculate_frame_features(skeleton)
        features['frame_idx'] = frame_idx
        features['timestamp'] = frame_idx / metadata['fps']
        features_per_frame.append(features)
    
    # Tính giá trị trung bình và các thống kê
    profile = calculate_profile_statistics(features_per_frame, metadata)
    
    # Lưu profile
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    
    print(f"Đã lưu profile: {output_path}")
    
    return profile


def calculate_frame_features(skeleton: np.ndarray) -> Dict:
    """
    Tính các đặc điểm cho một frame
    
    Args:
        skeleton: Keypoints [17, 3]
        
    Returns:
        Dict chứa các đặc điểm
    """
    features = {}
    
    # Góc tay
    left_arm_angle = calculate_arm_angle(skeleton, "left")
    right_arm_angle = calculate_arm_angle(skeleton, "right")
    features['arm_angles'] = {
        'left': left_arm_angle,
        'right': right_arm_angle,
        'average': (left_arm_angle + right_arm_angle) / 2 if (left_arm_angle and right_arm_angle) else None
    }
    
    # Góc chân
    left_leg_angle = calculate_leg_angle(skeleton, "left")
    right_leg_angle = calculate_leg_angle(skeleton, "right")
    features['leg_angles'] = {
        'left': left_leg_angle,
        'right': right_leg_angle,
        'average': (left_leg_angle + right_leg_angle) / 2 if (left_leg_angle and right_leg_angle) else None
    }
    
    # Độ cao tay
    left_arm_height = calculate_arm_height(skeleton, "left")
    right_arm_height = calculate_arm_height(skeleton, "right")
    features['arm_heights'] = {
        'left': left_arm_height,
        'right': right_arm_height,
        'average': (left_arm_height + right_arm_height) / 2 if (left_arm_height and right_arm_height) else None
    }
    
    # Độ cao chân
    left_leg_height = calculate_leg_height(skeleton, "left")
    right_leg_height = calculate_leg_height(skeleton, "right")
    features['leg_heights'] = {
        'left': left_leg_height,
        'right': right_leg_height,
        'average': (left_leg_height + right_leg_height) / 2 if (left_leg_height and right_leg_height) else None
    }
    
    # Góc đầu
    head_angle = calculate_head_angle(skeleton)
    features['head_angle'] = head_angle
    
    return features


def calculate_profile_statistics(
    features_per_frame: List[Dict],
    metadata: Dict
) -> Dict:
    """
    Tính thống kê từ các features để tạo profile chuẩn
    """
    # Lọc bỏ các giá trị None
    def get_valid_values(key_path):
        values = []
        for feat in features_per_frame:
            value = feat
            for key in key_path.split('.'):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            if value is not None:
                values.append(value)
        return values
    
    # Tính giá trị trung bình và độ lệch chuẩn
    profile = {
        'metadata': metadata,
        'num_frames': len(features_per_frame),
        'statistics': {}
    }
    
    # Arm angles
    left_arm_angles = get_valid_values('arm_angles.left')
    right_arm_angles = get_valid_values('arm_angles.right')
    profile['statistics']['arm_angle'] = {
        'left': {
            'mean': float(np.mean(left_arm_angles)) if left_arm_angles else None,
            'std': float(np.std(left_arm_angles)) if left_arm_angles else None,
        },
        'right': {
            'mean': float(np.mean(right_arm_angles)) if right_arm_angles else None,
            'std': float(np.std(right_arm_angles)) if right_arm_angles else None,
        }
    }
    
    # Leg angles
    left_leg_angles = get_valid_values('leg_angles.left')
    right_leg_angles = get_valid_values('leg_angles.right')
    profile['statistics']['leg_angle'] = {
        'left': {
            'mean': float(np.mean(left_leg_angles)) if left_leg_angles else None,
            'std': float(np.std(left_leg_angles)) if left_leg_angles else None,
        },
        'right': {
            'mean': float(np.mean(right_leg_angles)) if right_leg_angles else None,
            'std': float(np.std(right_leg_angles)) if right_leg_angles else None,
        }
    }
    
    # Arm heights
    left_arm_heights = get_valid_values('arm_heights.left')
    right_arm_heights = get_valid_values('arm_heights.right')
    profile['statistics']['arm_height'] = {
        'left': {
            'mean': float(np.mean(left_arm_heights)) if left_arm_heights else None,
            'std': float(np.std(left_arm_heights)) if left_arm_heights else None,
        },
        'right': {
            'mean': float(np.mean(right_arm_heights)) if right_arm_heights else None,
            'std': float(np.std(right_arm_heights)) if right_arm_heights else None,
        }
    }
    
    # Leg heights
    left_leg_heights = get_valid_values('leg_heights.left')
    right_leg_heights = get_valid_values('leg_heights.right')
    profile['statistics']['leg_height'] = {
        'left': {
            'mean': float(np.mean(left_leg_heights)) if left_leg_heights else None,
            'std': float(np.std(left_leg_heights)) if left_leg_heights else None,
        },
        'right': {
            'mean': float(np.mean(right_leg_heights)) if right_leg_heights else None,
            'std': float(np.std(right_leg_heights)) if right_leg_heights else None,
        }
    }
    
    # Head angle
    head_angles = get_valid_values('head_angle')
    profile['statistics']['head_angle'] = {
        'mean': float(np.mean(head_angles)) if head_angles else None,
        'std': float(np.std(head_angles)) if head_angles else None,
    }
    
    # Nhịp bước (steps per minute)
    # Phát hiện nhịp bước bằng cách tìm các điểm cực đại của độ cao chân
    step_rhythm = detect_step_rhythm(features_per_frame, metadata)
    profile['statistics']['step_rhythm'] = step_rhythm
    
    # Độ ổn định thân người
    # Cần skeleton array để tính
    # Sẽ được tính trong step khác hoặc có thể tính từ features
    
    return profile


def detect_step_rhythm(features_per_frame: List[Dict], metadata: Dict) -> Dict:
    """
    Phát hiện nhịp bước (steps per minute)
    """
    # Lấy độ cao chân trung bình qua các frame
    leg_heights = []
    for feat in features_per_frame:
        avg_height = feat.get('leg_heights', {}).get('average')
        if avg_height is not None:
            leg_heights.append(avg_height)
    
    if len(leg_heights) < 10:
        return {'steps_per_minute': None, 'detected': False}
    
    # Tìm các điểm cực đại (khi chân đưa lên cao nhất)
    from scipy.signal import find_peaks
    peaks, _ = find_peaks(leg_heights, distance=5, height=np.mean(leg_heights))
    
    if len(peaks) < 2:
        return {'steps_per_minute': None, 'detected': False}
    
    # Tính số bước trên phút
    duration_seconds = len(leg_heights) / metadata['fps']
    num_steps = len(peaks)
    steps_per_minute = (num_steps / duration_seconds) * 60
    
    return {
        'steps_per_minute': float(steps_per_minute),
        'num_steps': int(num_steps),
        'duration_seconds': float(duration_seconds),
        'detected': True
    }


if __name__ == "__main__":
    import sys
    
    skeleton_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_SKELETON_NAME
    
    if len(sys.argv) > 1:
        skeleton_path = Path(sys.argv[1])
    
    if not skeleton_path.exists():
        print(f"Không tìm thấy skeleton file: {skeleton_path}")
        print("Hãy chạy step1_golden_template.py trước!")
        sys.exit(1)
    
    try:
        # Load skeleton data
        with open(skeleton_path, 'rb') as f:
            skeleton_data = pickle.load(f)
        
        # Trích xuất features
        profile = extract_features_from_skeleton(skeleton_data)
        
        print("\n✅ Hoàn thành Bước 2!")
        print(f"Profile đã được lưu: {config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_PROFILE_NAME}")
        print(f"\nThống kê:")
        print(f"- Góc tay trung bình: {profile['statistics']['arm_angle']['left']['mean']:.2f}°")
        print(f"- Góc chân trung bình: {profile['statistics']['leg_angle']['left']['mean']:.2f}°")
        if profile['statistics']['step_rhythm']['detected']:
            print(f"- Nhịp bước: {profile['statistics']['step_rhythm']['steps_per_minute']:.2f} bước/phút")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

