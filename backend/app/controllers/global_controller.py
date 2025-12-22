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
from backend.app.services.tracker_service import TrackerService, Detection
from backend.app.services.bytetrack_service import ByteTrackService
from backend.app.services.database_service import DatabaseService
from backend.app.config import (
    MOTION_DETECTION_CONFIG,
    KEYPOINT_INDICES,
    SEQUENCE_COMPARISON_CONFIG,
    MULTI_PERSON_CONFIG,
    SCORING_CONFIG,
    ERROR_THRESHOLDS,
    POST_PROCESSING_FILTERS_CONFIG,
)
from backend.app.services.post_processing_filters import PostProcessingFilters


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
        self.db_service = DatabaseService()
        
        # Multi-person tracking
        self.multi_person_enabled = SCORING_CONFIG.get(
            "multi_person_enabled",
            MULTI_PERSON_CONFIG.get("enabled", False),
        )
        
        # Tracking method selection
        tracking_method = MULTI_PERSON_CONFIG.get("tracking_method", "bytetrack")
        
        # Legacy keypoint-based tracker (giữ lại để tương thích nếu cần)
        self.tracker: Optional[PersonTracker] = None
        # SORT-style tracker
        self.tracker_service: Optional[TrackerService] = None
        # ByteTrack tracker (recommended)
        self.bytetrack_service: Optional[ByteTrackService] = None
        
        if self.multi_person_enabled:
            if tracking_method == "bytetrack":
                # Use ByteTrack (best performance)
                bytetrack_config = MULTI_PERSON_CONFIG.get("bytetrack", {})
                adaptive_kalman_config = bytetrack_config.get("adaptive_kalman", {})
                reid_config = MULTI_PERSON_CONFIG.get("reid", {})
                formation_config = MULTI_PERSON_CONFIG.get("formation_tracking", {})
                self.bytetrack_service = ByteTrackService(
                    track_thresh=bytetrack_config.get("track_thresh", 0.5),
                    track_buffer=bytetrack_config.get("track_buffer", 30),
                    match_thresh=bytetrack_config.get("match_thresh", 0.8),
                    high_thresh=bytetrack_config.get("high_thresh", 0.6),
                    low_thresh=bytetrack_config.get("low_thresh", 0.1),
                    use_adaptive_kalman=bytetrack_config.get("use_adaptive_kalman", True),
                    adaptive_kalman_config=adaptive_kalman_config,
                    reid_config=reid_config,
                    formation_config=formation_config,
                )
            elif tracking_method == "sort":
                # Use SORT-style tracker
                self.tracker_service = TrackerService(
                    max_disappeared=MULTI_PERSON_CONFIG.get("max_disappeared", 90),
                    iou_threshold=MULTI_PERSON_CONFIG.get("iou_threshold", 0.4),
                )
            else:
                # Use legacy tracker
                self.tracker = PersonTracker(
                    max_disappeared=MULTI_PERSON_CONFIG.get("max_disappeared", 90),
                    iou_threshold=MULTI_PERSON_CONFIG.get("iou_threshold", 0.4),
                    enable_reid=MULTI_PERSON_CONFIG.get("reid_features", True)
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

        # Frame tracking per person (để lưu DB)
        self.person_first_frame: Dict[int, Optional[int]] = {}
        self.person_last_frame: Dict[int, Optional[int]] = {}
        
        # Configuration
        self.config = MOTION_DETECTION_CONFIG
        
        # Initialize sequence comparator for error grouping
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
        
        # Initialize post-processing filters
        if POST_PROCESSING_FILTERS_CONFIG.get("enabled", True):
            self.post_processing_filters = PostProcessingFilters(
                config={"post_processing_filters": POST_PROCESSING_FILTERS_CONFIG}
            )
        else:
            self.post_processing_filters = None
        
        # Keypoint history for occlusion interpolation (per person)
        self.keypoints_history: Dict[int, List[np.ndarray]] = {}
        
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
        if person_id not in self.person_first_frame:
            self.person_first_frame[person_id] = None
        if person_id not in self.person_last_frame:
            self.person_last_frame[person_id] = None
        if person_id not in self.keypoints_history:
            self.keypoints_history[person_id] = []

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
        # 1. Detect pose + bbox (multi-person)
        persons: Dict[int, np.ndarray] = {}
        frame_shape = frame.shape[:2]  # (height, width)
        
        if self.multi_person_enabled:
            detections_meta = self.pose_service.predict_multi_person(frame)
            
            # Apply post-processing filters to detections
            if self.post_processing_filters:
                detections_meta = self.post_processing_filters.filter_detections(
                    detections_meta,
                    frame_shape,
                    frame=frame
                )
            
            if self.bytetrack_service:
                # Use ByteTrack (recommended)
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
                
                # Apply velocity filter to tracks
                if self.post_processing_filters:
                    tracks = self.post_processing_filters.filter_tracks(tracks, frame_number)
                
                for track in tracks:
                    persons[track.track_id] = track.keypoints
                    
            elif self.tracker_service:
                # Use SORT-style tracker
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
                # Use legacy tracker
                keypoints_list = [det["keypoints"] for det in detections_meta]
                if len(keypoints_list) > 0:
                    tracked = self.tracker.update(keypoints_list, frame_number)
                    persons = tracked
        else:
            # Fallback: single-person hoặc không bật multi-person
            detections = self.pose_service.predict(frame)
            if len(detections) > 0:
                persons = {0: detections[0]}

        # 3. For each person, detect errors and motion
        for person_id, keypoints in persons.items():
            self._ensure_person(person_id)

            # Cập nhật first/last frame để lưu DB
            if self.person_first_frame[person_id] is None:
                self.person_first_frame[person_id] = frame_number
            self.person_last_frame[person_id] = frame_number

            # Handle occlusion and interpolate missing keypoints
            if self.post_processing_filters:
                # Detect occlusion
                is_occluded, occlusion_ratio = self.post_processing_filters.detect_occlusion(keypoints)
                
                # Interpolate missing keypoints from history
                if person_id in self.keypoints_history and len(self.keypoints_history[person_id]) > 0:
                    keypoints = self.post_processing_filters.interpolate_keypoints(
                        self.keypoints_history[person_id],
                        keypoints
                    )
                
                # Update keypoints history
                self.keypoints_history[person_id].append(keypoints.copy())
                # Keep only recent history (last 10 frames)
                if len(self.keypoints_history[person_id]) > 10:
                    self.keypoints_history[person_id] = self.keypoints_history[person_id][-10:]

            # Get difficulty level from config
            difficulty_level = SCORING_CONFIG.get("difficulty_level", "medium")

            posture_errors = self.ai_controller.detect_posture_errors(
                keypoints,
                frame_number=frame_number,
                timestamp=timestamp,
                difficulty_level=difficulty_level
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
                
                # Kiểm tra rhythm ngay khi phát hiện motion event
                rhythm_errors = self._check_rhythm_for_motion(
                    person_id=person_id,
                    timestamp=timestamp,
                    motion_type=motion_type,
                    frame_number=frame_number
                )
                if rhythm_errors:
                    self.frame_errors_buffer[person_id].extend(rhythm_errors)

            self.prev_keypoints[person_id] = keypoints.copy()
            self.prev_timestamp[person_id] = timestamp

            # Group errors periodically
            if len(self.frame_errors_buffer[person_id]) >= 30:
                self._process_error_grouping(person_id)

            # Cập nhật DB cho person (score và tổng lỗi hiện tại)
            self.db_service.create_or_update_person(
                session_id=self.session_id,
                person_id=person_id,
                score=self.scores.get(person_id, self.initial_score),
                total_errors=len(self.errors.get(person_id, [])),
                status="active",
                first_frame=self.person_first_frame.get(person_id),
                last_frame=self.person_last_frame.get(person_id),
            )

        # Optionally process rhythm per person (skipped unless motion batch ready)
        for pid, events in self.motion_events.items():
            if len(events) >= self.config["batch_size"]:
                self._process_rhythm_batch(pid, frame_number, timestamp)

        # Build response per person (only for persons detected in this frame)
        persons_result = []
        current_person_ids = sorted(persons.keys())
        for pid in current_person_ids:
            self._ensure_person(pid)
            # Get keypoints for this person (convert numpy array to list for JSON serialization)
            keypoints_data = None
            if pid in persons:
                kp = persons[pid]
                # Convert numpy array [17, 3] to list of [x, y, confidence]
                if kp is not None and len(kp.shape) >= 2:
                    keypoints_data = kp.tolist() if hasattr(kp, 'tolist') else kp
            
            persons_result.append({
                "person_id": pid,
                "errors": self.errors.get(pid, []),
                "score": self.scores.get(pid, self.initial_score),
                "keypoints": keypoints_data,  # Add keypoints for skeleton visualization
            })

        # Tính danh sách ID "ổn định" (người thật) dựa trên thống kê từ tracker
        stable_person_ids = []
        max_persons = MULTI_PERSON_CONFIG.get("max_persons", 5)
        
        if self.multi_person_enabled:
            # Ưu tiên ByteTrack nếu có
            if self.bytetrack_service:
                try:
                    # Sử dụng min_track_length từ config để lọc ghost detections
                    min_track_length = MULTI_PERSON_CONFIG.get("min_track_length", 30)
                    stable_person_ids = self.bytetrack_service.get_stable_track_ids(
                        min_frames=min_track_length,  # Sử dụng min_track_length từ config
                        min_height=30.0,        # Giảm từ 40.0 → 30.0 pixels
                        min_frame_ratio=0.40,   # Giảm từ 0.70 → 0.40 (40% frames) cho video ngắn
                        max_persons=max_persons,
                    )
                except Exception as e:
                    print(f"Warning: Could not get stable track IDs from ByteTrack: {e}")
                    stable_person_ids = []
            # Fallback: tracker_service
            elif self.tracker_service:
                try:
                    # Sử dụng min_track_length từ config để lọc ghost detections
                    min_track_length = MULTI_PERSON_CONFIG.get("min_track_length", 30)
                    stable_person_ids = self.tracker_service.get_stable_track_ids(
                        min_frames=min_track_length,  # Sử dụng min_track_length từ config
                        min_height=30.0,
                        min_frame_ratio=0.40,
                    )
                except Exception as e:
                    print(f"Warning: Could not get stable track IDs from tracker_service: {e}")
                    stable_person_ids = []
            # Fallback: legacy tracker
            elif self.tracker:
                try:
                    # Sử dụng min_track_length từ config để lọc ghost detections
                    min_track_length = MULTI_PERSON_CONFIG.get("min_track_length", 30)
                    stable_person_ids = self.tracker.get_stable_person_ids(
                        min_frames=min_track_length,  # Sử dụng min_track_length từ config
                        min_height=30.0,
                        min_frame_ratio=0.40,
                    )
                except Exception as e:
                    print(f"Warning: Could not get stable person IDs from legacy tracker: {e}")
                    stable_person_ids = []

        return {
            "success": True,
            "timestamp": timestamp,
            "frame_number": frame_number,
            "persons": persons_result,
            "multi_person": self.multi_person_enabled,
            "person_ids": current_person_ids,
            "stable_person_ids": stable_person_ids,
            "total_persons": len(stable_person_ids) if stable_person_ids else len(current_person_ids),
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
    
    def _check_rhythm_for_motion(
        self,
        person_id: int,
        timestamp: float,
        motion_type: str,
        frame_number: int
    ) -> List[Dict]:
        """
        Kiểm tra rhythm cho một motion event đơn lẻ
        
        Args:
            person_id: ID của người
            timestamp: Timestamp của motion event (giây)
            motion_type: Loại động tác ("step_left", "step_right", "arm_swing_left", etc.)
            frame_number: Số frame hiện tại
            
        Returns:
            List các rhythm error dicts (rỗng nếu không có lỗi)
        """
        # Chỉ kiểm tra rhythm nếu có beat detector
        if self.ai_controller.beat_detector is None:
            return []
        
        # Chỉ kiểm tra rhythm cho các động tác quan trọng (steps, arm swings)
        if "step" not in motion_type and "arm_swing" not in motion_type:
            return []
        
        # Kiểm tra xem motion event có khớp với beat không
        tolerance = ERROR_THRESHOLDS.get("rhythm", 0.15)
        beat_time = self.ai_controller.beat_detector.get_beat_at_time(timestamp, tolerance)
        
        if beat_time is None:
            # Không có beat trong khoảng tolerance → lỗi rhythm
            # Tìm beat gần nhất để tính diff
            beat_times = self.ai_controller.beat_detector.beat_times
            if beat_times is None or len(beat_times) == 0:
                return []
            
            idx = np.searchsorted(beat_times, timestamp)
            closest_beat = None
            if idx < len(beat_times):
                closest_beat = float(beat_times[idx])
            elif idx > 0:
                closest_beat = float(beat_times[idx - 1])
            
            if closest_beat is None:
                return []
            
            diff = abs(timestamp - closest_beat)
            
            # Tạo error dict
            error = self.ai_controller._build_error(
                error_type="rhythm",
                description=f"Động tác {motion_type} không theo nhịp (lệch {diff:.2f}s)",
                diff=diff,
                body_part=motion_type,
                side=None
            )
            
            # Thêm metadata
            error["frame_number"] = frame_number
            error["timestamp"] = timestamp
            error["motion_type"] = motion_type
            error["expected_beat"] = closest_beat
            error["actual_timestamp"] = timestamp
            
            return [error]
        
        # Có beat trong khoảng tolerance → không có lỗi
        return []
    
    def _process_rhythm_batch(self, person_id: int, frame_number: int, timestamp: float):
        """
        Process accumulated motion events for rhythm errors (legacy method, giữ lại để tương thích)
        
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
        # Base: chỉ lưu DB, không trừ điểm. Subclass có thể trừ điểm.
        self._save_error_to_db(person_id, error)

    def _save_error_to_db(self, person_id: int, error: Dict):
        """Lưu lỗi vào database (an toàn, không raise)."""
        try:
            self.db_service.save_error(
                session_id=self.session_id,
                person_id=person_id,
                error_type=error.get("type") or error.get("error_type") or "unknown",
                severity=float(error.get("severity", 0.0)),
                deduction=float(error.get("deduction", 0.0)),
                message=error.get("message"),
                frame_number=error.get("frame_number") or error.get("start_frame"),
                timestamp_sec=error.get("timestamp"),
                is_sequence=error.get("is_sequence", False),
                sequence_length=error.get("sequence_length"),
                start_frame=error.get("start_frame"),
                end_frame=error.get("end_frame"),
            )
        except Exception:
            # Không làm gián đoạn pipeline nếu lỗi DB
            pass
    
    def get_score(self) -> Dict[int, float]:
        """Get current score per person (ưu tiên chỉ trả về các ID ổn định)."""
        self.finalize_errors()

        # Nếu không bật multi-person, trả toàn bộ
        if not self.multi_person_enabled:
            return self.scores

        # Lấy danh sách ID ổn định từ tracker
        max_persons = MULTI_PERSON_CONFIG.get("max_persons", 5)
        stable_ids = []
        
        # Sử dụng min_track_length từ config để lọc ghost detections
        min_track_length = MULTI_PERSON_CONFIG.get("min_track_length", 30)
        
        if self.bytetrack_service:
            try:
                stable_ids = self.bytetrack_service.get_stable_track_ids(
                    min_frames=min_track_length,  # Sử dụng min_track_length từ config
                    min_height=30.0,        # Giảm từ 40.0 → 30.0
                    min_frame_ratio=0.40,   # Giảm từ 0.70 → 0.40
                    max_persons=max_persons,
                )
            except Exception as e:
                print(f"Warning: Could not get stable track IDs from ByteTrack: {e}")
        elif self.tracker_service:
            try:
                stable_ids = self.tracker_service.get_stable_track_ids(
                    min_frames=min_track_length,  # Sử dụng min_track_length từ config
                    min_height=30.0,
                    min_frame_ratio=0.40,
                )
            except Exception as e:
                print(f"Warning: Could not get stable track IDs: {e}")
        elif self.tracker:
            try:
                # Sử dụng min_track_length từ config để lọc ghost detections
                min_track_length = MULTI_PERSON_CONFIG.get("min_track_length", 30)
                stable_ids = self.tracker.get_stable_person_ids(
                    min_frames=min_track_length,  # Sử dụng min_track_length từ config
                    min_height=30.0,
                    min_frame_ratio=0.40,
                )
            except Exception as e:
                print(f"Warning: Could not get stable person IDs: {e}")

        if not stable_ids:
            # Nếu chưa suy ra được ID ổn định (ví dụ video quá ngắn), trả toàn bộ
            return self.scores

        # Chỉ giữ lại các ID ổn định
        return {pid: score for pid, score in self.scores.items() if pid in stable_ids}
    
    def get_errors(self) -> Dict[int, List[Dict]]:
        """Get all detected errors per person (ưu tiên các ID ổn định)."""
        self.finalize_errors()

        if not self.multi_person_enabled:
            return self.errors

        max_persons = MULTI_PERSON_CONFIG.get("max_persons", 5)
        stable_ids = []
        
        # Sử dụng min_track_length từ config để lọc ghost detections
        min_track_length = MULTI_PERSON_CONFIG.get("min_track_length", 30)
        
        if self.bytetrack_service:
            try:
                stable_ids = self.bytetrack_service.get_stable_track_ids(
                    min_frames=min_track_length,  # Sử dụng min_track_length từ config
                    min_height=30.0,        # Giảm từ 40.0 → 30.0
                    min_frame_ratio=0.40,   # Giảm từ 0.70 → 0.40
                    max_persons=max_persons,
                )
            except Exception:
                pass
        elif self.tracker_service:
            try:
                stable_ids = self.tracker_service.get_stable_track_ids(
                    min_frames=min_track_length,  # Sử dụng min_track_length từ config
                    min_height=30.0,
                    min_frame_ratio=0.40,
                )
            except Exception:
                pass
        elif self.tracker:
            try:
                # Sử dụng min_track_length từ config để lọc ghost detections
                min_track_length = MULTI_PERSON_CONFIG.get("min_track_length", 30)
                stable_ids = self.tracker.get_stable_person_ids(
                    min_frames=min_track_length,  # Sử dụng min_track_length từ config
                    min_height=30.0,
                    min_frame_ratio=0.40,
                )
            except Exception:
                stable_ids = []

        if not stable_ids:
            return self.errors

        return {pid: errs for pid, errs in self.errors.items() if pid in stable_ids}
    
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
        self.person_first_frame = {}
        self.person_last_frame = {}
        self.keypoints_history = {}
        # Reset all trackers
        if self.tracker:
            self.tracker.reset()
        if self.tracker_service:
            self.tracker_service.reset()
        if self.bytetrack_service:
            self.bytetrack_service.reset()
        # Reset post-processing filters
        if self.post_processing_filters and hasattr(self.post_processing_filters.velocity_filter, 'track_history'):
            self.post_processing_filters.velocity_filter.track_history = {}
