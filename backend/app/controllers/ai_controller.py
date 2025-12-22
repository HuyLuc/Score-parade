"""
AIController - Phát hiện lỗi của người thí sinh
"""
import json
import math
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np
from backend.app.services.pose_service import PoseService
from backend.app.services.geometry import (
    calculate_arm_angle,
    calculate_leg_angle,
    calculate_arm_height,
    calculate_leg_height,
    calculate_head_angle,
    calculate_torso_stability
)
from backend.app.services.keypoint_normalization import normalize_keypoints_relative
from backend.app.services.temporal_smoothing import TemporalSmoother, KeypointSmoother
from backend.app.services.adaptive_threshold import AdaptiveThresholdManager
from backend.app.services.dtw_alignment import DTWAligner
from backend.app.services.sequence_comparison import SequenceComparator
from backend.app.config import GOLDEN_TEMPLATE_DIR, SCORING_CONFIG, ERROR_THRESHOLDS, NORMALIZATION_CONFIG, TEMPORAL_SMOOTHING_CONFIG, ADAPTIVE_THRESHOLD_CONFIG, DTW_CONFIG, SEQUENCE_COMPARISON_CONFIG


class AIController:
    """Controller cho AI phát hiện lỗi"""
    
    def __init__(self, pose_service: PoseService):
        self.pose_service = pose_service
        self.golden_profile = None
        self.golden_keypoints = None
        self.beat_detector = None  # Beat detector for rhythm checking
        
        # Initialize temporal smoothers
        smoothing_enabled = TEMPORAL_SMOOTHING_CONFIG.get("enabled", False)
        window_size = TEMPORAL_SMOOTHING_CONFIG.get("window_size", 7)  # Updated default: 7 frames
        method = TEMPORAL_SMOOTHING_CONFIG.get("method", "gaussian")  # Updated default: gaussian
        
        if smoothing_enabled:
            self.keypoint_smoother = KeypointSmoother(
                window_size=window_size,
                num_keypoints=17,
                method=method
            )
            # Metric smoothers for arm, leg, head angles (left and right)
            self.metric_smoothers = {
                "arm_angle_left": TemporalSmoother(window_size=window_size, method=method),
                "arm_angle_right": TemporalSmoother(window_size=window_size, method=method),
                "leg_angle_left": TemporalSmoother(window_size=window_size, method=method),
                "leg_angle_right": TemporalSmoother(window_size=window_size, method=method),
                "head_angle": TemporalSmoother(window_size=window_size, method=method),
            }
        else:
            self.keypoint_smoother = None
            self.metric_smoothers = None
        
        # Initialize adaptive threshold manager
        adaptive_enabled = ADAPTIVE_THRESHOLD_CONFIG.get("enabled", False)
        if adaptive_enabled:
            self.adaptive_threshold_manager = AdaptiveThresholdManager(
                multiplier=ADAPTIVE_THRESHOLD_CONFIG.get("multiplier", 3.0),
                min_ratio=ADAPTIVE_THRESHOLD_CONFIG.get("min_ratio", 0.3),
                max_ratio=ADAPTIVE_THRESHOLD_CONFIG.get("max_ratio", 2.0),
                enable_cache=ADAPTIVE_THRESHOLD_CONFIG.get("cache_thresholds", True)
            )
        else:
            self.adaptive_threshold_manager = None
        
        # Initialize sequence comparator
        sequence_enabled = SEQUENCE_COMPARISON_CONFIG.get("enabled", True)
        if sequence_enabled:
            self.sequence_comparator = SequenceComparator(
                min_sequence_length=SEQUENCE_COMPARISON_CONFIG.get("min_sequence_length", 5),
                severity_aggregation=SEQUENCE_COMPARISON_CONFIG.get("severity_aggregation", "median"),
                max_gap_frames=SEQUENCE_COMPARISON_CONFIG.get("max_gap_frames", 3),
                enabled=True
            )
        else:
            self.sequence_comparator = None

    # ===================== Helper =====================
    def _build_error(
        self,
        error_type: str,
        description: str,
        diff: float,
        body_part: str,
        side: Optional[str] = None
    ) -> Dict:
        """
        Tạo dict lỗi kèm severity và deduction dựa trên config
        
        Sử dụng sqrt để severity tăng chậm hơn (sub-linear growth)
        thay vì tuyến tính, giúp giảm điểm trừ cho các lỗi nhỏ.
        
        VD: 
        - Trước: diff=60, threshold=30, weight=2.0 → severity = 60/30 = 2.0 → deduction = 2.0 * 2.0 = 4.0
        - Sau:  diff=60, threshold=30, weight=1.0 → severity = sqrt(60/30) = 1.41 → deduction = 1.0 * 1.41 = 1.41
        """
        weight = SCORING_CONFIG["error_weights"].get(error_type, 1.0)
        threshold = ERROR_THRESHOLDS.get(error_type, 10.0)
        threshold = threshold if threshold and threshold > 0 else 10.0
        
        # Sử dụng sqrt để severity tăng chậm hơn + cap ở 3.0 thay vì 10.0
        severity = min(math.sqrt(diff / threshold), 3.0)
        deduction = weight * severity
        
        return {
            "type": error_type,
            "description": description,
            "severity": severity,
            "deduction": deduction,
            "body_part": body_part,
            **({"side": side} if side else {})
        }

    def _get_golden_stat(self, metric: str, side: Optional[str] = None) -> Tuple[Optional[float], Optional[float]]:
        """Lấy mean/std từ golden profile nếu có"""
        if not self.golden_profile or "statistics" not in self.golden_profile:
            return None, None
        stats = self.golden_profile["statistics"]
        if metric not in stats:
            return None, None
        val = stats[metric]
        if side and isinstance(val, dict) and side in val:
            mean = val[side].get("mean")
            std = val[side].get("std")
            return mean, std
        if isinstance(val, dict) and "mean" in val:
            return val.get("mean"), val.get("std")
        return None, None

    def _is_outlier(
        self,
        value: float,
        mean: Optional[float],
        std: Optional[float],
        default_threshold: float,
        error_type: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        torso_length: Optional[float] = None,
        reference_torso_length: float = 100.0
    ) -> Tuple[bool, float]:
        """
        Kiểm tra vượt ngưỡng so với golden (mean/std) hoặc ngưỡng mặc định
        
        Sử dụng adaptive threshold dựa trên golden template statistics nếu được bật.
        Falls back to 3-sigma rule hoặc default threshold nếu adaptive disabled.
        Adjusts threshold based on difficulty level and person height (torso length).
        
        Args:
            value: Giá trị cần kiểm tra
            mean: Mean từ golden template
            std: Standard deviation từ golden template
            default_threshold: Ngưỡng mặc định
            error_type: Loại lỗi (e.g., "arm_angle") - dùng cho adaptive threshold
            difficulty_level: Difficulty level ("easy", "medium", "hard") - affects threshold
            torso_length: Person's torso length in pixels (for height adjustment)
            reference_torso_length: Reference torso length for normalization
        
        Returns:
            Tuple (is_outlier, diff)
        """
        if value is None:
            return False, 0.0
        
        # Use adaptive threshold if enabled and error_type provided
        if (
            self.adaptive_threshold_manager is not None
            and error_type is not None
            and std is not None
            and ADAPTIVE_THRESHOLD_CONFIG.get("enabled", False)
        ):
            # Get difficulty level from config if not provided
            if difficulty_level is None:
                difficulty_level = SCORING_CONFIG.get("difficulty_level", "medium")
            
            # Get reference torso length from config if not provided
            if reference_torso_length is None or reference_torso_length <= 0:
                reference_torso_length = NORMALIZATION_CONFIG.get("reference_torso_length", 100.0)
            
            threshold = self.adaptive_threshold_manager.get_threshold(
                error_type=error_type,
                golden_mean=mean,
                golden_std=std,
                default_threshold=default_threshold,
                difficulty_level=difficulty_level,
                torso_length=torso_length,
                reference_torso_length=reference_torso_length
            )
        else:
            # Fallback: Use 3-sigma rule or default threshold
            base_threshold = default_threshold
            if base_threshold is None or base_threshold <= 0:
                # Nếu default_threshold không hợp lệ, lấy từ ERROR_THRESHOLDS hoặc dùng 10.0
                if error_type is not None:
                    base_threshold = ERROR_THRESHOLDS.get(error_type, 10.0)
                else:
                    base_threshold = 10.0

            threshold = (std * 3) if std else base_threshold
            if threshold is None or threshold <= 0:
                threshold = base_threshold
        
        diff = abs(value - mean) if mean is not None else 0.0
        return diff > threshold, diff
    
    def load_golden_template(self, template_name: str = None, camera_angle: str = None):
        """
        Load golden template để so sánh
        
        Args:
            template_name: Tên template (None = dùng default)
            camera_angle: Góc quay ("front", "side", "back", "diagonal", None = auto select)
        """
        # Auto-select profile logic dựa trên camera_angle
        if template_name:
            template_dir = GOLDEN_TEMPLATE_DIR / template_name
            profile_path = template_dir / "combined_profile.json"
        elif camera_angle:
            # Tự động chọn profile dựa trên góc camera
            angle_dir = GOLDEN_TEMPLATE_DIR / camera_angle
            combined_path = angle_dir / "combined_profile.json"
            default_path = angle_dir / "golden_profile.json"
            
            # Ưu tiên combined_profile.json, fallback về golden_profile.json
            if combined_path.exists():
                profile_path = combined_path
            elif default_path.exists():
                profile_path = default_path
            else:
                # Fallback về profile mặc định nếu không tìm thấy profile cho góc này
                profile_path = GOLDEN_TEMPLATE_DIR / "golden_profile.json"
        else:
            # Load profile mặc định
            profile_path = GOLDEN_TEMPLATE_DIR / "golden_profile.json"
        
        if profile_path.exists():
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    self.golden_profile = json.load(f)
            except (json.JSONDecodeError, IOError, UnicodeDecodeError, ValueError) as e:
                print(f"⚠️ Cảnh báo: Không thể load golden profile: {e}")
                self.golden_profile = None
            except Exception as e:
                # Catch any other unexpected exceptions
                print(f"⚠️ Cảnh báo: Lỗi không mong đợi khi load golden profile: {type(e).__name__}: {e}")
                self.golden_profile = None
        else:
            print(f"⚠️ Cảnh báo: Không tìm thấy golden profile: {profile_path}")
            self.golden_profile = None
        
        # Load golden keypoints
        skeleton_path = GOLDEN_TEMPLATE_DIR / "golden_skeleton.pkl"
        if skeleton_path.exists():
            try:
                with open(skeleton_path, 'rb') as f:
                    golden_data = pickle.load(f)
                if 'valid_skeletons' in golden_data:
                    self.golden_keypoints = np.array(golden_data['valid_skeletons'])
                elif 'keypoints' in golden_data:
                    # Fallback nếu không có 'valid_skeletons'
                    self.golden_keypoints = np.array(golden_data['keypoints'])
                else:
                    print(f"⚠️ Cảnh báo: Golden skeleton không có 'valid_skeletons' hoặc 'keypoints'")
                    self.golden_keypoints = None
            except (pickle.UnpicklingError, IOError, EOFError, ValueError, AttributeError, KeyError) as e:
                # Catch common pickle errors: UnpicklingError, IOError, EOFError (empty file), 
                # ValueError (corrupted data), AttributeError (class definition issues), KeyError (missing keys)
                print(f"⚠️ Cảnh báo: Không thể load golden skeleton: {type(e).__name__}: {e}")
                self.golden_keypoints = None
            except Exception as e:
                # Catch any other unexpected exceptions
                print(f"⚠️ Cảnh báo: Lỗi không mong đợi khi load golden skeleton: {type(e).__name__}: {e}")
                self.golden_keypoints = None
        else:
            self.golden_keypoints = None
    
    def detect_posture_errors(
        self,
        keypoints: np.ndarray,
        frame_number: int = 0,
        timestamp: float = 0.0,
        difficulty_level: Optional[str] = None
    ) -> List[Dict]:
        """
        Phát hiện lỗi tư thế (Local Mode)
        
        Args:
            keypoints: Keypoints [17, 3]
            frame_number: Số frame
            timestamp: Timestamp (giây)
            difficulty_level: Difficulty level ("easy", "medium", "hard") - affects threshold adjustment
            
        Returns:
            List các dict chứa thông tin lỗi:
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left"
            }
        """
        errors = []
        
        if keypoints.shape[0] < 17 or keypoints.shape[1] < 3:
            return errors
        
        # So sánh với golden template nếu có
        if self.golden_profile is None:
            self.load_golden_template()
        
        # Get difficulty level from config if not provided
        if difficulty_level is None:
            difficulty_level = SCORING_CONFIG.get("difficulty_level", "medium")
        
        # Calculate torso length for height adjustment
        from backend.app.services.keypoint_normalization import calculate_torso_length
        torso_length = calculate_torso_length(keypoints)
        reference_torso_length = NORMALIZATION_CONFIG.get("reference_torso_length", 100.0)
        
        # Apply temporal smoothing to keypoints if enabled
        smoothed_keypoints = keypoints
        if self.keypoint_smoother is not None and TEMPORAL_SMOOTHING_CONFIG.get("smooth_keypoints", True):
            self.keypoint_smoother.add_keypoints(keypoints)
            smoothed = self.keypoint_smoother.get_smoothed_keypoints()
            if smoothed is not None:
                smoothed_keypoints = smoothed
        
        # Normalize keypoints nếu được bật trong config
        normalized_keypoints = smoothed_keypoints
        if NORMALIZATION_CONFIG.get("enabled", True):
            normalized_keypoints = normalize_keypoints_relative(smoothed_keypoints)
            if normalized_keypoints is None:
                # Không đủ keypoints để normalize, dùng keypoints gốc
                print(f"⚠️ Cảnh báo: Không thể normalize keypoints tại frame {frame_number}, sử dụng keypoints gốc")
                normalized_keypoints = smoothed_keypoints
        
        # Kiểm tra từng bộ phận với normalized keypoints
        # Pass difficulty_level and torso_length to error checking methods
        # 1. Tay (Arm) - use smoothed version if enabled
        if self.metric_smoothers is not None and TEMPORAL_SMOOTHING_CONFIG.get("smooth_metrics", True):
            arm_errors = self._check_arm_posture_smoothed(normalized_keypoints, difficulty_level, torso_length, reference_torso_length)
        else:
            arm_errors = self._check_arm_posture(normalized_keypoints, difficulty_level, torso_length, reference_torso_length)
        errors.extend(arm_errors)
        
        # 2. Chân (Leg) - use smoothed version if enabled
        if self.metric_smoothers is not None and TEMPORAL_SMOOTHING_CONFIG.get("smooth_metrics", True):
            leg_errors = self._check_leg_posture_smoothed(normalized_keypoints, difficulty_level, torso_length, reference_torso_length)
        else:
            leg_errors = self._check_leg_posture(normalized_keypoints, difficulty_level, torso_length, reference_torso_length)
        errors.extend(leg_errors)
        
        # 3. Vai (Shoulder)
        shoulder_errors = self._check_shoulder_posture(normalized_keypoints)
        errors.extend(shoulder_errors)
        
        # 4. Mũi (Nose) - Kiểm tra đầu có cúi không - use smoothed version if enabled
        if self.metric_smoothers is not None and TEMPORAL_SMOOTHING_CONFIG.get("smooth_metrics", True):
            nose_errors = self._check_head_posture_smoothed(normalized_keypoints, difficulty_level, torso_length, reference_torso_length)
        else:
            nose_errors = self._check_head_posture(normalized_keypoints, difficulty_level, torso_length, reference_torso_length)
        errors.extend(nose_errors)
        
        # 5. Cổ (Neck)
        neck_errors = self._check_neck_posture(normalized_keypoints, difficulty_level, torso_length, reference_torso_length)
        errors.extend(neck_errors)
        
        # 6. Lưng (Back)
        back_errors = self._check_back_posture(normalized_keypoints)
        errors.extend(back_errors)
        
        # Thêm metadata
        for error in errors:
            error["frame_number"] = frame_number
            error["timestamp"] = timestamp
        
        return errors
    
    def _check_arm_posture(
        self, 
        keypoints: np.ndarray,
        difficulty_level: Optional[str] = None,
        torso_length: Optional[float] = None,
        reference_torso_length: float = 100.0
    ) -> List[Dict]:
        """Kiểm tra tư thế tay"""
        errors = []
        threshold = ERROR_THRESHOLDS.get("arm_angle", 50.0)
        
        # Tính góc tay
        left_arm_angle = calculate_arm_angle(keypoints, "left")
        right_arm_angle = calculate_arm_angle(keypoints, "right")
        
        # So sánh với golden (nếu có)
        if self.golden_profile and "statistics" in self.golden_profile:
            stats = self.golden_profile["statistics"]
            if "arm_angle" in stats and "left" in stats["arm_angle"]:
                golden_left = stats["arm_angle"]["left"].get("mean", 0)
                golden_std = stats["arm_angle"]["left"].get("std", 5.0)
                
                if left_arm_angle is not None:
                    is_out, diff = self._is_outlier(
                        left_arm_angle,
                        golden_left,
                        golden_std,
                        threshold,
                        error_type="arm_angle",
                        difficulty_level=difficulty_level,
                        torso_length=torso_length,
                        reference_torso_length=reference_torso_length
                    )
                    if is_out:
                        desc = "Tay trái quá cao" if left_arm_angle > (golden_left or 0) else "Tay trái quá thấp"
                        errors.append(self._build_error(
                            "arm_angle",
                            desc,
                            diff,
                            "arm",
                            "left"
                        ))
            else:
                # Không có golden cho tay trái, dùng threshold tuyệt đối
                # Giả định tư thế chuẩn là tay ở góc ~90-120° (tùy động tác)
                # Kiểm tra nếu góc quá nhỏ (< 30°) hoặc quá lớn (> 180°)
                if left_arm_angle is not None:
                    if left_arm_angle < 30 or left_arm_angle > 180:
                        diff = abs(left_arm_angle - 90) if left_arm_angle < 30 else abs(left_arm_angle - 180)
                        if diff > threshold:
                            desc = f"Tay trái ở góc bất thường ({left_arm_angle:.1f}°)"
                            errors.append(self._build_error(
                                "arm_angle",
                                desc,
                                diff - threshold,
                                "arm",
                                "left"
                            ))
        else:
            # Không có golden template, dùng threshold tuyệt đối
            if left_arm_angle is not None:
                if left_arm_angle < 30 or left_arm_angle > 180:
                    diff = abs(left_arm_angle - 90) if left_arm_angle < 30 else abs(left_arm_angle - 180)
                    if diff > threshold:
                        desc = f"Tay trái ở góc bất thường ({left_arm_angle:.1f}°)"
                        errors.append(self._build_error(
                            "arm_angle",
                            desc,
                            diff - threshold,
                            "arm",
                            "left"
                        ))
        
        # Tương tự cho tay phải
        if self.golden_profile and "statistics" in self.golden_profile:
            stats = self.golden_profile["statistics"]
            if "arm_angle" in stats and "right" in stats["arm_angle"]:
                golden_right = stats["arm_angle"]["right"].get("mean", 0)
                golden_std = stats["arm_angle"]["right"].get("std", 5.0)
                
                if right_arm_angle is not None:
                    is_out, diff = self._is_outlier(
                        right_arm_angle,
                        golden_right,
                        golden_std,
                        threshold,
                        error_type="arm_angle",
                        difficulty_level=difficulty_level,
                        torso_length=torso_length,
                        reference_torso_length=reference_torso_length
                    )
                    if is_out:
                        desc = "Tay phải quá cao" if right_arm_angle > (golden_right or 0) else "Tay phải quá thấp"
                        errors.append(self._build_error(
                            "arm_angle",
                            desc,
                            diff,
                            "arm",
                            "right"
                        ))
            else:
                # Không có golden cho tay phải, dùng threshold tuyệt đối
                if right_arm_angle is not None:
                    if right_arm_angle < 30 or right_arm_angle > 180:
                        diff = abs(right_arm_angle - 90) if right_arm_angle < 30 else abs(right_arm_angle - 180)
                        if diff > threshold:
                            desc = f"Tay phải ở góc bất thường ({right_arm_angle:.1f}°)"
                            errors.append(self._build_error(
                                "arm_angle",
                                desc,
                                diff - threshold,
                                "arm",
                                "right"
                            ))
        else:
            # Không có golden template, dùng threshold tuyệt đối
            if right_arm_angle is not None:
                if right_arm_angle < 30 or right_arm_angle > 180:
                    diff = abs(right_arm_angle - 90) if right_arm_angle < 30 else abs(right_arm_angle - 180)
                    if diff > threshold:
                        desc = f"Tay phải ở góc bất thường ({right_arm_angle:.1f}°)"
                        errors.append(self._build_error(
                            "arm_angle",
                            desc,
                            diff - threshold,
                            "arm",
                            "right"
                        ))
        
        return errors
    
    def _check_leg_posture(
        self, 
        keypoints: np.ndarray,
        difficulty_level: Optional[str] = None,
        torso_length: Optional[float] = None,
        reference_torso_length: float = 100.0
    ) -> List[Dict]:
        """Kiểm tra tư thế chân"""
        errors = []
        threshold = ERROR_THRESHOLDS.get("leg_angle", 45.0)
        
        left_leg_angle = calculate_leg_angle(keypoints, "left")
        right_leg_angle = calculate_leg_angle(keypoints, "right")
        
        # Tương tự như arm
        if self.golden_profile and "statistics" in self.golden_profile:
            stats = self.golden_profile["statistics"]
            if "leg_angle" in stats:
                # Kiểm tra chân trái
                if "left" in stats["leg_angle"] and left_leg_angle is not None:
                    golden_left = stats["leg_angle"]["left"].get("mean", 0)
                    golden_std = stats["leg_angle"]["left"].get("std", 5.0)
                    is_out, diff = self._is_outlier(
                        left_leg_angle,
                        golden_left,
                        golden_std,
                        threshold,
                        error_type="leg_angle",
                        difficulty_level=difficulty_level,
                        torso_length=torso_length,
                        reference_torso_length=reference_torso_length
                    )
                    if is_out:
                        desc = f"Chân trái {'quá cao' if left_leg_angle > (golden_left or 0) else 'quá thấp'}"
                        errors.append(self._build_error(
                            "leg_angle",
                            desc,
                            diff,
                            "leg",
                            "left"
                        ))
                else:
                    # Không có golden cho chân trái, dùng threshold tuyệt đối
                    if left_leg_angle is not None:
                        # Giả định tư thế chuẩn là chân ở góc ~150-180° (đứng thẳng)
                        if left_leg_angle < 120 or left_leg_angle > 200:
                            diff = abs(left_leg_angle - 180) if left_leg_angle < 120 else abs(left_leg_angle - 200)
                            if diff > threshold:
                                desc = f"Chân trái ở góc bất thường ({left_leg_angle:.1f}°)"
                                errors.append(self._build_error(
                                    "leg_angle",
                                    desc,
                                    diff - threshold,
                                    "leg",
                                    "left"
                                ))
                
                # Kiểm tra chân phải
                if "right" in stats["leg_angle"] and right_leg_angle is not None:
                    golden_right = stats["leg_angle"]["right"].get("mean", 0)
                    golden_std = stats["leg_angle"]["right"].get("std", 5.0)
                    is_out, diff = self._is_outlier(
                        right_leg_angle,
                        golden_right,
                        golden_std,
                        threshold,
                        error_type="leg_angle",
                        difficulty_level=difficulty_level,
                        torso_length=torso_length,
                        reference_torso_length=reference_torso_length
                    )
                    if is_out:
                        desc = f"Chân phải {'quá cao' if right_leg_angle > (golden_right or 0) else 'quá thấp'}"
                        errors.append(self._build_error(
                            "leg_angle",
                            desc,
                            diff,
                            "leg",
                            "right"
                        ))
                else:
                    # Không có golden cho chân phải, dùng threshold tuyệt đối
                    if right_leg_angle is not None:
                        if right_leg_angle < 120 or right_leg_angle > 200:
                            diff = abs(right_leg_angle - 180) if right_leg_angle < 120 else abs(right_leg_angle - 200)
                            if diff > threshold:
                                desc = f"Chân phải ở góc bất thường ({right_leg_angle:.1f}°)"
                                errors.append(self._build_error(
                                    "leg_angle",
                                    desc,
                                    diff - threshold,
                                    "leg",
                                    "right"
                                ))
        else:
            # Không có golden template, dùng threshold tuyệt đối
            if left_leg_angle is not None:
                if left_leg_angle < 120 or left_leg_angle > 200:
                    diff = abs(left_leg_angle - 180) if left_leg_angle < 120 else abs(left_leg_angle - 200)
                    if diff > threshold:
                        desc = f"Chân trái ở góc bất thường ({left_leg_angle:.1f}°)"
                        errors.append(self._build_error(
                            "leg_angle",
                            desc,
                            diff - threshold,
                            "leg",
                            "left"
                        ))
            
            if right_leg_angle is not None:
                if right_leg_angle < 120 or right_leg_angle > 200:
                    diff = abs(right_leg_angle - 180) if right_leg_angle < 120 else abs(right_leg_angle - 200)
                    if diff > threshold:
                        desc = f"Chân phải ở góc bất thường ({right_leg_angle:.1f}°)"
                        errors.append(self._build_error(
                            "leg_angle",
                            desc,
                            diff - threshold,
                            "leg",
                            "right"
                        ))
        
        return errors
    
    def _check_shoulder_posture(self, keypoints: np.ndarray) -> List[Dict]:
        """Kiểm tra tư thế vai"""
        errors = []
        
        # Kiểm tra vai có cân bằng không
        if keypoints.shape[0] >= 7:  # Có keypoints cho vai
            left_shoulder = keypoints[5]  # Left shoulder
            right_shoulder = keypoints[6]  # Right shoulder
            
            if left_shoulder[2] > 0 and right_shoulder[2] > 0:
                height_diff = abs(left_shoulder[1] - right_shoulder[1])
                threshold = ERROR_THRESHOLDS.get("torso_stability", 20.0)
                if height_diff > threshold:
                    errors.append(self._build_error(
                        "torso_stability",
                        "Vai không cân bằng",
                        height_diff,
                        "shoulder"
                    ))
        
        return errors
    
    def _check_head_posture(
        self, 
        keypoints: np.ndarray,
        difficulty_level: Optional[str] = None,
        torso_length: Optional[float] = None,
        reference_torso_length: float = 100.0
    ) -> List[Dict]:
        """
        Kiểm tra tư thế đầu (mũi)
        
        Kiểm tra đầu có cúi quá thấp hoặc ngẩng quá cao so với golden template.
        Sử dụng giá trị head_angle có dấu:
        - Âm: đầu cúi
        - Dương: đầu ngẩng
        - ~0: đầu thẳng
        """
        errors = []
        
        head_angle = calculate_head_angle(keypoints)
        
        if head_angle is None:
            return errors
        
        # Lấy golden statistics nếu có
        golden_mean, golden_std = self._get_golden_stat("head_angle")
        threshold = ERROR_THRESHOLDS.get("head_angle", 30.0)
        
        # Nếu có golden template, so sánh với nó
        if golden_mean is not None and golden_std is not None:
            is_out, diff = self._is_outlier(
                head_angle,
                golden_mean,
                golden_std,
                threshold,
                error_type="head_angle",
                difficulty_level=difficulty_level,
                torso_length=torso_length,
                reference_torso_length=reference_torso_length
            )
            
            if is_out:
                # Phân biệt cúi vs ngẩng dựa trên dấu
                if head_angle < golden_mean:
                    desc = "Đầu cúi quá thấp"
                else:
                    desc = "Đầu ngẩng quá cao"
                
                errors.append(self._build_error(
                    "head_angle",
                    desc,
                    diff,
                    "nose"
                ))
        else:
            # Không có golden template, dùng threshold tuyệt đối
            # Giả định tư thế chuẩn là đầu thẳng (~0°)
            # Cho phép lệch ±threshold
            
            if head_angle < -threshold:
                # Đầu cúi quá (âm và lớn hơn threshold)
                # Ví dụ: head_angle = -40°, threshold = 30° → diff = 40° - 30° = 10°
                diff = abs(head_angle) - threshold
                errors.append(self._build_error(
                    "head_angle",
                    f"Đầu cúi quá thấp ({head_angle:.1f}°)",
                    diff,
                    "nose"
                ))
            elif head_angle > threshold:
                # Đầu ngẩng quá (dương và lớn hơn threshold)
                diff = head_angle - threshold
                errors.append(self._build_error(
                    "head_angle",
                    f"Đầu ngẩng quá cao ({head_angle:.1f}°)",
                    diff,
                    "nose"
                ))
        
        return errors
    
    def _check_neck_posture(
        self, 
        keypoints: np.ndarray,
        difficulty_level: Optional[str] = None,
        torso_length: Optional[float] = None,
        reference_torso_length: float = 100.0
    ) -> List[Dict]:
        """
        Kiểm tra tư thế cổ
        
        Kiểm tra cổ có thẳng không dựa vào góc giữa đầu (nose) và vai.
        Sử dụng logic tương tự như _check_head_posture nhưng tập trung vào góc cổ.
        """
        errors = []
        
        # Cần ít nhất 3 keypoints: nose, left_shoulder, right_shoulder
        if keypoints.shape[0] < 7:
            return errors
        
        nose_idx = 0
        left_shoulder_idx = 5
        right_shoulder_idx = 6
        
        nose = keypoints[nose_idx]
        left_shoulder = keypoints[left_shoulder_idx]
        right_shoulder = keypoints[right_shoulder_idx]
        
        # Kiểm tra confidence
        if (nose[2] == 0 or left_shoulder[2] == 0 or right_shoulder[2] == 0):
            return errors
        
        # Tính điểm cổ (trung điểm của 2 vai)
        neck_point = (left_shoulder[:2] + right_shoulder[:2]) / 2
        
        # Vector từ cổ đến mũi
        vec_neck_to_nose = nose[:2] - neck_point
        
        # Tính góc cổ (tương tự head_angle nhưng tập trung vào độ thẳng)
        # Sử dụng atan2 để có giá trị có dấu
        import numpy as np
        angle_rad = np.arctan2(vec_neck_to_nose[0], -vec_neck_to_nose[1])
        neck_angle = np.degrees(angle_rad)
        
        # Clamp về khoảng -90 đến +90
        neck_angle = np.clip(neck_angle, -90.0, 90.0)
        
        # Lấy golden statistics nếu có
        golden_mean, golden_std = self._get_golden_stat("neck_angle")
        threshold = ERROR_THRESHOLDS.get("neck_angle", 25.0)  # Ngưỡng mặc định cho cổ
        
        # Nếu có golden template, so sánh với nó
        if golden_mean is not None and golden_std is not None:
            is_out, diff = self._is_outlier(
                neck_angle,
                golden_mean,
                golden_std,
                threshold,
                error_type="neck_angle",
                difficulty_level=difficulty_level,
                torso_length=torso_length,
                reference_torso_length=reference_torso_length
            )
            
            if is_out:
                # Phân biệt cúi vs ngẩng dựa trên dấu
                if neck_angle < golden_mean:
                    desc = "Cổ cúi quá thấp"
                else:
                    desc = "Cổ ngẩng quá cao"
                
                errors.append(self._build_error(
                    "neck_angle",
                    desc,
                    diff,
                    "neck"
                ))
        else:
            # Không có golden template, dùng threshold tuyệt đối
            # Giả định tư thế chuẩn là cổ thẳng (~0°)
            if abs(neck_angle) > threshold:
                diff = abs(neck_angle) - threshold
                if neck_angle < 0:
                    desc = f"Cổ cúi quá thấp ({neck_angle:.1f}°)"
                else:
                    desc = f"Cổ ngẩng quá cao ({neck_angle:.1f}°)"
                
                errors.append(self._build_error(
                    "neck_angle",
                    desc,
                    diff,
                    "neck"
                ))
        
        return errors
    
    def _check_back_posture(self, keypoints: np.ndarray) -> List[Dict]:
        """Kiểm tra tư thế lưng"""
        errors = []
        
        # torso_stability cần nhiều frames để tính variance
        # Nên không kiểm tra ở đây (single frame)
        # torso_stability sẽ được kiểm tra trong global mode với nhiều frames
        
        return errors
    
    def set_beat_detector(self, audio_path: str):
        """
        Khởi tạo beat detector cho audio
        
        Args:
            audio_path: Đường dẫn file audio đang phát
        """
        try:
            from backend.app.services.beat_detection import BeatDetector
            self.beat_detector = BeatDetector(audio_path)
        except Exception as e:
            print(f"⚠️ Không thể khởi tạo beat detector: {e}")
            self.beat_detector = None
    
    def detect_rhythm_errors(
        self,
        motion_keypoints: List[Tuple[float, np.ndarray]],
        motion_type: str = "step"
    ) -> List[Dict]:
        """
        Phát hiện lỗi rhythm - động tác không theo nhịp
        
        Args:
            motion_keypoints: List các tuple (timestamp, keypoints) của động tác
            motion_type: Loại động tác ("step", "arm_swing", etc.)
            
        Returns:
            List các dict lỗi rhythm
        """
        errors = []
        
        if self.beat_detector is None:
            return errors
        
        # Extract timestamps
        motion_times = [t for t, _ in motion_keypoints]
        
        # Lấy tolerance từ config
        tolerance = ERROR_THRESHOLDS.get("rhythm", 0.15)
        
        # Tính lỗi rhythm
        error_count, error_pairs = self.beat_detector.calculate_rhythm_error(
            motion_times,
            tolerance=tolerance
        )
        
        # Build error dicts
        for motion_time, beat_time in error_pairs:
            diff = abs(motion_time - beat_time)
            desc = f"Động tác {motion_type} không theo nhịp (lệch {diff:.2f}s)"
            
            errors.append(self._build_error(
                "rhythm",
                desc,
                diff,
                motion_type,
                None
            ))
        
        return errors
    
    def _check_arm_posture_smoothed(
        self, 
        keypoints: np.ndarray,
        difficulty_level: Optional[str] = None,
        torso_length: Optional[float] = None,
        reference_torso_length: float = 100.0
    ) -> List[Dict]:
        """
        Kiểm tra tư thế tay với temporal smoothing
        
        Smooths arm angles across frames before comparing to golden template
        to reduce false positives from keypoint jitter.
        """
        errors = []
        
        # Tính góc tay
        left_arm_angle = calculate_arm_angle(keypoints, "left")
        right_arm_angle = calculate_arm_angle(keypoints, "right")
        
        # Smooth angles before checking
        if left_arm_angle is not None:
            self.metric_smoothers["arm_angle_left"].add_value(left_arm_angle)
        if right_arm_angle is not None:
            self.metric_smoothers["arm_angle_right"].add_value(right_arm_angle)
        
        # Get smoothed values
        smoothed_left = self.metric_smoothers["arm_angle_left"].get_smoothed_value()
        smoothed_right = self.metric_smoothers["arm_angle_right"].get_smoothed_value()
        
        # Check left arm with smoothed value
        if smoothed_left is not None and self.golden_profile and "statistics" in self.golden_profile:
            stats = self.golden_profile["statistics"]
            if "arm_angle" in stats and "left" in stats["arm_angle"]:
                golden_left = stats["arm_angle"]["left"].get("mean", 0)
                golden_std = stats["arm_angle"]["left"].get("std", 5.0)
                
                is_out, diff = self._is_outlier(
                    smoothed_left,
                    golden_left,
                    golden_std,
                    ERROR_THRESHOLDS.get("arm_angle", 10.0),
                    error_type="arm_angle",
                    difficulty_level=difficulty_level,
                    torso_length=torso_length,
                    reference_torso_length=reference_torso_length
                )
                if is_out:
                    desc = "Tay trái quá cao" if smoothed_left > (golden_left or 0) else "Tay trái quá thấp"
                    errors.append(self._build_error(
                        "arm_angle",
                        desc,
                        diff,
                        "arm",
                        "left"
                    ))
        
        # Check right arm with smoothed value
        if smoothed_right is not None and self.golden_profile and "statistics" in self.golden_profile:
            stats = self.golden_profile["statistics"]
            if "arm_angle" in stats and "right" in stats["arm_angle"]:
                golden_right = stats["arm_angle"]["right"].get("mean", 0)
                golden_std = stats["arm_angle"]["right"].get("std", 5.0)
                
                is_out, diff = self._is_outlier(
                    smoothed_right,
                    golden_right,
                    golden_std,
                    ERROR_THRESHOLDS.get("arm_angle", 10.0),
                    error_type="arm_angle",
                    difficulty_level=difficulty_level,
                    torso_length=torso_length,
                    reference_torso_length=reference_torso_length
                )
                if is_out:
                    desc = "Tay phải quá cao" if smoothed_right > (golden_right or 0) else "Tay phải quá thấp"
                    errors.append(self._build_error(
                        "arm_angle",
                        desc,
                        diff,
                        "arm",
                        "right"
                    ))
        
        return errors
    
    def _check_leg_posture_smoothed(
        self, 
        keypoints: np.ndarray,
        difficulty_level: Optional[str] = None,
        torso_length: Optional[float] = None,
        reference_torso_length: float = 100.0
    ) -> List[Dict]:
        """
        Kiểm tra tư thế chân với temporal smoothing
        
        Smooths leg angles across frames before comparing to golden template.
        """
        errors = []
        
        left_leg_angle = calculate_leg_angle(keypoints, "left")
        right_leg_angle = calculate_leg_angle(keypoints, "right")
        
        # Smooth angles before checking
        if left_leg_angle is not None:
            self.metric_smoothers["leg_angle_left"].add_value(left_leg_angle)
        if right_leg_angle is not None:
            self.metric_smoothers["leg_angle_right"].add_value(right_leg_angle)
        
        # Get smoothed values
        smoothed_left = self.metric_smoothers["leg_angle_left"].get_smoothed_value()
        smoothed_right = self.metric_smoothers["leg_angle_right"].get_smoothed_value()
        
        # Check left leg with smoothed value
        if smoothed_left is not None and self.golden_profile and "statistics" in self.golden_profile:
            stats = self.golden_profile["statistics"]
            if "leg_angle" in stats and "left" in stats["leg_angle"]:
                golden_left = stats["leg_angle"]["left"].get("mean", 0)
                golden_std = stats["leg_angle"]["left"].get("std", 5.0)
                is_out, diff = self._is_outlier(
                    smoothed_left,
                    golden_left,
                    golden_std,
                    ERROR_THRESHOLDS.get("leg_angle", 10.0),
                    error_type="leg_angle",
                    difficulty_level=difficulty_level,
                    torso_length=torso_length,
                    reference_torso_length=reference_torso_length
                )
                if is_out:
                    desc = f"Chân trái {'quá cao' if smoothed_left > (golden_left or 0) else 'quá thấp'}"
                    errors.append(self._build_error(
                        "leg_angle",
                        desc,
                        diff,
                        "leg",
                        "left"
                    ))
        
        # Check right leg with smoothed value
        if smoothed_right is not None and self.golden_profile and "statistics" in self.golden_profile:
            stats = self.golden_profile["statistics"]
            if "leg_angle" in stats and "right" in stats["leg_angle"]:
                golden_right = stats["leg_angle"]["right"].get("mean", 0)
                golden_std = stats["leg_angle"]["right"].get("std", 5.0)
                is_out, diff = self._is_outlier(
                    smoothed_right,
                    golden_right,
                    golden_std,
                    ERROR_THRESHOLDS.get("leg_angle", 10.0),
                    error_type="leg_angle",
                    difficulty_level=difficulty_level,
                    torso_length=torso_length,
                    reference_torso_length=reference_torso_length
                )
                if is_out:
                    desc = f"Chân phải {'quá cao' if smoothed_right > (golden_right or 0) else 'quá thấp'}"
                    errors.append(self._build_error(
                        "leg_angle",
                        desc,
                        diff,
                        "leg",
                        "right"
                    ))
        
        return errors
    
    def _check_head_posture_smoothed(
        self, 
        keypoints: np.ndarray,
        difficulty_level: Optional[str] = None,
        torso_length: Optional[float] = None,
        reference_torso_length: float = 100.0
    ) -> List[Dict]:
        """
        Kiểm tra tư thế đầu (mũi) với temporal smoothing
        
        Smooths head angle across frames before comparing to golden template.
        """
        errors = []
        
        head_angle = calculate_head_angle(keypoints)
        
        if head_angle is None:
            return errors
        
        # Smooth head angle
        self.metric_smoothers["head_angle"].add_value(head_angle)
        smoothed_head = self.metric_smoothers["head_angle"].get_smoothed_value()
        
        if smoothed_head is None:
            return errors
        
        # Lấy golden statistics nếu có
        golden_mean, golden_std = self._get_golden_stat("head_angle")
        threshold = ERROR_THRESHOLDS.get("head_angle", 30.0)
        
        # Nếu có golden template, so sánh với nó
        if golden_mean is not None and golden_std is not None:
            is_out, diff = self._is_outlier(
                smoothed_head,
                golden_mean,
                golden_std,
                threshold,
                error_type="head_angle",
                difficulty_level=difficulty_level,
                torso_length=torso_length,
                reference_torso_length=reference_torso_length
            )
            
            if is_out:
                # Phân biệt cúi vs ngẩng dựa trên dấu
                if smoothed_head < golden_mean:
                    desc = "Đầu cúi quá thấp"
                else:
                    desc = "Đầu ngẩng quá cao"
                
                errors.append(self._build_error(
                    "head_angle",
                    desc,
                    diff,
                    "nose"
                ))
        else:
            # Không có golden template, dùng threshold tuyệt đối
            if smoothed_head < -threshold:
                diff = abs(smoothed_head) - threshold
                errors.append(self._build_error(
                    "head_angle",
                    f"Đầu cúi quá thấp ({smoothed_head:.1f}°)",
                    diff,
                    "nose"
                ))
            elif smoothed_head > threshold:
                diff = smoothed_head - threshold
                errors.append(self._build_error(
                    "head_angle",
                    f"Đầu ngẩng quá cao ({smoothed_head:.1f}°)",
                    diff,
                    "nose"
                ))
        
        return errors
    
    def reset_smoothers(self) -> None:
        """
        Reset all temporal smoothers
        
        Should be called when starting a new video or session to ensure
        smoothing doesn't carry over from previous frames.
        """
        if self.keypoint_smoother is not None:
            self.keypoint_smoother.reset()
        
        if self.metric_smoothers is not None:
            for smoother in self.metric_smoothers.values():
                smoother.reset()
    
    def process_video_with_dtw(
        self,
        test_keypoints_sequence: List[np.ndarray],
        golden_keypoints_sequence: Optional[List[np.ndarray]] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Xử lý video test với DTW alignment để xử lý tempo variations
        
        Args:
            test_keypoints_sequence: List of keypoints arrays từ test video
            golden_keypoints_sequence: List of keypoints arrays từ golden video
                                       (nếu None, sẽ dùng self.golden_keypoints)
        
        Returns:
            Tuple (errors, alignment_info):
                - errors: List các error dicts từ việc so sánh aligned frames
                - alignment_info: Dict chứa thông tin về alignment (tempo ratio, etc.)
        """
        # Check if DTW is enabled
        if not DTW_CONFIG.get("enabled", False):
            print("⚠️ DTW is disabled in config. Enable it by setting DTW_CONFIG['enabled'] = True")
            return [], {}
        
        # Use golden keypoints from loaded template if not provided
        if golden_keypoints_sequence is None:
            if self.golden_keypoints is None:
                print("⚠️ No golden keypoints available. Load golden template first.")
                return [], {}
            golden_keypoints_sequence = self.golden_keypoints
        
        # Validate inputs
        if not test_keypoints_sequence or not golden_keypoints_sequence:
            print("⚠️ Empty keypoints sequences provided")
            return [], {}
        
        # Initialize DTW aligner with config
        window_size = DTW_CONFIG.get("window_size", 50)
        distance_metric = DTW_CONFIG.get("distance_metric", "euclidean")
        
        aligner = DTWAligner(window_size=window_size, distance_metric=distance_metric)
        
        # Align sequences
        print(f"🔄 Aligning {len(test_keypoints_sequence)} test frames with {len(golden_keypoints_sequence)} golden frames...")
        dtw_distance, alignment_path = aligner.align_sequences(
            test_keypoints_sequence,
            golden_keypoints_sequence
        )
        
        # Get alignment info
        alignment_info = aligner.get_alignment_info()
        if alignment_info:
            print(f"✅ DTW Alignment complete:")
            print(f"   - Tempo ratio: {alignment_info['tempo_ratio']:.2f}x")
            print(f"   - Path length: {alignment_info['path_length']}")
            print(f"   - DTW distance: {dtw_distance:.2f}")
        
        # Compare aligned frames
        errors = []
        for test_idx in range(len(test_keypoints_sequence)):
            golden_idx = aligner.get_aligned_frame(test_idx)
            
            if golden_idx is None or golden_idx >= len(golden_keypoints_sequence):
                continue
            
            test_keypoints = test_keypoints_sequence[test_idx]
            golden_keypoints = golden_keypoints_sequence[golden_idx]
            
            # Validate keypoints shape
            if test_keypoints.shape[0] < 17 or test_keypoints.shape[1] < 3:
                continue
            
            # Detect posture errors for this aligned pair
            frame_errors = self.detect_posture_errors(
                keypoints=test_keypoints,
                frame_number=test_idx,
                timestamp=test_idx / 30.0  # Assume 30 fps
            )
            
            # Add golden frame info to errors
            for error in frame_errors:
                error["golden_frame"] = golden_idx
                error["test_frame"] = test_idx
            
            errors.extend(frame_errors)
        
        return errors, alignment_info
    
    def process_video_sequence(
        self,
        frame_errors: List[Dict],
        initial_score: Optional[float] = None
    ) -> Tuple[float, List[Dict]]:
        """
        Process entire video with sequence-based error grouping
        
        This method groups consecutive frame errors into sequences to avoid over-penalization.
        Instead of penalizing each frame independently (600 errors → -300 points),
        it groups consecutive errors (600 frames → 1 sequence → -2.6 points).
        
        Args:
            frame_errors: List of frame-by-frame error dicts from detect_posture_errors()
                Each error should have: type, body_part, side (optional), frame_number,
                severity, deduction, description
            initial_score: Starting score (default: from SCORING_CONFIG)
        
        Returns:
            Tuple (final_score, sequence_errors):
                - final_score: Score after applying sequence penalties
                - sequence_errors: List of sequence error dicts with aggregated severity
        
        Example:
            # Detect errors for each frame
            frame_errors = []
            for frame_num, keypoints in enumerate(video_keypoints):
                errors = controller.detect_posture_errors(
                    keypoints=keypoints,
                    frame_number=frame_num
                )
                # Add frame_number to each error
                for error in errors:
                    error["frame_number"] = frame_num
                frame_errors.extend(errors)
            
            # Process with sequence grouping
            final_score, sequence_errors = controller.process_video_sequence(frame_errors)
            
            # Result: 600 frame errors → 1 sequence error
            # Deduction: -300 → -2.6 points
        """
        # Check if sequence comparison is enabled
        if self.sequence_comparator is None:
            # Fallback to frame-by-frame scoring
            if initial_score is None:
                initial_score = SCORING_CONFIG.get("initial_score", 100.0)
            
            total_deduction = sum(e.get("deduction", 0.0) for e in frame_errors)
            final_score = initial_score - total_deduction
            
            return final_score, frame_errors
        
        # Use sequence comparator
        if initial_score is None:
            initial_score = SCORING_CONFIG.get("initial_score", 100.0)
        
        final_score, sequence_errors = self.sequence_comparator.calculate_sequence_score(
            frame_errors=frame_errors,
            initial_score=initial_score
        )
        
        return final_score, sequence_errors
    
    # ===================== Multi-Person Methods =====================
    
    def enable_multi_person_mode(self, golden_templates: Dict[str, Dict]):
        """
        Enable multi-person mode with multiple golden templates
        
        Args:
            golden_templates: Dict mapping template_id to template data
                {
                    "template_id": {
                        "keypoints": np.ndarray [n_frames, 17, 3] or [17, 3],
                        "profile": dict (optional)
                    }
                }
        """
        from backend.app.services.multi_person_tracker import MultiPersonManager
        from backend.app.config import MULTI_PERSON_CONFIG
        
        similarity_threshold = MULTI_PERSON_CONFIG.get("similarity_threshold", 0.6)
        self.multi_person_manager = MultiPersonManager(similarity_threshold=similarity_threshold)
        
        # Add all golden templates
        for template_id, template_data in golden_templates.items():
            keypoints = template_data.get("keypoints")
            profile = template_data.get("profile", {})
            self.multi_person_manager.add_golden_template(template_id, keypoints, profile)
        
        # Initialize person tracker
        max_disappeared = MULTI_PERSON_CONFIG.get("max_disappeared", 90)
        iou_threshold = MULTI_PERSON_CONFIG.get("iou_threshold", 0.4)
        enable_reid = MULTI_PERSON_CONFIG.get("reid_features", True)
        from backend.app.services.multi_person_tracker import PersonTracker
        self.person_tracker = PersonTracker(
            max_disappeared=max_disappeared,
            iou_threshold=iou_threshold,
            enable_reid=enable_reid
        )
        
        print(f"✅ Multi-person mode enabled with {len(golden_templates)} templates")
    
    def process_frame_multi_person(self, frame: np.ndarray, frame_number: int) -> Dict[int, List[Dict]]:
        """
        Process frame with multiple people, return errors per person
        
        Args:
            frame: Input frame
            frame_number: Frame number
            
        Returns:
            Dict mapping person_id to list of errors for that person
        """
        if not hasattr(self, 'person_tracker') or not hasattr(self, 'multi_person_manager'):
            raise ValueError("Multi-person mode not enabled. Call enable_multi_person_mode() first.")
        
        # Detect all persons in frame
        detections = self.pose_service.predict_multi_person(frame)
        detection_keypoints = [d["keypoints"] for d in detections]
        
        # Track persons across frames
        tracked_persons = self.person_tracker.update(detection_keypoints, frame_number)
        
        # Match test persons to golden templates
        matches = self.multi_person_manager.match_test_to_golden(tracked_persons)
        
        # Detect errors for each matched person independently
        person_errors = {}
        for person_id, keypoints in tracked_persons.items():
            # Get matched template
            template_id = matches.get(person_id)
            if template_id is None:
                # Person not matched to any template, skip
                continue
            
            # Get template data
            template_data = self.multi_person_manager.get_template_data(template_id)
            if template_data is None:
                continue
            
            # Temporarily set golden template for this person
            # Note: This modifies instance state but is safe because:
            # 1. We save and restore original values in same method call
            # 2. detect_posture_errors is designed to use instance variables
            # 3. Not intended for concurrent use (single-threaded processing)
            original_profile = self.golden_profile
            original_keypoints = self.golden_keypoints
            
            self.golden_profile = template_data.get("profile", {})
            template_keypoints = template_data.get("keypoints")
            
            # If template has multiple frames, use them; otherwise use single frame
            if template_keypoints.ndim == 3:
                self.golden_keypoints = template_keypoints
            else:
                self.golden_keypoints = template_keypoints[np.newaxis, :]
            
            # Detect errors for this person
            errors = self.detect_posture_errors(keypoints, frame_number=frame_number)
            
            # Add template information to errors
            for error in errors:
                error["person_id"] = person_id
                error["template_id"] = template_id
            
            person_errors[person_id] = errors
            
            # Restore original golden template
            self.golden_profile = original_profile
            self.golden_keypoints = original_keypoints
        
        return person_errors
    
    def process_video_multi_person(self, video_path: str) -> Dict[int, Dict]:
        """
        Process entire video with multiple people
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict mapping person_id to results:
            {
                person_id: {
                    "score": float,
                    "errors": List[Dict],
                    "matched_template": str,
                    "frame_count": int
                }
            }
        """
        import cv2
        from backend.app.config import MULTI_PERSON_CONFIG
        
        if not hasattr(self, 'person_tracker') or not hasattr(self, 'multi_person_manager'):
            raise ValueError("Multi-person mode not enabled. Call enable_multi_person_mode() first.")
        
        # Reset trackers
        self.person_tracker.reset()
        self.multi_person_manager.reset_matches()
        
        # Reset smoothers if enabled
        if self.keypoint_smoother is not None:
            self.keypoint_smoother.reset()
        if self.metric_smoothers is not None:
            for smoother in self.metric_smoothers.values():
                smoother.reset()
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Collect all frame errors per person
        person_frame_errors = {}  # {person_id: [errors]}
        person_frame_counts = {}  # {person_id: frame_count}
        
        frame_number = 0
        batch_size = MULTI_PERSON_CONFIG.get("batch_size", 8)
        
        # Process video frame by frame
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame for all persons
            frame_errors = self.process_frame_multi_person(frame, frame_number)
            
            # Accumulate errors per person
            for person_id, errors in frame_errors.items():
                if person_id not in person_frame_errors:
                    person_frame_errors[person_id] = []
                    person_frame_counts[person_id] = 0
                
                person_frame_errors[person_id].extend(errors)
                person_frame_counts[person_id] += 1
            
            frame_number += 1
        
        cap.release()
        
        # Calculate scores and aggregate results per person
        results = {}
        initial_score = SCORING_CONFIG.get("initial_score", 100.0)
        
        for person_id in person_frame_errors.keys():
            errors = person_frame_errors[person_id]
            
            # Use sequence comparator if enabled
            if self.sequence_comparator is not None:
                score, sequence_errors = self.sequence_comparator.calculate_sequence_score(
                    frame_errors=errors,
                    initial_score=initial_score
                )
            else:
                # Simple scoring without sequence comparison
                total_deduction = sum(e.get("deduction", 0) for e in errors)
                score = max(0.0, initial_score - total_deduction)
                sequence_errors = errors
            
            # Get matched template
            template_id = self.multi_person_manager.get_template_for_person(person_id)
            
            results[person_id] = {
                "score": score,
                "errors": sequence_errors,
                "matched_template": template_id,
                "frame_count": person_frame_counts[person_id]
            }
        
        return results

