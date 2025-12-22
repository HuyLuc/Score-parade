"""
LocalController - Base controller for Local Mode (Làm chậm)
Chỉ kiểm tra tư thế: tay, chân, vai, mũi, cổ, lưng
KHÔNG kiểm tra nhịp/timing (rhythm)
"""
import numpy as np
from typing import Dict, List, Optional
from backend.app.services.pose_service import PoseService
from backend.app.controllers.ai_controller import AIController
from backend.app.services.database_service import DatabaseService
from backend.app.services.multi_person_tracker import PersonTracker
from backend.app.services.tracker_service import TrackerService, Detection
from backend.app.services.bytetrack_service import ByteTrackService
from backend.app.config import (
    SCORING_CONFIG,
    MULTI_PERSON_CONFIG,
)


class LocalController:
    """
    Base controller for Local Mode (Làm chậm)
    Chỉ kiểm tra tư thế, không kiểm tra nhịp/timing
    """
    
    def __init__(self, session_id: str, pose_service: PoseService):
        """
        Initialize LocalController
        
        Args:
            session_id: Unique session identifier
            pose_service: Pose estimation service
        """
        self.session_id = session_id
        self.pose_service = pose_service
        self.ai_controller = AIController(pose_service)
        self.db_service = DatabaseService()
        
        # Load golden template
        self.ai_controller.load_golden_template()
        
        # Multi-person tracking
        self.multi_person_enabled = SCORING_CONFIG.get(
            "multi_person_enabled",
            MULTI_PERSON_CONFIG.get("enabled", False),
        )
        
        # Tracking method selection
        tracking_method = MULTI_PERSON_CONFIG.get("tracking_method", "bytetrack")
        
        self.tracker: Optional[PersonTracker] = None
        self.tracker_service: Optional[TrackerService] = None
        self.bytetrack_service: Optional[ByteTrackService] = None
        
        if self.multi_person_enabled:
            if tracking_method == "bytetrack":
                bytetrack_config = MULTI_PERSON_CONFIG.get("bytetrack", {})
                reid_config = MULTI_PERSON_CONFIG.get("reid", {})
                self.bytetrack_service = ByteTrackService(
                    track_thresh=bytetrack_config.get("track_thresh", 0.5),
                    track_buffer=bytetrack_config.get("track_buffer", 30),
                    match_thresh=bytetrack_config.get("match_thresh", 0.8),
                    high_thresh=bytetrack_config.get("high_thresh", 0.6),
                    low_thresh=bytetrack_config.get("low_thresh", 0.1),
                    use_adaptive_kalman=bytetrack_config.get("use_adaptive_kalman", True),
                    adaptive_kalman_config=bytetrack_config.get("adaptive_kalman", {}),
                    reid_config=reid_config,
                )
            elif tracking_method == "sort":
                self.tracker_service = TrackerService(
                    max_disappeared=MULTI_PERSON_CONFIG.get("max_disappeared", 90),
                    iou_threshold=MULTI_PERSON_CONFIG.get("iou_threshold", 0.4),
                )
            else:
                self.tracker = PersonTracker(
                    max_disappeared=MULTI_PERSON_CONFIG.get("max_disappeared", 90),
                    iou_threshold=MULTI_PERSON_CONFIG.get("iou_threshold", 0.4),
                    enable_reid=MULTI_PERSON_CONFIG.get("reid_features", True)
                )
        
        # Error tracking per person
        self.errors: Dict[int, List[Dict]] = {}
        self.frame_errors_buffer: Dict[int, List[Dict]] = {}
        
        # Score tracking per person
        self.scores: Dict[int, float] = {}
        self.initial_score = SCORING_CONFIG.get("initial_score", 100.0)
        
        # Frame tracking per person
        self.person_first_frame: Dict[int, Optional[int]] = {}
        self.person_last_frame: Dict[int, Optional[int]] = {}
    
    def _ensure_person(self, person_id: int):
        """Ensure per-person state exists."""
        if person_id not in self.errors:
            self.errors[person_id] = []
        if person_id not in self.frame_errors_buffer:
            self.frame_errors_buffer[person_id] = []
        if person_id not in self.scores:
            self.scores[person_id] = float(self.initial_score)
        if person_id not in self.person_first_frame:
            self.person_first_frame[person_id] = None
        if person_id not in self.person_last_frame:
            self.person_last_frame[person_id] = None
    
    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: float,
        frame_number: int
    ) -> Dict:
        """
        Process a single video frame (Local Mode - chỉ kiểm tra tư thế)
        
        Returns:
            Processing results with errors and score per person
        """
        # Detect pose + bbox (multi-person)
        persons: Dict[int, np.ndarray] = {}
        
        if self.multi_person_enabled:
            detections_meta = self.pose_service.predict_multi_person(frame)
            
            if self.bytetrack_service:
                detections_for_bytetrack = []
                for det in detections_meta:
                    detections_for_bytetrack.append({
                        "bbox": det["bbox"],
                        "score": det["confidence"],
                        "keypoints": det["keypoints"]
                    })
                
                tracks = self.bytetrack_service.update(
                    detections_for_bytetrack,
                    frame_number,
                    frame=frame
                )
                for track in tracks:
                    persons[track.track_id] = track.keypoints
                    
            elif self.tracker_service:
                detections_for_tracker = []
                for det in detections_meta:
                    kpts = det["keypoints"]
                    bbox = det["bbox"]
                    conf = det["confidence"]
                    detections_for_tracker.append(Detection(bbox=bbox, score=conf, keypoints=kpts))
                
                tracks = self.tracker_service.update(detections_for_tracker, frame_number)
                for tr in tracks:
                    persons[tr.track_id] = tr.keypoints
                    
            elif self.tracker:
                keypoints_list = [det["keypoints"] for det in detections_meta]
                if len(keypoints_list) > 0:
                    tracked = self.tracker.update(keypoints_list, frame_number)
                    persons = tracked
        else:
            detections = self.pose_service.predict(frame)
            if len(detections) > 0:
                persons = {0: detections[0]}

        # For each person, detect posture errors (chỉ tư thế, không có rhythm)
        for person_id, keypoints in persons.items():
            self._ensure_person(person_id)

            # Update first/last frame
            if self.person_first_frame[person_id] is None:
                self.person_first_frame[person_id] = frame_number
            self.person_last_frame[person_id] = frame_number

            # Detect posture errors (chỉ tư thế: tay, chân, vai, mũi, cổ, lưng)
            posture_errors = self.ai_controller.detect_posture_errors(
                keypoints,
                frame_number=frame_number,
                timestamp=timestamp
            )

            if posture_errors:
                self.frame_errors_buffer[person_id].extend(posture_errors)

            # Group errors periodically
            if len(self.frame_errors_buffer[person_id]) >= 30:
                self._process_error_grouping(person_id)

            # Update DB
            self.db_service.create_or_update_person(
                session_id=self.session_id,
                person_id=person_id,
                score=self.scores.get(person_id, self.initial_score),
                total_errors=len(self.errors.get(person_id, [])),
                status="active",
                first_frame=self.person_first_frame.get(person_id),
                last_frame=self.person_last_frame.get(person_id),
            )

        # Build response per person
        persons_result = []
        current_person_ids = sorted(persons.keys())
        for pid in current_person_ids:
            self._ensure_person(pid)
            persons_result.append({
                "person_id": pid,
                "errors": self.errors.get(pid, []),
                "score": self.scores.get(pid, self.initial_score),
            })

        return {
            "success": True,
            "timestamp": timestamp,
            "frame_number": frame_number,
            "persons": persons_result,
            "multi_person": self.multi_person_enabled,
            "person_ids": current_person_ids,
            "total_persons": len(current_person_ids),
        }
    
    def _process_error_grouping(self, person_id: int):
        """Nhóm các lỗi liên tiếp trong buffer thành sequences"""
        buffer = self.frame_errors_buffer.get(person_id, [])
        if not buffer:
            return
        
        # Simple grouping: add all errors
        for error in buffer:
            self.errors.setdefault(person_id, []).append(error)
            self._handle_error(person_id, error)
        
        self.frame_errors_buffer[person_id] = []
    
    def _handle_error(self, person_id: int, error: Dict):
        """
        Handle detected error - can be overridden by subclasses
        Base implementation does nothing (for practising mode)
        """
        self._save_error_to_db(person_id, error)

    def _save_error_to_db(self, person_id: int, error: Dict):
        """Lưu lỗi vào database"""
        try:
            self.db_service.save_error(
                session_id=self.session_id,
                person_id=person_id,
                error_type=error.get("type") or error.get("error_type") or "unknown",
                severity=float(error.get("severity", 0.0)),
                deduction=float(error.get("deduction", 0.0)),
                message=error.get("description") or error.get("message"),
                frame_number=error.get("frame_number") or error.get("start_frame"),
                timestamp_sec=error.get("timestamp"),
                is_sequence=error.get("is_sequence", False),
                sequence_length=error.get("sequence_length"),
                start_frame=error.get("start_frame"),
                end_frame=error.get("end_frame"),
            )
        except Exception:
            pass
    
    def get_score(self) -> Dict[int, float]:
        """Get current score per person"""
        self.finalize_errors()
        return self.scores
    
    def get_errors(self) -> Dict[int, List[Dict]]:
        """Get all detected errors per person"""
        self.finalize_errors()
        return self.errors
    
    def finalize_errors(self):
        """Finalize error grouping khi video kết thúc"""
        for pid in list(self.frame_errors_buffer.keys()):
            if self.frame_errors_buffer[pid]:
                self._process_error_grouping(pid)
    
    def reset(self):
        """Reset controller state"""
        self.errors = {}
        self.frame_errors_buffer = {}
        self.scores = {}
        self.person_first_frame = {}
        self.person_last_frame = {}
        if self.tracker:
            self.tracker.reset()
        if self.tracker_service:
            self.tracker_service.reset()
        if self.bytetrack_service:
            self.bytetrack_service.reset()

