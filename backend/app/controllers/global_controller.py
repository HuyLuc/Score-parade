"""
GlobalController - Base controller for Global Mode (Practising and Testing)
Implements motion detection and rhythm checking with beat detection integration
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from backend.app.services.pose_service import PoseService
from backend.app.controllers.ai_controller import AIController
from backend.app.services.sequence_comparison import SequenceComparator
from backend.app.services.multi_person_tracker import PersonTracker
from backend.app.config import (
    MOTION_DETECTION_CONFIG,
    KEYPOINT_INDICES,
    SEQUENCE_COMPARISON_CONFIG,
    MULTI_PERSON_CONFIG,
    SCORING_CONFIG,
)


class GlobalController:
    """
    Base controller for Global Mode
    Handles motion detection, rhythm checking, and error tracking
    """
    
    def __init__(self, session_id: str, pose_service: PoseService):
        """
        Initialize GlobalController
        
        Args:
            session_id: Unique session identifier
            pose_service: Pose estimation service
        """
        self.session_id = session_id
        self.pose_service = pose_service
        self.ai_controller = AIController(pose_service)
        
        # Multi-person tracking
        self.multi_person_enabled = SCORING_CONFIG.get(
            "multi_person_enabled",
            MULTI_PERSON_CONFIG.get("enabled", False),
        )
        self.tracker = None
        if self.multi_person_enabled:
            self.tracker = PersonTracker(
                max_disappeared=MULTI_PERSON_CONFIG.get("max_disappeared", 30),
                iou_threshold=MULTI_PERSON_CONFIG.get("iou_threshold", 0.5),
                enable_reid=MULTI_PERSON_CONFIG.get("enable_reidentification", False),
            )
        
        # Motion detection state (per person if multi)
        self.motion_events: Dict[int, List] = {}  # person_id -> List[(timestamp, keypoints, motion_type)]
        self.prev_keypoints: Dict[int, np.ndarray] = {}
        self.prev_timestamp: Dict[int, float] = {}
        
        # Error tracking per person
        self.errors: Dict[int, List[Dict]] = {}
        self.frame_errors_buffer: Dict[int, List[Dict]] = {}
        
        # Score tracking per person
        self.scores: Dict[int, float] = {}
        self.initial_score = SCORING_CONFIG.get("initial_score", 100.0)
        
        # Configuration
        self.config = MOTION_DETECTION_CONFIG
        
        # Initialize sequence comparator for error grouping
        sequence_enabled = SEQUENCE_COMPARISON_CONFIG.get("enabled", True)
        if sequence_enabled:
            self.sequence_comparator = SequenceComparator(
                min_sequence_length=SEQUENCE_COMPARISON_CONFIG.get("min_sequence_length", 2),
                severity_aggregation=SEQUENCE_COMPARISON_CONFIG.get("severity_aggregation", "mean"),
                max_gap_frames=SEQUENCE_COMPARISON_CONFIG.get("max_gap_frames", 1),
                enabled=True
            )
        else:
            self.sequence_comparator = None
        
    def set_audio(self, audio_path: str):
        """
        Set audio file for beat detection
        
        Args:
            audio_path: Path to audio file
        """
        self.ai_controller.set_beat_detector(audio_path)
        
    def _detect_motion_event(
        self,
        keypoints: np.ndarray,
        timestamp: float,
        prev_keypoints: Optional[np.ndarray] = None
    ) -> Optional[str]:
        """
        Detect motion events (steps, arm swings) by comparing with previous frame
        
        Args:
            keypoints: Current frame keypoints [17, 3] (x, y, confidence)
            timestamp: Current timestamp in seconds
            
        Returns:
            Motion type string or None if no significant motion detected
            Possible values: "step_left", "step_right", "arm_swing_left", "arm_swing_right"
        """
        if prev_keypoints is None or keypoints is None:
            return None
            
        # Get indices for key body parts
        left_ankle_idx = KEYPOINT_INDICES["left_ankle"]
        right_ankle_idx = KEYPOINT_INDICES["right_ankle"]
        left_wrist_idx = KEYPOINT_INDICES["left_wrist"]
        right_wrist_idx = KEYPOINT_INDICES["right_wrist"]
        
        # Extract keypoints with confidence check
        conf_threshold = self.config["confidence_threshold"]
        
        # Check left ankle (step detection)
        if (keypoints[left_ankle_idx, 2] >= conf_threshold and
            prev_keypoints[left_ankle_idx, 2] >= conf_threshold):
            
            dy = abs(keypoints[left_ankle_idx, 1] - prev_keypoints[left_ankle_idx, 1])
            dx = abs(keypoints[left_ankle_idx, 0] - prev_keypoints[left_ankle_idx, 0])
            
            if dy > self.config["step_threshold_y"] or dx > self.config["step_threshold_x"]:
                return "step_left"
        
        # Check right ankle (step detection)
        if (keypoints[right_ankle_idx, 2] >= conf_threshold and
            prev_keypoints[right_ankle_idx, 2] >= conf_threshold):
            
            dy = abs(keypoints[right_ankle_idx, 1] - prev_keypoints[right_ankle_idx, 1])
            dx = abs(keypoints[right_ankle_idx, 0] - prev_keypoints[right_ankle_idx, 0])
            
            if dy > self.config["step_threshold_y"] or dx > self.config["step_threshold_x"]:
                return "step_right"
        
        # Check left wrist (arm swing detection)
        if (keypoints[left_wrist_idx, 2] >= conf_threshold and
            prev_keypoints[left_wrist_idx, 2] >= conf_threshold):
            
            dx = keypoints[left_wrist_idx, 0] - prev_keypoints[left_wrist_idx, 0]
            dy = keypoints[left_wrist_idx, 1] - prev_keypoints[left_wrist_idx, 1]
            distance = np.sqrt(dx**2 + dy**2)
            
            if distance > self.config["arm_threshold"]:
                return "arm_swing_left"
        
        # Check right wrist (arm swing detection)
        if (keypoints[right_wrist_idx, 2] >= conf_threshold and
            prev_keypoints[right_wrist_idx, 2] >= conf_threshold):
            
            dx = keypoints[right_wrist_idx, 0] - prev_keypoints[right_wrist_idx, 0]
            dy = keypoints[right_wrist_idx, 1] - prev_keypoints[right_wrist_idx, 1]
            distance = np.sqrt(dx**2 + dy**2)
            
            if distance > self.config["arm_threshold"]:
                return "arm_swing_right"
        
        return None
    
    def _ensure_person(self, person_id: int):
        """Ensure per-person state exists."""
        if person_id not in self.errors:
            self.errors[person_id] = []
        if person_id not in self.frame_errors_buffer:
            self.frame_errors_buffer[person_id] = []
        if person_id not in self.scores:
            self.scores[person_id] = float(self.initial_score)
        if person_id not in self.motion_events:
            self.motion_events[person_id] = []
        if person_id not in self.prev_keypoints:
            self.prev_keypoints[person_id] = None
        if person_id not in self.prev_timestamp:
            self.prev_timestamp[person_id] = None

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: float,
        frame_number: int
    ) -> Dict:
        """
        Process a single video frame (multi-person aware).
        Returns per-person scores and errors.
        """
        # 1. Detect pose (may return multiple persons)
        detections = self.pose_service.predict(frame)

        # 2. If multi-person enabled, track and assign IDs
        persons: Dict[int, np.ndarray] = {}
        if self.multi_person_enabled and self.tracker:
            persons = self.tracker.update(detections, frame_number)
        else:
            if len(detections) > 0:
                persons = {0: detections[0]}

        # 3. For each person, detect errors and motion
        for person_id, keypoints in persons.items():
            self._ensure_person(person_id)

            posture_errors = self.ai_controller.detect_posture_errors(
                keypoints,
                frame_number=frame_number,
                timestamp=timestamp
            )

            if posture_errors:
                self.frame_errors_buffer[person_id].extend(posture_errors)

            # Motion (optional; keep simple per-person)
            motion_type = self._detect_motion_event(
                keypoints,
                timestamp,
                prev_keypoints=self.prev_keypoints.get(person_id),
            )
            if motion_type:
                self.motion_events[person_id].append((timestamp, keypoints.copy(), motion_type))

            self.prev_keypoints[person_id] = keypoints.copy()
            self.prev_timestamp[person_id] = timestamp

            # Group errors periodically
            if len(self.frame_errors_buffer[person_id]) >= 30:
                self._process_error_grouping(person_id)

        # Optionally process rhythm per person (skipped unless motion batch ready)
        for pid, events in self.motion_events.items():
            if len(events) >= self.config["batch_size"]:
                self._process_rhythm_batch(pid, frame_number, timestamp)

        # Build response per person (only for persons detected in this frame)
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
        }
    
    def _process_error_grouping(self, person_id: int):
        """
        Nhóm các lỗi liên tiếp trong buffer thành sequences
        Tránh phạt nhiều lần cho cùng một lỗi kéo dài
        """
        buffer = self.frame_errors_buffer.get(person_id, [])
        if not buffer:
            return
        
        if self.sequence_comparator is None:
            # Nếu không bật sequence grouping, thêm tất cả lỗi trực tiếp
            for error in buffer:
                self.errors.setdefault(person_id, []).append(error)
                self._handle_error(person_id, error)
            self.frame_errors_buffer[person_id] = []
            return
        
        # Nhóm lỗi thành sequences
        sequence_errors = self.sequence_comparator.group_errors_into_sequences(buffer)
        
        # Thêm các sequence errors vào danh sách lỗi
        # Chỉ thêm các sequence mới (chưa được xử lý)
        for seq_error in sequence_errors:
            # Kiểm tra xem sequence này đã được thêm chưa
            # (dựa trên start_frame và error type)
            is_duplicate = any(
                e.get("start_frame") == seq_error.get("start_frame") and
                e.get("type") == seq_error.get("type") and
                e.get("is_sequence", False)
                for e in self.errors.get(person_id, [])
            )
            
            if not is_duplicate:
                self.errors.setdefault(person_id, []).append(seq_error)
                # Xử lý lỗi (trừ điểm) - sẽ được override trong subclass
                self._handle_error(person_id, seq_error)
        
        # Clear buffer sau khi đã xử lý
        self.frame_errors_buffer[person_id] = []
    
    def _process_rhythm_batch(self, person_id: int, frame_number: int, timestamp: float):
        """
        Process accumulated motion events for rhythm errors
        
        Args:
            frame_number: Current frame number
            timestamp: Current timestamp
        """
        events = self.motion_events.get(person_id, [])
        step_events = [(t, kp) for t, kp, mt in events if "step" in mt]
        
        if len(step_events) > 0:
            # Detect rhythm errors using AI controller
            rhythm_errors = self.ai_controller.detect_rhythm_errors(
                step_events,
                motion_type="step"
            )
            
            # Process each error
            for error in rhythm_errors:
                error["frame_number"] = frame_number
                error["timestamp"] = timestamp
                self.errors.setdefault(person_id, []).append(error)
                self._handle_error(person_id, error)
        
        # Clear processed events
        self.motion_events[person_id] = []
    
    def _handle_error(self, person_id: int, error: Dict):
        """
        Handle detected error - can be overridden by subclasses
        Base implementation does nothing (for practising mode)
        
        Args:
            error: Error dictionary with type, severity, deduction, etc.
        """
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
        """
        Finalize error grouping khi video kết thúc
        Xử lý các lỗi còn lại trong buffer
        """
        for pid in list(self.frame_errors_buffer.keys()):
            if self.frame_errors_buffer[pid]:
                self._process_error_grouping(pid)
    
    def reset(self):
        """Reset controller state"""
        self.motion_events = {}
        self.prev_keypoints = {}
        self.prev_timestamp = {}
        self.errors = {}
        self.frame_errors_buffer = {}
        self.scores = {}
        if self.tracker:
            self.tracker.reset()
