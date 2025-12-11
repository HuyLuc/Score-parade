"""
Script đơn giản để:
1. Tạo golden template từ video (phân tích đặc trưng)
2. Đánh giá video test so với golden template
"""
import sys
from pathlib import Path
import numpy as np
import json
import pickle
from typing import List, Dict
import cv2

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.pose_service import PoseService
from backend.app.services.video_utils import load_video, get_frames
from backend.app.services.geometry import (
    calculate_arm_angle, calculate_leg_angle,
    calculate_arm_height, calculate_leg_height,
    calculate_head_angle, calculate_torso_stability
)
from backend.app.controllers.ai_controller import AIController
from backend.app.services.scoring_service import ScoringService
from backend.app.config import GOLDEN_TEMPLATE_DIR, INPUT_VIDEOS_DIR, OUTPUT_DIR


def create_golden_template(video_path: Path, output_dir: Path = None):
    """
    Tạo golden template từ video
    
    Args:
        video_path: Đường dẫn video golden
        output_dir: Thư mục lưu output (mặc định: data/golden_template)
    """
    if output_dir is None:
        output_dir = GOLDEN_TEMPLATE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📹 Đang xử lý video golden: {video_path}")
    
    # Load video
    cap, metadata = load_video(video_path)
    print(f"   FPS: {metadata['fps']}, Kích thước: {metadata['width']}x{metadata['height']}")
    
    # Khởi tạo pose service
    pose_service = PoseService()
    
    # Lưu trữ keypoints và đặc trưng
    all_keypoints = []
    features = {
        "arm_angle": {"left": [], "right": []},
        "leg_angle": {"left": [], "right": []},
        "arm_height": {"left": [], "right": []},
        "leg_height": {"left": [], "right": []},
        "head_angle": [],
        "torso_stability": []
    }
    
    frame_count = 0
    valid_frames = 0
    
    print("   Đang phân tích từng frame...")
    for frame in get_frames(cap):
        frame_count += 1
        
        # Detect pose
        keypoints_list = pose_service.predict(frame)
        
        if len(keypoints_list) == 0:
            continue
        
        # Lấy người đầu tiên
        keypoints = keypoints_list[0]
        
        # Kiểm tra keypoints hợp lệ (có đủ 17 keypoints và confidence)
        if keypoints.shape[0] < 17 or keypoints.shape[1] < 3:
            continue
        
        # Lưu keypoints
        all_keypoints.append(keypoints.copy())
        
        # Tính toán đặc trưng
        # Góc tay
        left_arm_angle = calculate_arm_angle(keypoints, "left")
        right_arm_angle = calculate_arm_angle(keypoints, "right")
        if left_arm_angle is not None:
            features["arm_angle"]["left"].append(left_arm_angle)
        if right_arm_angle is not None:
            features["arm_angle"]["right"].append(right_arm_angle)
        
        # Góc chân
        left_leg_angle = calculate_leg_angle(keypoints, "left")
        right_leg_angle = calculate_leg_angle(keypoints, "right")
        if left_leg_angle is not None:
            features["leg_angle"]["left"].append(left_leg_angle)
        if right_leg_angle is not None:
            features["leg_angle"]["right"].append(right_leg_angle)
        
        # Độ cao tay
        left_arm_h = calculate_arm_height(keypoints, "left")
        right_arm_h = calculate_arm_height(keypoints, "right")
        if left_arm_h is not None:
            features["arm_height"]["left"].append(left_arm_h)
        if right_arm_h is not None:
            features["arm_height"]["right"].append(right_arm_h)
        
        # Độ cao chân
        left_leg_h = calculate_leg_height(keypoints, "left")
        right_leg_h = calculate_leg_height(keypoints, "right")
        if left_leg_h is not None:
            features["leg_height"]["left"].append(left_leg_h)
        if right_leg_h is not None:
            features["leg_height"]["right"].append(right_leg_h)
        
        # Góc đầu
        head_angle = calculate_head_angle(keypoints)
        if head_angle is not None:
            features["head_angle"].append(head_angle)
        
        # Ổn định thân - sẽ tính sau khi có đủ frames
        # (torso_stability cần nhiều frames để tính variance)
        
        valid_frames += 1
        
        if frame_count % 30 == 0:
            print(f"   Đã xử lý {frame_count} frames...")
    
    cap.release()
    
    if valid_frames == 0:
        print("❌ Không tìm thấy người nào trong video!")
        return None
    
    print(f"✅ Đã phân tích {valid_frames}/{frame_count} frames hợp lệ")
    
    # Tính torso_stability sau khi có đủ keypoints
    if len(all_keypoints) > 1:
        try:
            keypoints_array = np.array(all_keypoints)  # [n_frames, 17, 3]
            torso_stab = calculate_torso_stability(keypoints_array)
            if torso_stab is not None:
                features["torso_stability"].append(torso_stab)
        except Exception as e:
            print(f"   Cảnh báo: Không thể tính torso_stability: {e}")
    
    # Tính thống kê (mean, std) cho mỗi đặc trưng
    statistics = {}
    for feature_name, feature_data in features.items():
        if isinstance(feature_data, dict):
            statistics[feature_name] = {}
            for side, values in feature_data.items():
                if len(values) > 0:
                    statistics[feature_name][side] = {
                        "mean": float(np.mean(values)),
                        "std": float(np.std(values)),
                        "min": float(np.min(values)),
                        "max": float(np.max(values)),
                        "count": len(values)
                    }
        else:
            if len(feature_data) > 0:
                statistics[feature_name] = {
                    "mean": float(np.mean(feature_data)),
                    "std": float(np.std(feature_data)),
                    "min": float(np.min(feature_data)),
                    "max": float(np.max(feature_data)),
                    "count": len(feature_data)
                }
    
    # Tạo golden profile
    golden_profile = {
        "video_path": str(video_path),
        "metadata": metadata,
        "statistics": statistics,
        "total_frames": frame_count,
        "valid_frames": valid_frames
    }
    
    # Lưu golden profile
    profile_path = output_dir / "golden_profile.json"
    with open(profile_path, 'w', encoding='utf-8') as f:
        json.dump(golden_profile, f, indent=2, ensure_ascii=False)
    print(f"✅ Đã lưu golden profile: {profile_path}")
    
    # Lưu keypoints
    skeleton_path = output_dir / "golden_skeleton.pkl"
    with open(skeleton_path, 'wb') as f:
        pickle.dump({
            "keypoints": np.array(all_keypoints),
            "valid_skeletons": np.array(all_keypoints)
        }, f)
    print(f"✅ Đã lưu golden skeleton: {skeleton_path}")
    
    return golden_profile


def evaluate_video(test_video_path: Path, golden_template_dir: Path = None):
    """
    Đánh giá video test so với golden template
    
    Args:
        test_video_path: Đường dẫn video test
        golden_template_dir: Thư mục chứa golden template (mặc định: data/golden_template)
    """
    if golden_template_dir is None:
        golden_template_dir = GOLDEN_TEMPLATE_DIR
    
    print(f"\n📹 Đang đánh giá video test: {test_video_path}")
    
    # Kiểm tra golden template
    profile_path = golden_template_dir / "golden_profile.json"
    if not profile_path.exists():
        print(f"❌ Không tìm thấy golden profile: {profile_path}")
        print("   Hãy chạy tạo golden template trước!")
        return None
    
    # Load video test
    cap, metadata = load_video(test_video_path)
    print(f"   FPS: {metadata['fps']}, Kích thước: {metadata['width']}x{metadata['height']}")
    
    # Khởi tạo services
    pose_service = PoseService()
    ai_controller = AIController(pose_service)
    scoring_service = ScoringService()
    
    # Load golden template
    ai_controller.load_golden_template()
    if ai_controller.golden_profile is None:
        print("⚠️ Cảnh báo: Không load được golden profile, sẽ dùng ngưỡng mặc định")
    else:
        print("✅ Đã load golden template")
    
    # Phát hiện lỗi từng frame
    all_errors = []
    frame_count = 0
    valid_frames = 0
    
    print("   Đang phân tích từng frame...")
    for frame in get_frames(cap):
        frame_count += 1
        
        # Detect pose
        keypoints_list = pose_service.predict(frame)
        
        if len(keypoints_list) == 0:
            continue
        
        keypoints = keypoints_list[0]
        
        if keypoints.shape[0] < 17 or keypoints.shape[1] < 3:
            continue
        
        # Phát hiện lỗi
        errors = ai_controller.detect_posture_errors(
            keypoints=keypoints,
            frame_number=frame_count,
            timestamp=frame_count / metadata['fps']
        )
        
        all_errors.extend(errors)
        valid_frames += 1
        
        if frame_count % 30 == 0:
            print(f"   Đã xử lý {frame_count} frames, phát hiện {len(all_errors)} lỗi...")
    
    cap.release()
    
    if valid_frames == 0:
        print("❌ Không tìm thấy người nào trong video!")
        return None
    
    print(f"✅ Đã phân tích {valid_frames}/{frame_count} frames hợp lệ")
    print(f"   Tổng số lỗi phát hiện: {len(all_errors)}")
    
    # Tính điểm
    total_deduction = sum(error.get("deduction", 0.0) for error in all_errors)
    initial_score = scoring_service.initial_score
    final_score = max(0.0, initial_score - total_deduction)
    is_passed = scoring_service.is_passed(final_score)
    
    # Tổng hợp kết quả
    result = {
        "video_path": str(test_video_path),
        "metadata": metadata,
        "total_frames": frame_count,
        "valid_frames": valid_frames,
        "initial_score": initial_score,
        "total_deduction": float(total_deduction),
        "final_score": float(final_score),
        "is_passed": is_passed,
        "total_errors": len(all_errors),
        "errors_by_type": {}
    }
    
    # Nhóm lỗi theo type
    for error in all_errors:
        error_type = error.get("type", "unknown")
        if error_type not in result["errors_by_type"]:
            result["errors_by_type"][error_type] = 0
        result["errors_by_type"][error_type] += 1
    
    # Lưu kết quả
    output_dir = OUTPUT_DIR / test_video_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result_path = output_dir / "evaluation_result.json"
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"✅ Đã lưu kết quả: {result_path}")
    
    # In kết quả
    print("\n" + "="*60)
    print("KẾT QUẢ ĐÁNH GIÁ")
    print("="*60)
    print(f"Video: {test_video_path.name}")
    print(f"Điểm ban đầu: {initial_score:.2f}")
    print(f"Tổng điểm trừ: {total_deduction:.2f}")
    print(f"Điểm cuối: {final_score:.2f}")
    print(f"Kết quả: {'✅ ĐẠT' if is_passed else '❌ TRƯỢT'}")
    print(f"\nTổng số lỗi: {len(all_errors)}")
    print("\nLỗi theo loại:")
    for error_type, count in result["errors_by_type"].items():
        print(f"  - {error_type}: {count}")
    print("="*60)
    
    return result


def main():
    """Hàm main"""
    import argparse
    import sys
    
    # Fix encoding for Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    parser = argparse.ArgumentParser(description="Cham diem video dieu lenh")
    parser.add_argument(
        "mode",
        choices=["create_golden", "evaluate"],
        help="Chế độ: create_golden (tạo golden template) hoặc evaluate (đánh giá video)"
    )
    parser.add_argument(
        "video_path",
        type=str,
        help="Đường dẫn video (golden hoặc test)"
    )
    parser.add_argument(
        "--golden-dir",
        type=str,
        default=None,
        help="Thư mục golden template (mặc định: data/golden_template)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Thư mục output (mặc định: data/golden_template cho create_golden, data/output cho evaluate)"
    )
    
    args = parser.parse_args()
    
    video_path = Path(args.video_path)
    if not video_path.exists():
        print(f"❌ Video không tồn tại: {video_path}")
        return
    
    if args.mode == "create_golden":
        output_dir = Path(args.output_dir) if args.output_dir else None
        create_golden_template(video_path, output_dir)
    elif args.mode == "evaluate":
        golden_dir = Path(args.golden_dir) if args.golden_dir else None
        evaluate_video(video_path, golden_dir)


if __name__ == "__main__":
    main()

