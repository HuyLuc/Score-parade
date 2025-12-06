"""
BƯỚC 6: TÍNH ĐIỂM

Quy đổi sai lệch thành điểm số (0-10).
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
    
    # Điểm kỹ thuật tay (30%)
    arm_score = calculate_arm_score(summary)
    scores['arm_technique'] = arm_score
    
    # Điểm kỹ thuật chân (30%)
    leg_score = calculate_leg_score(summary)
    scores['leg_technique'] = leg_score
    
    # Điểm nhịp bước (20%) - cần thêm thông tin từ step4
    rhythm_score = 10.0  # Tạm thời, cần tính từ DTW distance
    scores['step_rhythm'] = rhythm_score
    
    # Điểm ổn định thân người (20%)
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
    """Tính điểm kỹ thuật tay"""
    if 'arm_angle' not in summary or 'arm_height' not in summary:
        return 10.0
    
    # Tính điểm từ góc tay
    arm_angle_errors = []
    if 'left' in summary['arm_angle']:
        arm_angle_errors.append(summary['arm_angle']['left']['mean'])
    if 'right' in summary['arm_angle']:
        arm_angle_errors.append(summary['arm_angle']['right']['mean'])
    
    angle_score = 10.0
    if arm_angle_errors:
        avg_angle_error = np.mean(arm_angle_errors)
        threshold = config.ERROR_THRESHOLDS['arm_angle']
        if config.SCORING_FORMULA == 'exponential':
            angle_score = 10.0 * np.exp(-avg_angle_error / threshold)
        else:  # linear
            angle_score = max(0, 10.0 - (avg_angle_error / threshold) * 10.0)
    
    # Tính điểm từ độ cao tay
    arm_height_errors = []
    if 'left' in summary['arm_height']:
        arm_height_errors.append(summary['arm_height']['left']['mean'])
    if 'right' in summary['arm_height']:
        arm_height_errors.append(summary['arm_height']['right']['mean'])
    
    height_score = 10.0
    if arm_height_errors:
        avg_height_error = np.mean(arm_height_errors)
        threshold = config.ERROR_THRESHOLDS['arm_height']
        if config.SCORING_FORMULA == 'exponential':
            height_score = 10.0 * np.exp(-avg_height_error / threshold)
        else:  # linear
            height_score = max(0, 10.0 - (avg_height_error / threshold) * 10.0)
    
    # Trung bình có trọng số (góc quan trọng hơn)
    return (angle_score * 0.6 + height_score * 0.4)


def calculate_leg_score(summary: Dict) -> float:
    """Tính điểm kỹ thuật chân"""
    if 'leg_angle' not in summary or 'leg_height' not in summary:
        return 10.0
    
    # Tính điểm từ góc chân
    leg_angle_errors = []
    if 'left' in summary['leg_angle']:
        leg_angle_errors.append(summary['leg_angle']['left']['mean'])
    if 'right' in summary['leg_angle']:
        leg_angle_errors.append(summary['leg_angle']['right']['mean'])
    
    angle_score = 10.0
    if leg_angle_errors:
        avg_angle_error = np.mean(leg_angle_errors)
        threshold = config.ERROR_THRESHOLDS['leg_angle']
        if config.SCORING_FORMULA == 'exponential':
            angle_score = 10.0 * np.exp(-avg_angle_error / threshold)
        else:  # linear
            angle_score = max(0, 10.0 - (avg_angle_error / threshold) * 10.0)
    
    # Tính điểm từ độ cao chân
    leg_height_errors = []
    if 'left' in summary['leg_height']:
        leg_height_errors.append(summary['leg_height']['left']['mean'])
    if 'right' in summary['leg_height']:
        leg_height_errors.append(summary['leg_height']['right']['mean'])
    
    height_score = 10.0
    if leg_height_errors:
        avg_height_error = np.mean(leg_height_errors)
        threshold = config.ERROR_THRESHOLDS['leg_height']
        if config.SCORING_FORMULA == 'exponential':
            height_score = 10.0 * np.exp(-avg_height_error / threshold)
        else:  # linear
            height_score = max(0, 10.0 - (avg_height_error / threshold) * 10.0)
    
    # Trung bình có trọng số
    return (angle_score * 0.6 + height_score * 0.4)


def calculate_stability_score(summary: Dict) -> float:
    """Tính điểm ổn định thân người"""
    # Dựa trên head_angle error (đầu cúi/ngẩng)
    if 'head_angle' not in summary:
        return 10.0
    
    head_error = summary['head_angle']['mean']
    threshold = config.ERROR_THRESHOLDS['head_angle']
    
    if config.SCORING_FORMULA == 'exponential':
        return 10.0 * np.exp(-head_error / threshold)
    else:  # linear
        return max(0, 10.0 - (head_error / threshold) * 10.0)


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

