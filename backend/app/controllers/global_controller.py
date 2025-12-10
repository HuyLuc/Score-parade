"""
GlobalController - Điều khiển việc chấm theo chế độ tổng hợp (nhịp, khoảng cách, tốc độ)
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.controllers.video_controller import VideoController
from backend.app.controllers.camera_controller import CameraController
from backend.app.services.scoring_service import ScoringService
from backend.app.services.pose_service import PoseService
from backend.app.controllers.ai_controller import AIController
from backend.app.models.session import ScoringSession, SessionMode, SessionType
from backend.app.models.score import Score
from backend.app.models.session import Error
import numpy as np
import cv2
from scipy.signal import find_peaks


class GlobalController:
    """Base class cho Global Mode controllers"""
    
    def __init__(
        self,
        session: Session,
        scoring_session: ScoringSession,
        camera_controller: CameraController,
        video_controller: VideoController,
        pose_service: PoseService,
        scoring_service: ScoringService,
        ai_controller: AIController = None
    ):
        self.session = session
        self.scoring_session = scoring_session
        self.camera_controller = camera_controller
        self.video_controller = video_controller
        self.pose_service = pose_service
        self.scoring_service = scoring_service
        
        # Tạo AI controller nếu chưa có
        if ai_controller is None:
            ai_controller = AIController(pose_service)
            ai_controller.load_golden_template()
        self.ai_controller = ai_controller
        
        # Lấy score từ Local Mode (nếu có) hoặc tạo mới
        score = self.session.query(Score).filter(
            Score.session_id == scoring_session.id
        ).first()
        
        if score:
            self.score = score
        else:
            # Tạo score mới nếu chưa có
            self.score = Score(
                value=100.0,
                initial_value=100.0,
                session_id=scoring_session.id
            )
            self.session.add(self.score)
            self.session.commit()
        
        # Lưu keypoints sequence để phân tích nhịp, khoảng cách, tốc độ
        self.keypoints_history: List[np.ndarray] = []
        self.frame_timestamps: List[float] = []
        self.max_history = 300  # Lưu tối đa 300 frames (~10 giây @ 30fps)
    
    def process_frame(self, camera_id: int, frame: np.ndarray, timestamp: float) -> Dict:
        """
        Xử lý một frame để phát hiện lỗi tổng hợp
        
        Args:
            camera_id: ID của camera
            frame: Frame từ camera
            timestamp: Timestamp (giây)
            
        Returns:
            Dict chứa errors và score update
        """
        # Detect pose
        keypoints_list = self.pose_service.predict(frame)
        
        if len(keypoints_list) == 0:
            return {
                "errors": [],
                "score_deduction": 0.0,
                "new_score": self.score.value
            }
        
        # Lấy người đầu tiên
        keypoints = keypoints_list[0]
        
        # Thêm vào history
        self.keypoints_history.append(keypoints)
        self.frame_timestamps.append(timestamp)
        
        # Giữ history trong giới hạn
        if len(self.keypoints_history) > self.max_history:
            self.keypoints_history.pop(0)
            self.frame_timestamps.pop(0)
        
        # Phát hiện lỗi tổng hợp (cần ít nhất một số frame)
        errors = []
        if len(self.keypoints_history) >= 30:  # Cần ít nhất 1 giây @ 30fps
            errors = self.detect_global_errors(
                self.keypoints_history,
                self.frame_timestamps,
                frame,
                camera_id
            )
        
        # Tính điểm trừ
        total_deduction = 0.0
        for error in errors:
            total_deduction += error.get("deduction", 0.0)
        
        # Cập nhật score
        if total_deduction > 0:
            self.score.add_deduction(total_deduction, "Lỗi tổng hợp")
            self.session.commit()
        
        return {
            "errors": errors,
            "score_deduction": total_deduction,
            "new_score": self.score.value,
            "is_failed": not self.score.is_passed()
        }
    
    def detect_global_errors(
        self,
        keypoints_sequence: List[np.ndarray],
        timestamps: List[float],
        current_frame: np.ndarray,
        camera_id: int
    ) -> List[Dict]:
        """
        Phát hiện lỗi tổng hợp:
        (i) Nhịp nhạc
        (ii) Khoảng cách (bước chân, vung tay)
        (iii) Tốc độ
        
        Args:
            keypoints_sequence: List các keypoints [n_frames, 17, 3]
            timestamps: List timestamps tương ứng
            current_frame: Frame hiện tại
            camera_id: ID của camera
            
        Returns:
            List các dict chứa thông tin lỗi
        """
        errors = []
        
        # Chuyển thành numpy array
        keypoints_array = np.array(keypoints_sequence)
        
        # 1. Kiểm tra nhịp nhạc
        rhythm_errors = self._check_rhythm(keypoints_array, timestamps)
        errors.extend(rhythm_errors)
        
        # 2. Kiểm tra khoảng cách
        distance_errors = self._check_distance(keypoints_array)
        errors.extend(distance_errors)
        
        # 3. Kiểm tra tốc độ
        speed_errors = self._check_speed(keypoints_array, timestamps)
        errors.extend(speed_errors)
        
        # Lưu video cho mỗi lỗi
        for error in errors:
            video_path = self.save_error_video(
                error["type"],
                camera_id
            )
            if video_path:
                error["video_path"] = video_path
        
        return errors
    
    def _check_rhythm(
        self,
        keypoints_sequence: np.ndarray,
        timestamps: List[float]
    ) -> List[Dict]:
        """
        Kiểm tra nhịp nhạc - các động tác có theo đúng nhịp không
        
        Returns:
            List các lỗi về nhịp
        """
        errors = []
        
        # TODO: So sánh với nhịp nhạc từ audio
        # Tạm thời: kiểm tra tính đều đặn của bước chân
        
        if len(keypoints_sequence) < 60 or len(timestamps) < 60:  # Cần ít nhất 2 giây
            return errors
        
        from backend.app.config import KEYPOINT_INDICES
        
        # Tính độ cao chân qua các frame (Y position - càng nhỏ càng cao)
        left_ankle_heights = []
        right_ankle_heights = []
        
        for keypoints in keypoints_sequence:
            if keypoints.shape[0] > KEYPOINT_INDICES["left_ankle"]:
                left_ankle = keypoints[KEYPOINT_INDICES["left_ankle"]]
                right_ankle = keypoints[KEYPOINT_INDICES["right_ankle"]]
                
                if left_ankle[2] > 0:  # Confidence > 0
                    left_ankle_heights.append(left_ankle[1])  # Y position (nhỏ hơn = cao hơn)
                if right_ankle[2] > 0:
                    right_ankle_heights.append(right_ankle[1])
        
        # Phát hiện bước chân: tìm các điểm cực tiểu (chân lên cao nhất)
        if len(left_ankle_heights) < 10 or len(right_ankle_heights) < 10:
            return errors
        
        # Tính nhịp bước (steps per minute)
        # Tìm các peak (chân lên cao) bằng cách tìm local minima
        
        # Đảo ngược để tìm minima (chân cao = Y nhỏ)
        left_heights_inv = [-h for h in left_ankle_heights]
        right_heights_inv = [-h for h in right_ankle_heights]
        
        left_peaks, _ = find_peaks(left_heights_inv, distance=10)  # Tối thiểu 10 frames giữa các bước
        right_peaks, _ = find_peaks(right_heights_inv, distance=10)
        
        # Tính số bước
        total_steps = len(left_peaks) + len(right_peaks)
        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 1.0
        steps_per_minute = (total_steps / duration) * 60 if duration > 0 else 0
        
        # So sánh với golden template (nếu có)
        if self.ai_controller.golden_profile:
            golden_rhythm = self.ai_controller.golden_profile.get("statistics", {}).get("step_rhythm", {})
            if golden_rhythm and "steps_per_minute" in golden_rhythm:
                golden_spm = golden_rhythm["steps_per_minute"]
                rhythm_std = golden_rhythm.get("std", 5.0)
                
                diff = abs(steps_per_minute - golden_spm)
                if diff > rhythm_std * 2:  # Vượt quá 2 sigma
                    if steps_per_minute > golden_spm:
                        errors.append({
                            "type": "rhythm",
                            "description": f"Nhịp quá nhanh ({steps_per_minute:.1f} vs {golden_spm:.1f} bước/phút)",
                            "severity": min(diff / 10, 10.0),
                            "deduction": 2.0,
                            "body_part": "rhythm"
                        })
                    else:
                        errors.append({
                            "type": "rhythm",
                            "description": f"Nhịp quá chậm ({steps_per_minute:.1f} vs {golden_spm:.1f} bước/phút)",
                            "severity": min(diff / 10, 10.0),
                            "deduction": 2.0,
                            "body_part": "rhythm"
                        })
        
        return errors
    
    def _check_distance(self, keypoints_sequence: np.ndarray) -> List[Dict]:
        """
        Kiểm tra khoảng cách - bước chân và vung tay có quá dài/cao/xa không
        
        Returns:
            List các lỗi về khoảng cách
        """
        errors = []
        
        if len(keypoints_sequence) < 30:
            return errors
        
        from backend.app.config import KEYPOINT_INDICES
        from backend.app.services.geometry import calculate_distance, calculate_leg_height, calculate_arm_height
        
        # Kiểm tra độ cao chân (khi bước)
        max_leg_heights = []
        for keypoints in keypoints_sequence:
            left_height = calculate_leg_height(keypoints, "left")
            right_height = calculate_leg_height(keypoints, "right")
            if left_height:
                max_leg_heights.append(left_height)
            if right_height:
                max_leg_heights.append(right_height)
        
        if max_leg_heights:
            avg_leg_height = np.mean(max_leg_heights)
            max_leg_height = np.max(max_leg_heights)
            
            # So sánh với golden template
            if self.ai_controller.golden_profile:
                golden_stats = self.ai_controller.golden_profile.get("statistics", {})
                if "leg_height" in golden_stats:
                    golden_leg = golden_stats["leg_height"]
                    if isinstance(golden_leg, dict):
                        # Có thể có left/right
                        golden_mean = golden_leg.get("mean", 0) or (
                            (golden_leg.get("left", {}).get("mean", 0) + 
                             golden_leg.get("right", {}).get("mean", 0)) / 2
                        )
                        golden_std = golden_leg.get("std", 10.0) or 10.0
                        
                        diff = abs(max_leg_height - golden_mean)
                        if diff > golden_std * 2:
                            if max_leg_height > golden_mean:
                                errors.append({
                                    "type": "distance",
                                    "description": f"Bước chân quá cao ({max_leg_height:.1f} vs {golden_mean:.1f})",
                                    "severity": min(diff / 10, 10.0),
                                    "deduction": 1.5,
                                    "body_part": "leg"
                                })
                            else:
                                errors.append({
                                    "type": "distance",
                                    "description": f"Bước chân quá thấp ({max_leg_height:.1f} vs {golden_mean:.1f})",
                                    "severity": min(diff / 10, 10.0),
                                    "deduction": 1.5,
                                    "body_part": "leg"
                                })
        
        # Kiểm tra độ cao tay (khi vung)
        max_arm_heights = []
        for keypoints in keypoints_sequence:
            left_height = calculate_arm_height(keypoints, "left")
            right_height = calculate_arm_height(keypoints, "right")
            if left_height:
                max_arm_heights.append(left_height)
            if right_height:
                max_arm_heights.append(right_height)
        
        if max_arm_heights:
            max_arm_height = np.max(max_arm_heights)
            
            # So sánh với golden template
            if self.ai_controller.golden_profile:
                golden_stats = self.ai_controller.golden_profile.get("statistics", {})
                if "arm_height" in golden_stats:
                    golden_arm = golden_stats["arm_height"]
                    if isinstance(golden_arm, dict):
                        golden_mean = golden_arm.get("mean", 0) or (
                            (golden_arm.get("left", {}).get("mean", 0) + 
                             golden_arm.get("right", {}).get("mean", 0)) / 2
                        )
                        golden_std = golden_arm.get("std", 10.0) or 10.0
                        
                        diff = abs(max_arm_height - golden_mean)
                        if diff > golden_std * 2:
                            if max_arm_height > golden_mean:
                                errors.append({
                                    "type": "distance",
                                    "description": f"Vung tay quá cao ({max_arm_height:.1f} vs {golden_mean:.1f})",
                                    "severity": min(diff / 10, 10.0),
                                    "deduction": 1.5,
                                    "body_part": "arm"
                                })
                            else:
                                errors.append({
                                    "type": "distance",
                                    "description": f"Vung tay quá thấp ({max_arm_height:.1f} vs {golden_mean:.1f})",
                                    "severity": min(diff / 10, 10.0),
                                    "deduction": 1.5,
                                    "body_part": "arm"
                                })
        
        return errors
    
    def _check_speed(
        self,
        keypoints_sequence: np.ndarray,
        timestamps: List[float]
    ) -> List[Dict]:
        """
        Kiểm tra tốc độ - động tác có quá nhanh hoặc quá chậm không
        
        Returns:
            List các lỗi về tốc độ
        """
        errors = []
        
        if len(keypoints_sequence) < 60 or len(timestamps) < 60:
            return errors
        
        from backend.app.config import KEYPOINT_INDICES
        
        # Tính tốc độ di chuyển của keypoints (pixels per second)
        # Sử dụng vị trí chân để tính tốc độ
        speeds = []
        
        for i in range(1, len(keypoints_sequence)):
            if i >= len(timestamps):
                break
                
            prev_keypoints = keypoints_sequence[i-1]
            curr_keypoints = keypoints_sequence[i]
            dt = timestamps[i] - timestamps[i-1]
            
            if dt <= 0:
                continue
            
            # Tính tốc độ từ vị trí chân
            if (prev_keypoints.shape[0] > KEYPOINT_INDICES["left_ankle"] and
                curr_keypoints.shape[0] > KEYPOINT_INDICES["left_ankle"]):
                
                prev_ankle = prev_keypoints[KEYPOINT_INDICES["left_ankle"]]
                curr_ankle = curr_keypoints[KEYPOINT_INDICES["left_ankle"]]
                
                if prev_ankle[2] > 0 and curr_ankle[2] > 0:
                    # Tính khoảng cách di chuyển
                    dx = curr_ankle[0] - prev_ankle[0]
                    dy = curr_ankle[1] - prev_ankle[1]
                    distance = np.sqrt(dx*dx + dy*dy)
                    speed = distance / dt  # pixels per second
                    speeds.append(speed)
        
        if not speeds:
            return errors
        
        avg_speed = np.mean(speeds)
        max_speed = np.max(speeds)
        
        # So sánh với golden template (nếu có)
        # TODO: Lưu speed trong golden profile để so sánh
        # Tạm thời: kiểm tra tốc độ có quá nhanh/chậm không
        
        # Ngưỡng tốc độ hợp lý (cần điều chỉnh dựa trên thực tế)
        min_speed = 50  # pixels/second
        max_speed_threshold = 200  # pixels/second
        
        if avg_speed < min_speed:
            errors.append({
                "type": "speed",
                "description": f"Tốc độ quá chậm ({avg_speed:.1f} pixels/s)",
                "severity": (min_speed - avg_speed) / 10,
                "deduction": 1.5,
                "body_part": "speed"
            })
        elif max_speed > max_speed_threshold:
            errors.append({
                "type": "speed",
                "description": f"Tốc độ quá nhanh ({max_speed:.1f} pixels/s)",
                "severity": (max_speed - max_speed_threshold) / 10,
                "deduction": 1.5,
                "body_part": "speed"
            })
        
        return errors
    
    def save_error_video(
        self,
        error_type: str,
        camera_id: int
    ) -> Optional[str]:
        """
        Lưu video khi có lỗi
        
        Args:
            error_type: Loại lỗi
            camera_id: ID của camera
            
        Returns:
            Đường dẫn file video hoặc None
        """
        # Lấy video chunk hiện tại
        video_path = self.video_controller.get_current_chunk_path(camera_id)
        
        if video_path:
            return str(video_path)
        return None


class GlobalTestingController(GlobalController):
    """Controller cho Global Mode - Testing (trừ điểm)"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = SessionMode.TESTING
    
    def process_frame(self, camera_id: int, frame: np.ndarray, timestamp: float) -> Dict:
        """Xử lý frame và trừ điểm nếu có lỗi"""
        result = super().process_frame(camera_id, frame, timestamp)
        
        # Thêm thông tin lỗi vào database
        for error_info in result["errors"]:
            error = Error(
                error_type=error_info["type"],
                description=error_info.get("description", ""),
                severity=error_info.get("severity", 1.0),
                deduction=error_info.get("deduction", 0.0),
                timestamp=error_info.get("timestamp"),
                video_path=error_info.get("video_path"),
                video_start_time=error_info.get("video_start_time"),
                video_end_time=error_info.get("video_end_time"),
                session_id=self.scoring_session.id
            )
            self.session.add(error)
        
        self.session.commit()
        
        return result


class GlobalPractisingController(GlobalController):
    """Controller cho Global Mode - Practising (chỉ hiển thị lỗi)"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = SessionMode.PRACTISING
    
    def process_frame(self, camera_id: int, frame: np.ndarray, timestamp: float) -> Dict:
        """Xử lý frame và chỉ trả về lỗi (không trừ điểm)"""
        result = super().process_frame(camera_id, frame, timestamp)
        
        # Không trừ điểm trong practising mode
        result["score_deduction"] = 0.0
        result["new_score"] = self.score.value  # Giữ nguyên điểm
        
        # Vẫn lưu errors để hiển thị
        for error_info in result["errors"]:
            error = Error(
                error_type=error_info["type"],
                description=error_info.get("description", ""),
                severity=error_info.get("severity", 1.0),
                deduction=0.0,  # Không trừ điểm
                timestamp=error_info.get("timestamp"),
                video_path=error_info.get("video_path"),
                video_start_time=error_info.get("video_start_time"),
                video_end_time=error_info.get("video_end_time"),
                session_id=self.scoring_session.id
            )
            self.session.add(error)
        
        self.session.commit()
        
        return result
    
    def get_error_notifications(self) -> List[Dict]:
        """Lấy danh sách lỗi để hiển thị"""
        errors = self.session.query(Error).filter(
            Error.session_id == self.scoring_session.id
        ).order_by(Error.occurred_at.desc()).limit(10).all()
        
        return [
            {
                "id": e.id,
                "type": e.error_type,
                "description": e.description,
                "timestamp": e.occurred_at.isoformat(),
                "video_path": e.video_path,
                "video_start_time": e.video_start_time,
                "video_end_time": e.video_end_time
            }
            for e in errors
        ]

