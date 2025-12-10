"""
BƯỚC 7: XUẤT LỖI CHO HUẤN LUYỆN VIÊN

Tạo báo cáo trực quan về lỗi sai.
"""
import pickle
import json
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List
import src.config as config
from src.utils.video_utils import load_video, get_frames, save_video


def create_visualization(
    video_path: Path,
    aligned_skeleton_path: Path,
    errors_path: Path,
    score_path: Path,
    golden_skeleton_path: Path,
    output_dir: Path = None
) -> Dict:
    """
    Tạo video visualization với annotations và báo cáo
    
    Args:
        video_path: Đường dẫn video gốc
        aligned_skeleton_path: Đường dẫn skeleton đã align
        errors_path: Đường dẫn errors từ step5
        score_path: Đường dẫn score từ step6
        golden_skeleton_path: Đường dẫn golden skeleton
        output_dir: Thư mục output
        
    Returns:
        Dict chứa đường dẫn các file output
    """
    # Load data
    with open(aligned_skeleton_path, 'rb') as f:
        aligned_data = pickle.load(f)
    person_id = aligned_data['person_id']
    aligned_keypoints = aligned_data['aligned_keypoints']
    frame_indices = aligned_data.get('frame_indices', None)  # Lấy frame indices nếu có
    
    with open(errors_path, 'r', encoding='utf-8') as f:
        errors_data = json.load(f)
    
    with open(score_path, 'r', encoding='utf-8') as f:
        score_data = json.load(f)
    
    with open(golden_skeleton_path, 'rb') as f:
        golden_data = pickle.load(f)
    golden_keypoints = np.array(golden_data['valid_skeletons'])
    
    # Tạo output directory
    if output_dir is None:
        output_dir = Path(video_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Tạo annotated video
    annotated_video_path = output_dir / f"person_{person_id}_annotated.mp4"
    create_annotated_video(
        video_path,
        aligned_keypoints,
        frame_indices,  # Truyền frame indices
        golden_keypoints,
        errors_data['errors_per_frame'],
        score_data,
        annotated_video_path
    )
    
    # Tạo báo cáo HTML
    report_html_path = output_dir / f"person_{person_id}_report.html"
    create_html_report(
        errors_data,
        score_data,
        person_id,
        report_html_path
    )
    
    # Tạo báo cáo JSON tổng hợp
    report_json_path = output_dir / f"person_{person_id}_report.json"
    create_json_report(
        errors_data,
        score_data,
        person_id,
        report_json_path
    )
    
    print(f"\n✅ Hoàn thành Bước 7!")
    print(f"Annotated video: {annotated_video_path}")
    print(f"HTML report: {report_html_path}")
    print(f"JSON report: {report_json_path}")
    
    return {
        'annotated_video': annotated_video_path,
        'html_report': report_html_path,
        'json_report': report_json_path
    }


def create_annotated_video(
    video_path: Path,
    person_keypoints: np.ndarray,
    frame_indices: np.ndarray,
    golden_keypoints: np.ndarray,
    errors_per_frame: List[Dict],
    score_data: Dict,
    output_path: Path
):
    """
    Tạo video với skeleton và annotations
    
    Args:
        person_keypoints: Keypoints của người [n_tracked_frames, 17, 3]
        frame_indices: Frame indices tương ứng với keypoints [n_tracked_frames]
        golden_keypoints: Golden skeleton
        errors_per_frame: Lỗi từng frame
        score_data: Điểm số
        output_path: Đường dẫn output
    """
    cap, metadata = load_video(video_path)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(
        str(output_path),
        fourcc,
        metadata['fps'],
        (metadata['width'], metadata['height'])
    )
    
    # Connections cho skeleton
    connections = [
        (0, 1), (0, 2), (1, 3), (2, 4),
        (5, 6),
        (5, 7), (7, 9),
        (6, 8), (8, 10),
        (5, 11), (6, 12),
        (11, 12),
        (11, 13), (13, 15),
        (12, 14), (14, 16),
    ]
    
    # Tạo mapping từ frame_idx -> keypoint_idx
    frame_to_kpt = {}
    if frame_indices is not None and len(frame_indices) > 0:
        for kpt_idx, frame_idx in enumerate(frame_indices):
            frame_to_kpt[int(frame_idx)] = kpt_idx
        
        # Tìm frame đầu và cuối
        min_frame = int(np.min(frame_indices))
        max_frame = int(np.max(frame_indices))
        print(f"Person xuất hiện từ frame {min_frame} đến {max_frame}")
    else:
        # Fallback: vẽ skeleton cho tất cả frames
        min_frame = 0
        max_frame = len(person_keypoints) - 1
        for kpt_idx in range(len(person_keypoints)):
            frame_to_kpt[kpt_idx] = kpt_idx
        print(f"Không có frame_indices, vẽ skeleton cho {len(person_keypoints)} frames đầu")
    
    def find_nearest_keypoint(video_frame_idx):
        """Tìm keypoint gần nhất với frame hiện tại"""
        if video_frame_idx in frame_to_kpt:
            return frame_to_kpt[video_frame_idx]
        
        # Tìm frame gần nhất trong frame_to_kpt
        available_frames = sorted(frame_to_kpt.keys())
        if not available_frames:
            return None
        
        # Nếu frame hiện tại nằm ngoài range, không vẽ
        if video_frame_idx < available_frames[0] or video_frame_idx > available_frames[-1]:
            return None
        
        # Tìm frame gần nhất
        closest_frame = min(available_frames, key=lambda x: abs(x - video_frame_idx))
        
        # Chỉ dùng nếu khoảng cách < 5 frames (tránh nhảy quá xa)
        if abs(closest_frame - video_frame_idx) <= 5:
            return frame_to_kpt[closest_frame]
        
        return None
    
    video_frame_idx = 0
    for frame in get_frames(cap):
        vis_frame = frame.copy()
        
        # Vẽ skeleton person (màu xanh)
        kpt_idx = find_nearest_keypoint(video_frame_idx)
        if kpt_idx is not None and kpt_idx < len(person_keypoints):
            draw_skeleton(
                vis_frame,
                person_keypoints[kpt_idx],
                connections,
                (0, 255, 0),
                2
            )
            
            # Vẽ annotations lỗi
            if kpt_idx < len(errors_per_frame):
                draw_error_annotations(
                    vis_frame,
                    errors_per_frame[kpt_idx],
                    person_keypoints[kpt_idx]
                )
        
        # Vẽ skeleton golden (màu vàng, mờ) - repeat nếu golden ngắn hơn
        golden_idx = video_frame_idx % len(golden_keypoints)
        draw_skeleton(
            vis_frame,
            golden_keypoints[golden_idx],
            connections,
            (0, 255, 255),
            1,
            alpha=0.3
        )
        
        # Vẽ điểm số ở góc trên
        draw_score(vis_frame, score_data)
        
        out.write(vis_frame)
        video_frame_idx += 1
    
    cap.release()
    out.release()


def draw_skeleton(
    frame: np.ndarray,
    keypoints: np.ndarray,
    connections: List[tuple],
    color: tuple,
    thickness: int,
    alpha: float = 1.0
):
    """Vẽ skeleton lên frame"""
    overlay = frame.copy()
    
    # Vẽ connections
    for start_idx, end_idx in connections:
        if (start_idx < len(keypoints) and end_idx < len(keypoints) and
            keypoints[start_idx][2] > 0 and keypoints[end_idx][2] > 0):
            pt1 = (int(keypoints[start_idx][0]), int(keypoints[start_idx][1]))
            pt2 = (int(keypoints[end_idx][0]), int(keypoints[end_idx][1]))
            cv2.line(overlay, pt1, pt2, color, thickness)
    
    # Vẽ keypoints
    for i, kpt in enumerate(keypoints):
        if kpt[2] > 0:
            x, y = int(kpt[0]), int(kpt[1])
            cv2.circle(overlay, (x, y), 5, color, -1)
    
    if alpha < 1.0:
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    else:
        frame[:] = overlay[:]


def draw_error_annotations(
    frame: np.ndarray,
    errors: Dict,
    keypoints: np.ndarray = None
):
    """Vẽ annotations lỗi lên frame"""
    y_offset = 30
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1
    
    # Màu sắc theo mức độ lỗi
    def get_error_color(error_value, threshold):
        if error_value > threshold * 2:
            return config.VIS_CONFIG['error_colors']['severe']
        elif error_value > threshold:
            return config.VIS_CONFIG['error_colors']['moderate']
        elif error_value > threshold * 0.5:
            return config.VIS_CONFIG['error_colors']['minor']
        else:
            return config.VIS_CONFIG['error_colors']['good']
    
    # Arm angle error
    if 'left' in errors.get('arm_angle_error', {}):
        error = errors['arm_angle_error']['left']
        color = get_error_color(error, config.ERROR_THRESHOLDS['arm_angle'])
        text = f"Tay trai: {error:.1f}°"
        cv2.putText(frame, text, (10, y_offset), font, font_scale, color, thickness)
        y_offset += 20
    
    # Leg angle error
    if 'left' in errors.get('leg_angle_error', {}):
        error = errors['leg_angle_error']['left']
        color = get_error_color(error, config.ERROR_THRESHOLDS['leg_angle'])
        text = f"Chan trai: {error:.1f}°"
        cv2.putText(frame, text, (10, y_offset), font, font_scale, color, thickness)
        y_offset += 20
    
    # Head angle error
    if errors.get('head_angle_error') is not None:
        error = errors['head_angle_error']
        color = get_error_color(error, config.ERROR_THRESHOLDS['head_angle'])
        text = f"Dau: {error:.1f}°"
        cv2.putText(frame, text, (10, y_offset), font, font_scale, color, thickness)


def draw_score(frame: np.ndarray, score_data: Dict):
    """Vẽ điểm số ở góc trên bên phải"""
    total_score = score_data['total_score']
    grade = score_data['grade']
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    thickness = 2
    
    # Màu theo điểm
    if total_score >= 8:
        color = (0, 255, 0)  # Xanh
    elif total_score >= 6:
        color = (0, 255, 255)  # Vàng
    else:
        color = (0, 0, 255)  # Đỏ
    
    text = f"{total_score:.1f}/10 - {grade}"
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    
    x = frame.shape[1] - text_size[0] - 10
    y = 30
    
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)


def create_html_report(
    errors_data: Dict,
    score_data: Dict,
    person_id: int,
    output_path: Path
):
    """Tạo báo cáo HTML"""
    summary = errors_data['summary']
    total_score = score_data['total_score']
    grade = score_data['grade']
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Báo cáo đánh giá - Người {person_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .score {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
        .grade {{ font-size: 18px; color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .error-high {{ background-color: #ffcccc; }}
        .error-medium {{ background-color: #fff4cc; }}
        .error-low {{ background-color: #ccffcc; }}
    </style>
</head>
<body>
    <h1>Báo cáo đánh giá điều lệnh - Người {person_id}</h1>
    
    <div class="score">Điểm tổng: {total_score:.2f}/10</div>
    <div class="grade">Xếp loại: {grade}</div>
    
    <h2>Chi tiết điểm số</h2>
    <table>
        <tr>
            <th>Yếu tố</th>
            <th>Điểm</th>
            <th>Trọng số</th>
        </tr>
        <tr>
            <td>Kỹ thuật tay</td>
            <td>{score_data['breakdown']['arm_technique']:.2f}</td>
            <td>{config.SCORING_WEIGHTS['arm_technique']*100:.0f}%</td>
        </tr>
        <tr>
            <td>Kỹ thuật chân</td>
            <td>{score_data['breakdown']['leg_technique']:.2f}</td>
            <td>{config.SCORING_WEIGHTS['leg_technique']*100:.0f}%</td>
        </tr>
        <tr>
            <td>Nhịp bước</td>
            <td>{score_data['breakdown']['step_rhythm']:.2f}</td>
            <td>{config.SCORING_WEIGHTS['step_rhythm']*100:.0f}%</td>
        </tr>
        <tr>
            <td>Ổn định thân</td>
            <td>{score_data['breakdown']['torso_stability']:.2f}</td>
            <td>{config.SCORING_WEIGHTS['torso_stability']*100:.0f}%</td>
        </tr>
    </table>
    
    <h2>Chi tiết lỗi</h2>
    <table>
        <tr>
            <th>Yếu tố</th>
            <th>Sai lệch trung bình</th>
            <th>Sai lệch lớn nhất</th>
            <th>Ngưỡng</th>
        </tr>
"""
    
    # Thêm các dòng lỗi
    if 'arm_angle' in summary:
        mean_error = summary['arm_angle']['left'].get('mean', 0)
        max_error = summary['arm_angle']['left'].get('max', 0)
        threshold = config.ERROR_THRESHOLDS['arm_angle']
        error_class = 'error-high' if mean_error > threshold else ('error-medium' if mean_error > threshold*0.5 else 'error-low')
        html += f"""
        <tr class="{error_class}">
            <td>Góc tay</td>
            <td>{mean_error:.2f}°</td>
            <td>{max_error:.2f}°</td>
            <td>{threshold}°</td>
        </tr>
"""
    
    if 'leg_angle' in summary:
        mean_error = summary['leg_angle']['left'].get('mean', 0)
        max_error = summary['leg_angle']['left'].get('max', 0)
        threshold = config.ERROR_THRESHOLDS['leg_angle']
        error_class = 'error-high' if mean_error > threshold else ('error-medium' if mean_error > threshold*0.5 else 'error-low')
        html += f"""
        <tr class="{error_class}">
            <td>Góc chân</td>
            <td>{mean_error:.2f}°</td>
            <td>{max_error:.2f}°</td>
            <td>{threshold}°</td>
        </tr>
"""
    
    if 'head_angle' in summary:
        mean_error = summary['head_angle'].get('mean', 0)
        max_error = summary['head_angle'].get('max', 0)
        threshold = config.ERROR_THRESHOLDS['head_angle']
        error_class = 'error-high' if mean_error > threshold else ('error-medium' if mean_error > threshold*0.5 else 'error-low')
        html += f"""
        <tr class="{error_class}">
            <td>Góc đầu</td>
            <td>{mean_error:.2f}°</td>
            <td>{max_error:.2f}°</td>
            <td>{threshold}°</td>
        </tr>
"""
    
    html += """
    </table>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)


def create_json_report(
    errors_data: Dict,
    score_data: Dict,
    person_id: int,
    output_path: Path
):
    """Tạo báo cáo JSON tổng hợp"""
    report = {
        'person_id': person_id,
        'score': score_data,
        'errors_summary': errors_data['summary'],
        'recommendations': generate_recommendations(errors_data['summary'], score_data)
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def generate_recommendations(summary: Dict, score_data: Dict) -> List[str]:
    """Tạo các khuyến nghị cải thiện"""
    recommendations = []
    
    if 'arm_angle' in summary:
        mean_error = summary['arm_angle']['left'].get('mean', 0)
        if mean_error > config.ERROR_THRESHOLDS['arm_angle']:
            recommendations.append(f"Tay lệch góc trung bình {mean_error:.1f}° - Cần điều chỉnh góc tay")
    
    if 'leg_angle' in summary:
        mean_error = summary['leg_angle']['left'].get('mean', 0)
        if mean_error > config.ERROR_THRESHOLDS['leg_angle']:
            recommendations.append(f"Chân lệch góc trung bình {mean_error:.1f}° - Cần điều chỉnh góc chân")
    
    if 'head_angle' in summary:
        mean_error = summary['head_angle'].get('mean', 0)
        if mean_error > config.ERROR_THRESHOLDS['head_angle']:
            recommendations.append(f"Đầu lệch góc trung bình {mean_error:.1f}° - Cần ngẩng đầu thẳng")
    
    if score_data['total_score'] < 6:
        recommendations.append("Điểm tổng thấp - Cần luyện tập thêm để cải thiện")
    
    return recommendations


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 6:
        print("Usage: python step7_visualization.py <video_path> <aligned_skeleton> <errors> <score> <golden_skeleton>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    aligned_skeleton_path = Path(sys.argv[2])
    errors_path = Path(sys.argv[3])
    score_path = Path(sys.argv[4])
    golden_skeleton_path = Path(sys.argv[5])
    
    try:
        result = create_visualization(
            video_path,
            aligned_skeleton_path,
            errors_path,
            score_path,
            golden_skeleton_path
        )
        print(f"\n✅ Hoàn thành Bước 7!")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

