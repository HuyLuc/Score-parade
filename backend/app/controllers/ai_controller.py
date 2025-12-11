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
from backend.app.config import GOLDEN_TEMPLATE_DIR, SCORING_CONFIG, ERROR_THRESHOLDS


class AIController:
    """Controller cho AI phát hiện lỗi"""
    
    def __init__(self, pose_service: PoseService):
        self.pose_service = pose_service
        self.golden_profile = None
        self.golden_keypoints = None

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

    def _is_outlier(self, value: float, mean: Optional[float], std: Optional[float], default_threshold: float) -> Tuple[bool, float]:
        """
        Kiểm tra vượt ngưỡng so với golden (mean/std) hoặc ngưỡng mặc định
        
        Sử dụng 3-sigma rule (99.7% confidence interval) thay vì 2-sigma (95%)
        để giảm false positive và tránh trừ điểm quá khắt khe.
        """
        if value is None:
            return False, 0.0
        
        # Thay đổi từ std * 2 → std * 3 (từ 95% CI → 99.7% CI)
        threshold = (std * 3) if std else default_threshold
        if threshold is None or threshold <= 0:
            threshold = default_threshold
        
        diff = abs(value - mean) if mean is not None else 0.0
        return diff > threshold, diff
    
    def load_golden_template(self, template_name: str = None, camera_angle: str = None):
        """
        Load golden template để so sánh
        
        Args:
            template_name: Tên template (None = dùng default)
            camera_angle: Góc quay (None = auto select)
        """
        # TODO: Implement auto-select profile logic từ step5
        # Tạm thời: load profile mặc định
        if template_name:
            template_dir = GOLDEN_TEMPLATE_DIR / template_name
            profile_path = template_dir / "combined_profile.json"
        else:
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
        timestamp: float = 0.0
    ) -> List[Dict]:
        """
        Phát hiện lỗi tư thế (Local Mode)
        
        Args:
            keypoints: Keypoints [17, 3]
            frame_number: Số frame
            timestamp: Timestamp (giây)
            
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
        
        # Kiểm tra từng bộ phận
        # 1. Tay (Arm)
        arm_errors = self._check_arm_posture(keypoints)
        errors.extend(arm_errors)
        
        # 2. Chân (Leg)
        leg_errors = self._check_leg_posture(keypoints)
        errors.extend(leg_errors)
        
        # 3. Vai (Shoulder)
        shoulder_errors = self._check_shoulder_posture(keypoints)
        errors.extend(shoulder_errors)
        
        # 4. Mũi (Nose) - Kiểm tra đầu có cúi không
        nose_errors = self._check_head_posture(keypoints)
        errors.extend(nose_errors)
        
        # 5. Cổ (Neck)
        neck_errors = self._check_neck_posture(keypoints)
        errors.extend(neck_errors)
        
        # 6. Lưng (Back)
        back_errors = self._check_back_posture(keypoints)
        errors.extend(back_errors)
        
        # Thêm metadata
        for error in errors:
            error["frame_number"] = frame_number
            error["timestamp"] = timestamp
        
        return errors
    
    def _check_arm_posture(self, keypoints: np.ndarray) -> List[Dict]:
        """Kiểm tra tư thế tay"""
        errors = []
        
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
                        ERROR_THRESHOLDS.get("arm_angle", 10.0)
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
                        ERROR_THRESHOLDS.get("arm_angle", 10.0)
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
        
        return errors
    
    def _check_leg_posture(self, keypoints: np.ndarray) -> List[Dict]:
        """Kiểm tra tư thế chân"""
        errors = []
        
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
                        ERROR_THRESHOLDS.get("leg_angle", 10.0)
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
                
                # Kiểm tra chân phải
                if "right" in stats["leg_angle"] and right_leg_angle is not None:
                    golden_right = stats["leg_angle"]["right"].get("mean", 0)
                    golden_std = stats["leg_angle"]["right"].get("std", 5.0)
                    is_out, diff = self._is_outlier(
                        right_leg_angle,
                        golden_right,
                        golden_std,
                        ERROR_THRESHOLDS.get("leg_angle", 10.0)
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
    
    def _check_head_posture(self, keypoints: np.ndarray) -> List[Dict]:
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
                threshold
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
                # Ví dụ: head_angle = -40°, threshold = 30° → diff = |-40° - (-30°)| = 10°
                diff = abs(head_angle + threshold)
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
    
    def _check_neck_posture(self, keypoints: np.ndarray) -> List[Dict]:
        """Kiểm tra tư thế cổ"""
        errors = []
        
        # Kiểm tra cổ có thẳng không (dựa vào góc giữa đầu và vai)
        if keypoints.shape[0] >= 2:
            nose = keypoints[0]
            neck = keypoints[1]
            
            if nose[2] > 0 and neck[2] > 0:
                # Tính góc cổ
                # Tạm thời: kiểm tra đơn giản
                pass  # TODO: Implement chi tiết
        
        return errors
    
    def _check_back_posture(self, keypoints: np.ndarray) -> List[Dict]:
        """Kiểm tra tư thế lưng"""
        errors = []
        
        # torso_stability cần nhiều frames để tính variance
        # Nên không kiểm tra ở đây (single frame)
        # torso_stability sẽ được kiểm tra trong global mode với nhiều frames
        
        return errors

