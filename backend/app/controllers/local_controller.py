"""
LocalController - Điều khiển việc chấm theo chế độ làm chậm (chỉ tư thế)
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.controllers.snapshot_controller import SnapshotController
from backend.app.controllers.video_controller import VideoController
from backend.app.controllers.camera_controller import CameraController
from backend.app.services.scoring_service import ScoringService
from backend.app.services.pose_service import PoseService
from backend.app.controllers.ai_controller import AIController
from backend.app.models.session import ScoringSession, SessionMode, SessionType, CriteriaType
from backend.app.models.score import Score
from backend.app.models.session import Error
from backend.app.models.part_of_body import PartOfBody
import numpy as np
import cv2


class LocalController:
    """Base class cho Local Mode controllers"""
    
    def __init__(
        self,
        session: Session,
        scoring_session: ScoringSession,
        camera_controller: CameraController,
        snapshot_controller: SnapshotController,
        pose_service: PoseService,
        scoring_service: ScoringService,
        ai_controller: AIController = None
    ):
        self.session = session
        self.scoring_session = scoring_session
        self.camera_controller = camera_controller
        self.snapshot_controller = snapshot_controller
        self.pose_service = pose_service
        self.scoring_service = scoring_service
        
        # Tạo AI controller nếu chưa có
        if ai_controller is None:
            ai_controller = AIController(pose_service)
            # Load golden template
            ai_controller.load_golden_template()
        self.ai_controller = ai_controller
        
        # Khởi tạo score
        self.score = Score(
            value=100.0,
            initial_value=100.0,
            session_id=scoring_session.id
        )
        self.session.add(self.score)
        self.session.commit()
        
        # Các bộ phận cần kiểm tra trong Local Mode
        self.body_parts_to_check = [
            "arm", "leg", "shoulder", "nose", "neck", "back"
        ]
    
    def process_frame(self, camera_id: int, frame: np.ndarray) -> Dict:
        """
        Xử lý một frame để phát hiện lỗi tư thế
        
        Args:
            camera_id: ID của camera
            frame: Frame từ camera
            
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
        
        # Lấy người đầu tiên (có thể cải thiện bằng tracking)
        keypoints = keypoints_list[0]
        
        # Phát hiện lỗi tư thế
        # TODO: Lấy frame_number và timestamp từ metadata
        errors = self.detect_posture_errors(
            keypoints,
            frame,
            camera_id,
            frame_number=0,  # TODO: Get from metadata
            timestamp=0.0  # TODO: Get from metadata
        )
        
        # Tính điểm trừ
        total_deduction = 0.0
        for error in errors:
            total_deduction += error.get("deduction", 0.0)
        
        # Cập nhật score
        if total_deduction > 0:
            self.score.add_deduction(total_deduction, "Lỗi tư thế")
            self.session.commit()
        
        return {
            "errors": errors,
            "score_deduction": total_deduction,
            "new_score": self.score.value,
            "is_failed": not self.score.is_passed()
        }
    
    def detect_posture_errors(
        self,
        keypoints: np.ndarray,
        frame: np.ndarray,
        camera_id: int,
        frame_number: int = 0,
        timestamp: float = 0.0
    ) -> List[Dict]:
        """
        Phát hiện lỗi tư thế (tay, chân, vai, mũi, cổ, lưng)
        
        Args:
            keypoints: Keypoints [17, 3]
            frame: Frame để lưu snapshot nếu có lỗi
            camera_id: ID của camera
            frame_number: Số frame
            timestamp: Timestamp (giây)
            
        Returns:
            List các dict chứa thông tin lỗi
        """
        # Sử dụng AI Controller để phát hiện lỗi
        errors = self.ai_controller.detect_posture_errors(
            keypoints,
            frame_number=frame_number,
            timestamp=timestamp
        )
        
        # Lưu snapshot cho mỗi lỗi
        for error in errors:
            snapshot_path = self.save_error_snapshot(
                error["type"],
                frame,
                camera_id
            )
            if snapshot_path:
                error["snapshot_path"] = snapshot_path
        
        return errors
    
    def save_error_snapshot(
        self,
        error_type: str,
        frame: np.ndarray,
        camera_id: int
    ) -> Optional[str]:
        """
        Lưu snapshot khi có lỗi
        
        Args:
            error_type: Loại lỗi
            frame: Frame chứa lỗi
            camera_id: ID của camera
            
        Returns:
            Đường dẫn file snapshot hoặc None
        """
        result = self.snapshot_controller.capture_snapshot(
            camera_id,
            save=True,
            session_id=self.scoring_session.id
        )
        
        if result:
            _, file_path = result
            return str(file_path)
        return None


class LocalTestingController(LocalController):
    """Controller cho Local Mode - Testing (trừ điểm)"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = SessionMode.TESTING
    
    def process_frame(self, camera_id: int, frame: np.ndarray) -> Dict:
        """
        Xử lý frame và trừ điểm nếu có lỗi
        
        Returns:
            Dict với errors và score deduction
        """
        result = super().process_frame(camera_id, frame)
        
        # Thêm thông tin lỗi vào database
        for error_info in result["errors"]:
            error = Error(
                error_type=error_info["type"],
                description=error_info.get("description", ""),
                severity=error_info.get("severity", 1.0),
                deduction=error_info.get("deduction", 0.0),
                frame_number=error_info.get("frame_number"),
                timestamp=error_info.get("timestamp"),
                snapshot_path=error_info.get("snapshot_path"),
                session_id=self.scoring_session.id
            )
            self.session.add(error)
        
        self.session.commit()
        
        return result


class LocalPractisingController(LocalController):
    """Controller cho Local Mode - Practising (chỉ hiển thị lỗi)"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = SessionMode.PRACTISING
    
    def process_frame(self, camera_id: int, frame: np.ndarray) -> Dict:
        """
        Xử lý frame và chỉ trả về lỗi (không trừ điểm)
        
        Returns:
            Dict với errors (không có deduction)
        """
        result = super().process_frame(camera_id, frame)
        
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
                frame_number=error_info.get("frame_number"),
                timestamp=error_info.get("timestamp"),
                snapshot_path=error_info.get("snapshot_path"),
                session_id=self.scoring_session.id
            )
            self.session.add(error)
        
        self.session.commit()
        
        return result
    
    def get_error_notifications(self) -> List[Dict]:
        """
        Lấy danh sách lỗi để hiển thị (stack notifications)
        
        Returns:
            List các dict chứa thông tin lỗi
        """
        errors = self.session.query(Error).filter(
            Error.session_id == self.scoring_session.id
        ).order_by(Error.occurred_at.desc()).limit(10).all()
        
        return [
            {
                "id": e.id,
                "type": e.error_type,
                "description": e.description,
                "timestamp": e.occurred_at.isoformat(),
                "snapshot_path": e.snapshot_path
            }
            for e in errors
        ]

