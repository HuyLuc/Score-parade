"""
GlobalController - Base controller for Global Mode (Practising and Testing)
Implements motion detection and rhythm checking with beat detection integration
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from backend.app.services.pose_service import PoseService
from backend.app.controllers.ai_controller import AIController
from backend.app.services.sequence_comparison import SequenceComparator
from backend.app.config import MOTION_DETECTION_CONFIG, KEYPOINT_INDICES, SEQUENCE_COMPARISON_CONFIG


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
        
        # Motion detection state
        self.motion_events = []  # List[(timestamp, keypoints, motion_type)]
        self.prev_keypoints = None  # Previous frame keypoints for comparison
        self.prev_timestamp = None
        
        # Error tracking
        self.errors = []  # All errors (including sequences)
        self.frame_errors_buffer = []  # Buffer để nhóm lỗi liên tiếp
        
        # Score tracking (may be overridden in subclasses)
        self.score = 100.0
        
        # Configuration
        self.config = MOTION_DETECTION_CONFIG
        
        # Initialize sequence comparator for error grouping
        sequence_enabled = SEQUENCE_COMPARISON_CONFIG.get("enabled", True)
        if sequence_enabled:
            self.sequence_comparator = SequenceComparator(
                min_sequence_length=SEQUENCE_COMPARISON_CONFIG.get("min_sequence_length", 5),
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
        timestamp: float
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
        if self.prev_keypoints is None or keypoints is None:
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
            self.prev_keypoints[left_ankle_idx, 2] >= conf_threshold):
            
            dy = abs(keypoints[left_ankle_idx, 1] - self.prev_keypoints[left_ankle_idx, 1])
            dx = abs(keypoints[left_ankle_idx, 0] - self.prev_keypoints[left_ankle_idx, 0])
            
            if dy > self.config["step_threshold_y"] or dx > self.config["step_threshold_x"]:
                return "step_left"
        
        # Check right ankle (step detection)
        if (keypoints[right_ankle_idx, 2] >= conf_threshold and
            self.prev_keypoints[right_ankle_idx, 2] >= conf_threshold):
            
            dy = abs(keypoints[right_ankle_idx, 1] - self.prev_keypoints[right_ankle_idx, 1])
            dx = abs(keypoints[right_ankle_idx, 0] - self.prev_keypoints[right_ankle_idx, 0])
            
            if dy > self.config["step_threshold_y"] or dx > self.config["step_threshold_x"]:
                return "step_right"
        
        # Check left wrist (arm swing detection)
        if (keypoints[left_wrist_idx, 2] >= conf_threshold and
            self.prev_keypoints[left_wrist_idx, 2] >= conf_threshold):
            
            dx = keypoints[left_wrist_idx, 0] - self.prev_keypoints[left_wrist_idx, 0]
            dy = keypoints[left_wrist_idx, 1] - self.prev_keypoints[left_wrist_idx, 1]
            distance = np.sqrt(dx**2 + dy**2)
            
            if distance > self.config["arm_threshold"]:
                return "arm_swing_left"
        
        # Check right wrist (arm swing detection)
        if (keypoints[right_wrist_idx, 2] >= conf_threshold and
            self.prev_keypoints[right_wrist_idx, 2] >= conf_threshold):
            
            dx = keypoints[right_wrist_idx, 0] - self.prev_keypoints[right_wrist_idx, 0]
            dy = keypoints[right_wrist_idx, 1] - self.prev_keypoints[right_wrist_idx, 1]
            distance = np.sqrt(dx**2 + dy**2)
            
            if distance > self.config["arm_threshold"]:
                return "arm_swing_right"
        
        return None
    
    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: float,
        frame_number: int
    ) -> Dict:
        """
        Process a single video frame
        
        Args:
            frame: Video frame (numpy array)
            timestamp: Frame timestamp in seconds
            frame_number: Frame number in video
            
        Returns:
            Dict with processing results including errors and score
        """
        # 1. Detect pose
        keypoints_list = self.pose_service.predict(frame)
        
        # 2. Detect motion events and posture errors if pose detected
        if len(keypoints_list) > 0:
            keypoints = keypoints_list[0]  # Take first person
            
            # Detect posture errors (Local Mode style)
            posture_errors = self.ai_controller.detect_posture_errors(
                keypoints,
                frame_number=frame_number,
                timestamp=timestamp
            )
            
            # Add to buffer for sequence grouping
            if posture_errors:
                self.frame_errors_buffer.extend(posture_errors)
            
            # Detect motion
            motion_type = self._detect_motion_event(keypoints, timestamp)
            
            if motion_type:
                # Add motion event to buffer
                # Copy is necessary because keypoints array may be reused in next frame
                self.motion_events.append((timestamp, keypoints.copy(), motion_type))
            
            # Update previous frame data
            # Copy is necessary to preserve state for comparison in next frame
            self.prev_keypoints = keypoints.copy()
            self.prev_timestamp = timestamp
        
        # 3. Group consecutive errors into sequences (every N frames or at end)
        # Process error grouping periodically to avoid memory buildup
        if len(self.frame_errors_buffer) >= 30:  # Process every 30 frames
            self._process_error_grouping()
        
        # 4. Batch rhythm error detection
        if len(self.motion_events) >= self.config["batch_size"]:
            self._process_rhythm_batch(frame_number, timestamp)
        
        return {
            "success": True,
            "timestamp": timestamp,
            "frame_number": frame_number,
            "errors": self.errors,
            "score": self.score,
            "motion_events_pending": len(self.motion_events)
        }
    
    def _process_error_grouping(self):
        """
        Nhóm các lỗi liên tiếp trong buffer thành sequences
        Tránh phạt nhiều lần cho cùng một lỗi kéo dài
        """
        if not self.frame_errors_buffer:
            return
        
        if self.sequence_comparator is None:
            # Nếu không bật sequence grouping, thêm tất cả lỗi trực tiếp
            for error in self.frame_errors_buffer:
                self.errors.append(error)
                self._handle_error(error)
            self.frame_errors_buffer = []
            return
        
        # Nhóm lỗi thành sequences
        sequence_errors = self.sequence_comparator.group_errors_into_sequences(
            self.frame_errors_buffer
        )
        
        # Thêm các sequence errors vào danh sách lỗi
        # Chỉ thêm các sequence mới (chưa được xử lý)
        for seq_error in sequence_errors:
            # Kiểm tra xem sequence này đã được thêm chưa
            # (dựa trên start_frame và error type)
            is_duplicate = any(
                e.get("start_frame") == seq_error.get("start_frame") and
                e.get("type") == seq_error.get("type") and
                e.get("is_sequence", False)
                for e in self.errors
            )
            
            if not is_duplicate:
                self.errors.append(seq_error)
                # Xử lý lỗi (trừ điểm) - sẽ được override trong subclass
                self._handle_error(seq_error)
        
        # Clear buffer sau khi đã xử lý
        self.frame_errors_buffer = []
    
    def _process_rhythm_batch(self, frame_number: int, timestamp: float):
        """
        Process accumulated motion events for rhythm errors
        
        Args:
            frame_number: Current frame number
            timestamp: Current timestamp
        """
        # Filter step events for rhythm checking
        step_events = [
            (t, kp) for t, kp, mt in self.motion_events 
            if "step" in mt
        ]
        
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
                self.errors.append(error)
                
                # Handle score deduction (can be overridden in subclasses)
                self._handle_error(error)
        
        # Clear processed events
        self.motion_events = []
    
    def _handle_error(self, error: Dict):
        """
        Handle detected error - can be overridden by subclasses
        Base implementation does nothing (for practising mode)
        
        Args:
            error: Error dictionary with type, severity, deduction, etc.
        """
        pass
    
    def get_score(self) -> float:
        """Get current score"""
        # Finalize errors trước khi trả về score
        self.finalize_errors()
        return self.score
    
    def get_errors(self) -> List[Dict]:
        """Get all detected errors"""
        # Finalize errors trước khi trả về
        self.finalize_errors()
        return self.errors
    
    def finalize_errors(self):
        """
        Finalize error grouping khi video kết thúc
        Xử lý các lỗi còn lại trong buffer
        """
        if self.frame_errors_buffer:
            self._process_error_grouping()
    
    def reset(self):
        """Reset controller state"""
        self.motion_events = []
        self.prev_keypoints = None
        self.prev_timestamp = None
        self.errors = []
        self.frame_errors_buffer = []
        self.score = 100.0
