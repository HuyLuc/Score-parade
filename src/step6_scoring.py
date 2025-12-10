"""
BƯỚC 6: TÍNH ĐIỂM

Quy đổi sai lệch thành điểm số (0-10).

CẢI TIẾN: Chỉ dùng GÓC (angle), bỏ HEIGHT (không bất biến với camera)
"""
import json
import numpy as np
from pathlib import Path
from typing import Dict
import src.config as config


def calculate_score(
    errors_path: Path,
    output_path: Path = None
) -> Dict:
    """
    Tính điểm dựa trên error metrics
    
    Args:
        errors_path: Đường dẫn file errors từ step5
        output_path: Đường dẫn lưu kết quả điểm
        
    Returns:
        Dict chứa điểm số và breakdown
    """
    # Load errors
    with open(errors_path, 'r', encoding='utf-8') as f:
        errors_data = json.load(f)
    
    summary = errors_data['summary']
    
    # Tính điểm cho từng yếu tố
    scores = {}
    
    # Điểm kỹ thuật tay (40% - CHỈ TỪ GÓC)
    arm_score = calculate_arm_score(summary)
    scores['arm_technique'] = arm_score
    
    # Điểm kỹ thuật chân (40% - CHỈ TỪ GÓC)
    leg_score = calculate_leg_score(summary)
    scores['leg_technique'] = leg_score
    
    # Điểm nhịp bước (10%)
    rhythm_score = 10.0  # Tạm thời, cần tính từ DTW distance
    scores['step_rhythm'] = rhythm_score
    
    # Điểm ổn định thân người (10%)
    stability_score = calculate_stability_score(summary)
    scores['torso_stability'] = stability_score
    
    # Tính điểm tổng với trọng số
    total_score = (
        scores['arm_technique'] * config.SCORING_WEIGHTS['arm_technique'] +
        scores['leg_technique'] * config.SCORING_WEIGHTS['leg_technique'] +
        scores['step_rhythm'] * config.SCORING_WEIGHTS['step_rhythm'] +
        scores['torso_stability'] * config.SCORING_WEIGHTS['torso_stability']
    )
    
    # Lưu kết quả
    if output_path is None:
        output_dir = errors_path.parent
        person_id = errors_data['person_id']
        output_path = output_dir / f"person_{person_id}_score.json"
    
    result = {
        'person_id': errors_data['person_id'],
        'total_score': float(total_score),
        'max_score': config.SCORING_MAX_POINTS,
        'breakdown': scores,
        'weights': config.SCORING_WEIGHTS,
        'grade': get_grade(total_score)
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Đã lưu điểm số: {output_path}")
    print(f"\nĐiểm tổng: {total_score:.2f}/10")
    print(f"Breakdown:")
    print(f"  - Kỹ thuật tay: {scores['arm_technique']:.2f}")
    print(f"  - Kỹ thuật chân: {scores['leg_technique']:.2f}")
    print(f"  - Nhịp bước: {scores['step_rhythm']:.2f}")
    print(f"  - Ổn định thân: {scores['torso_stability']:.2f}")
    
    return result


def calculate_arm_score(summary: Dict) -> float:
    """
    Tính điểm kỹ thuật tay - CHỈ TỪ GÓC (bỏ height)
    
    Lý do: arm_height phụ thuộc góc quay camera, không đáng tin cậy
    Góc tay (shoulder-elbow-wrist) là bất biến, chính xác hơn
    """
    if 'arm_angle' not in summary:
        return 10.0
    
    # Tính điểm từ góc tay (DUY NHẤT)
    arm_angle_errors = []
    if 'left' in summary['arm_angle']:
        arm_angle_errors.append(abs(summary['arm_angle']['left']['mean']))
    if 'right' in summary['arm_angle']:
        arm_angle_errors.append(abs(summary['arm_angle']['right']['mean']))
    
    if not arm_angle_errors:
        return 10.0
    
    avg_angle_error = np.mean(arm_angle_errors)
    threshold = config.ERROR_THRESHOLDS['arm_angle']
    decay_rate = config.SCORING_DECAY_RATE if hasattr(config, 'SCORING_DECAY_RATE') else 1.0
    
    if config.SCORING_FORMULA == 'exponential':
        # Công thức mới: score = 10 * exp(-error * decay_rate / threshold)
        score = 10.0 * np.exp(-avg_angle_error * decay_rate / threshold)
    else:  # linear
        score = max(0, 10.0 * (1 - avg_angle_error / threshold))
    
    return float(score)


def calculate_leg_score(summary: Dict) -> float:
    """
    Tính điểm kỹ thuật chân - CHỈ TỪ GÓC (bỏ height)
    
    Lý do: leg_height phụ thuộc góc quay camera, không đáng tin cậy
    Góc chân (hip-knee-ankle) là bất biến, chính xác hơn
    """
    if 'leg_angle' not in summary:
        return 10.0
    
    # Tính điểm từ góc chân (DUY NHẤT)
    leg_angle_errors = []
    if 'left' in summary['leg_angle']:
        leg_angle_errors.append(abs(summary['leg_angle']['left']['mean']))
    if 'right' in summary['leg_angle']:
        leg_angle_errors.append(abs(summary['leg_angle']['right']['mean']))
    
    if not leg_angle_errors:
        return 10.0
    
    avg_angle_error = np.mean(leg_angle_errors)
    threshold = config.ERROR_THRESHOLDS['leg_angle']
    decay_rate = config.SCORING_DECAY_RATE if hasattr(config, 'SCORING_DECAY_RATE') else 1.0
    
    if config.SCORING_FORMULA == 'exponential':
        # Công thức mới: score = 10 * exp(-error * decay_rate / threshold)
        score = 10.0 * np.exp(-avg_angle_error * decay_rate / threshold)
    else:  # linear
        score = max(0, 10.0 * (1 - avg_angle_error / threshold))
    
    return float(score)


def calculate_stability_score(summary: Dict) -> float:
    """Tính điểm ổn định thân người (dùng head_angle)"""
    # Dựa trên head_angle error (đầu cúi/ngẩng)
    if 'head_angle' not in summary:
        return 10.0
    
    head_error = abs(summary['head_angle']['mean'])
    threshold = config.ERROR_THRESHOLDS['head_angle']
    decay_rate = config.SCORING_DECAY_RATE if hasattr(config, 'SCORING_DECAY_RATE') else 1.0
    
    if config.SCORING_FORMULA == 'exponential':
        return float(10.0 * np.exp(-head_error * decay_rate / threshold))
    else:  # linear
        return float(max(0, 10.0 * (1 - head_error / threshold)))


def get_grade(score: float) -> str:
    """Chuyển điểm số thành xếp loại"""
    if score >= 9.0:
        return "Xuất sắc"
    elif score >= 8.0:
        return "Giỏi"
    elif score >= 7.0:
        return "Khá"
    elif score >= 6.0:
        return "Trung bình"
    elif score >= 5.0:
        return "Trung bình yếu"
    else:
        return "Yếu"


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python step6_scoring.py <errors_path>")
        sys.exit(1)
    
    errors_path = Path(sys.argv[1])
    if not errors_path.exists():
        print(f"Không tìm thấy errors file: {errors_path}")
        sys.exit(1)
    
    try:
        result = calculate_score(errors_path)
        print(f"\n✅ Hoàn thành Bước 6!")
        print(f"Xếp loại: {result['grade']}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
