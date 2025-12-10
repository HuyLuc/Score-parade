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


def extract_features_multi_person(
    template_dir: Path,
    create_combined: bool = True
) -> Dict:
    """
    Trích xuất features cho tất cả người trong template (nhiều người)
    
    Args:
        template_dir: Thư mục template (chứa person_0/, person_1/, ...)
        create_combined: Có tạo profile tổng hợp không
        
    Returns:
        Dict chứa profiles cho từng người và profile tổng hợp
    """
    import json
    
    result = {
        'template_dir': str(template_dir),
        'people': {},
        'combined_profile': None
    }
    
    # Tìm tất cả thư mục person_*
    person_dirs = sorted([d for d in template_dir.iterdir() 
                         if d.is_dir() and d.name.startswith('person_')])
    
    if len(person_dirs) == 0:
        raise ValueError(f"Không tìm thấy thư mục person_* trong {template_dir}")
    
    print(f"Tìm thấy {len(person_dirs)} người trong template")
    
    profiles = []
    
    # Xử lý từng người
    for person_dir in person_dirs:
        person_id = person_dir.name.replace('person_', '')
        skeleton_path = person_dir / "skeleton.pkl"
        
        if not skeleton_path.exists():
            print(f"⚠️  Không tìm thấy skeleton cho người {person_id}")
            continue
        
        # Load skeleton
        with open(skeleton_path, 'rb') as f:
            skeleton_data = pickle.load(f)
        
        keypoints_sequence = skeleton_data['keypoints']
        metadata = skeleton_data['metadata']
        camera_angle = skeleton_data.get('camera_angle', 'unknown')
        
        print(f"\nĐang xử lý người {person_id} (góc quay: {camera_angle})...")
        
        # Trích xuất profile cho người này
        profile_path = person_dir / "profile.json"
        profile = extract_features_from_keypoints_sequence(
            keypoints_sequence,
            metadata,
            profile_path
        )
        
        result['people'][person_id] = {
            'person_id': person_id,
            'profile_path': str(profile_path),
            'camera_angle': camera_angle,
            'num_frames': len(keypoints_sequence),
            'profile': profile
        }
        
        profiles.append(profile)
        print(f"  ✓ Đã tạo profile cho người {person_id}")
    
    # Tạo profile tổng hợp (trung bình)
    if create_combined and len(profiles) > 1:
        print("\nĐang tạo profile tổng hợp...")
        combined_profile = create_combined_profile(profiles, metadata)
        
        combined_path = template_dir / "combined_profile.json"
        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(combined_profile, f, indent=2, ensure_ascii=False)
        
        result['combined_profile'] = {
            'profile_path': str(combined_path),
            'profile': combined_profile
        }
        print(f"  ✓ Đã tạo profile tổng hợp: {combined_path}")
    
    # Lưu metadata tổng hợp
    summary_path = template_dir / "profiles_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Hoàn thành! Đã tạo profile cho {len(result['people'])} người")
    print(f"Summary: {summary_path}")
    
    return result


def extract_features_from_keypoints_sequence(
    keypoints_sequence: np.ndarray,
    metadata: Dict,
    output_path: Path = None
) -> Dict:
    """
    Trích xuất features từ keypoints sequence (cho một người)
    
    Args:
        keypoints_sequence: [n_frames, 17, 3]
        metadata: Video metadata
        output_path: Đường dẫn lưu profile
        
    Returns:
        Dict chứa profile
    """
    # Làm mượt skeleton
    print("  Đang làm mượt skeleton...")
    smoothed_skeletons = smooth_keypoints_sequence(keypoints_sequence)
    
    # Tính các đặc điểm cho từng frame
    features_per_frame = []
    
    print("  Đang tính toán đặc điểm hình học...")
    for frame_idx, skeleton in enumerate(smoothed_skeletons):
        features = calculate_frame_features(skeleton)
        features['frame_idx'] = frame_idx
        features['timestamp'] = frame_idx / metadata['fps']
        features_per_frame.append(features)
    
    # Tính giá trị trung bình và các thống kê
    profile = calculate_profile_statistics(features_per_frame, metadata)
    
    # Lưu profile nếu có output_path
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
    
    return profile


def create_combined_profile(profiles: List[Dict], metadata: Dict) -> Dict:
    """
    Tạo profile tổng hợp từ nhiều profiles (trung bình)
    
    Args:
        profiles: List các profile
        metadata: Video metadata
        
    Returns:
        Profile tổng hợp
    """
    if len(profiles) == 0:
        return {}
    
    combined = {
        'metadata': metadata,
        'num_profiles': len(profiles),
        'statistics': {}
    }
    
    # Tính trung bình cho từng thống kê
    stats_keys = ['arm_angle', 'leg_angle', 'arm_height', 'leg_height', 'head_angle']
    
    for key in stats_keys:
        if key not in profiles[0]['statistics']:
            continue
        
        stat = profiles[0]['statistics'][key]
        
        if isinstance(stat, dict):
            # Nested dict (arm_angle có left/right)
            combined['statistics'][key] = {}
            for sub_key in stat.keys():
                if isinstance(stat[sub_key], dict) and 'mean' in stat[sub_key]:
                    # Tính trung bình của mean
                    means = [p['statistics'][key][sub_key]['mean'] 
                            for p in profiles 
                            if key in p['statistics'] and sub_key in p['statistics'][key]
                            and p['statistics'][key][sub_key] is not None
                            and 'mean' in p['statistics'][key][sub_key]
                            and p['statistics'][key][sub_key]['mean'] is not None]
                    stds = [p['statistics'][key][sub_key]['std'] 
                           for p in profiles 
                           if key in p['statistics'] and sub_key in p['statistics'][key]
                           and p['statistics'][key][sub_key] is not None
                           and 'std' in p['statistics'][key][sub_key]
                           and p['statistics'][key][sub_key]['std'] is not None]
                    
                    if means:
                        combined['statistics'][key][sub_key] = {
                            'mean': float(np.mean(means)),
                            'std': float(np.mean(stds)) if stds else None
                        }
        elif isinstance(stat, dict) and 'mean' in stat:
            # Direct dict với mean/std
            means = [p['statistics'][key]['mean'] 
                    for p in profiles 
                    if key in p['statistics'] and p['statistics'][key] is not None
                    and 'mean' in p['statistics'][key]
                    and p['statistics'][key]['mean'] is not None]
            stds = [p['statistics'][key]['std'] 
                   for p in profiles 
                   if key in p['statistics'] and p['statistics'][key] is not None
                   and 'std' in p['statistics'][key]
                   and p['statistics'][key]['std'] is not None]
            
            if means:
                combined['statistics'][key] = {
                    'mean': float(np.mean(means)),
                    'std': float(np.mean(stds)) if stds else None
                }
    
    return combined


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
    import argparse
    
    parser = argparse.ArgumentParser(description="Trích xuất đặc điểm hình học")
    parser.add_argument('--skeleton-path', type=str, default=None,
                       help='Đường dẫn skeleton file (chế độ cũ)')
    parser.add_argument('--template-dir', type=str, default=None,
                       help='Thư mục template (chế độ mới - nhiều người)')
    parser.add_argument('--template-name', type=str, default=None,
                       help='Tên template (tự động tìm trong golden_template)')
    parser.add_argument('--no-combined', action='store_true',
                       help='Không tạo profile tổng hợp')
    
    args = parser.parse_args()
    
    try:
        if args.template_dir or args.template_name:
            # Chế độ mới: nhiều người
            if args.template_dir:
                template_dir = Path(args.template_dir)
            elif args.template_name:
                template_dir = config.GOLDEN_TEMPLATE_DIR / args.template_name
            else:
                # Tự động tìm template mới nhất
                template_dirs = [d for d in config.GOLDEN_TEMPLATE_DIR.iterdir() 
                               if d.is_dir() and (d / "metadata.json").exists()]
                if not template_dirs:
                    raise ValueError("Không tìm thấy template nào!")
                template_dir = max(template_dirs, key=lambda p: p.stat().st_mtime)
                print(f"Tự động chọn template: {template_dir.name}")
            
            if not template_dir.exists():
                raise ValueError(f"Không tìm thấy template: {template_dir}")
            
            result = extract_features_multi_person(
                template_dir,
                create_combined=not args.no_combined
            )
            
            print("\n✅ Hoàn thành Bước 2 (nhiều người)!")
            for person_id, info in result['people'].items():
                profile = info['profile']
                print(f"\nNgười {person_id}:")
                if 'arm_angle' in profile['statistics']:
                    print(f"  - Góc tay: {profile['statistics']['arm_angle']['left'].get('mean', 0):.2f}°")
                if 'leg_angle' in profile['statistics']:
                    print(f"  - Góc chân: {profile['statistics']['leg_angle']['left'].get('mean', 0):.2f}°")
        
        else:
            # Chế độ cũ: một người
            skeleton_path = config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_SKELETON_NAME
            
            if args.skeleton_path:
                skeleton_path = Path(args.skeleton_path)
            
            if not skeleton_path.exists():
                print(f"Không tìm thấy skeleton file: {skeleton_path}")
                print("Hãy chạy step1_golden_template.py trước!")
                sys.exit(1)
            
            # Load skeleton data
            with open(skeleton_path, 'rb') as f:
                skeleton_data = pickle.load(f)
            
            # Trích xuất features
            profile = extract_features_from_skeleton(skeleton_data)
            
            print("\n✅ Hoàn thành Bước 2!")
            print(f"Profile đã được lưu: {config.GOLDEN_TEMPLATE_DIR / config.GOLDEN_PROFILE_NAME}")
            print(f"\nThống kê:")
            if 'arm_angle' in profile['statistics']:
                print(f"- Góc tay trung bình: {profile['statistics']['arm_angle']['left']['mean']:.2f}°")
            if 'leg_angle' in profile['statistics']:
                print(f"- Góc chân trung bình: {profile['statistics']['leg_angle']['left']['mean']:.2f}°")
            if profile['statistics'].get('step_rhythm', {}).get('detected'):
                print(f"- Nhịp bước: {profile['statistics']['step_rhythm']['steps_per_minute']:.2f} bước/phút")
    
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

