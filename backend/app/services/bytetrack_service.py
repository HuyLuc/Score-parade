"""
ByteTrack implementation for multi-person tracking
Based on ByteTrack: https://arxiv.org/abs/2110.06864

ByteTrack is superior to SORT because:
1. Uses both high and low confidence detections
2. Reduces ID switches significantly
3. Better occlusion handling
4. More robust in crowded scenes
"""
import numpy as np
from typing import List, Tuple, Dict, Optional
from scipy.optimize import linear_sum_assignment
from collections import deque
from backend.app.services.adaptive_kalman_filter import AdaptiveKalmanFilter
from backend.app.services.reid_service import ReIDService
from backend.app.services.formation_tracker import FormationTracker
from backend.app.config import KEYPOINT_INDICES, MULTI_PERSON_CONFIG


def _calculate_torso_length(keypoints: np.ndarray) -> float:
    """
    Tính chiều dài torso (vai → hông) cho 1 frame.
    Sử dụng trung bình vai trái/phải và hông trái/phải.
    """
    ls = KEYPOINT_INDICES["left_shoulder"]
    rs = KEYPOINT_INDICES["right_shoulder"]
    lh = KEYPOINT_INDICES["left_hip"]
    rh = KEYPOINT_INDICES["right_hip"]

    shoulder_y = (keypoints[ls, 1] + keypoints[rs, 1]) / 2.0
    hip_y = (keypoints[lh, 1] + keypoints[rh, 1]) / 2.0
    shoulder_x = (keypoints[ls, 0] + keypoints[rs, 0]) / 2.0
    hip_x = (keypoints[lh, 0] + keypoints[rh, 0]) / 2.0

    return float(np.sqrt((shoulder_x - hip_x) ** 2 + (shoulder_y - hip_y) ** 2))


def _calculate_arm_length(keypoints: np.ndarray) -> float:
    """
    Tính chiều dài tay (vai → cổ tay), lấy trung bình 2 tay.
    """
    ls = KEYPOINT_INDICES["left_shoulder"]
    rs = KEYPOINT_INDICES["right_shoulder"]
    lw = KEYPOINT_INDICES["left_wrist"]
    rw = KEYPOINT_INDICES["right_wrist"]

    left_len = np.sqrt(
        (keypoints[ls, 0] - keypoints[lw, 0]) ** 2
        + (keypoints[ls, 1] - keypoints[lw, 1]) ** 2
    )
    right_len = np.sqrt(
        (keypoints[rs, 0] - keypoints[rw, 0]) ** 2
        + (keypoints[rs, 1] - keypoints[rw, 1]) ** 2
    )

    return float((left_len + right_len) / 2.0)


def calculate_skeleton_consistency(kpts1: np.ndarray, kpts2: np.ndarray) -> float:
    """
    So sánh pose giữa 2 frame liên tiếp của cùng 1 người dựa trên body proportions.

    Body proportions (torso, tỉ lệ tay/torsor) của 1 người về cơ bản không đổi theo thời gian.
    Giá trị trả về càng gần 1.0 thì 2 frame càng giống nhau.
    """
    torso1 = _calculate_torso_length(kpts1)
    torso2 = _calculate_torso_length(kpts2)

    arm_len1 = _calculate_arm_length(kpts1)
    arm_len2 = _calculate_arm_length(kpts2)

    # Tỉ lệ chiều dài tay / chiều dài torso
    arm_ratio1 = arm_len1 / (torso1 + 1e-6)
    arm_ratio2 = arm_len2 / (torso2 + 1e-6)

    proportion_diff = abs(torso1 - torso2) + abs(arm_ratio1 - arm_ratio2)

    return 1.0 / (1.0 + proportion_diff)


class TrackValidator:
    """
    Kiểm tra tính ổn định theo thời gian của từng track dựa trên body proportions.

    Ý tưởng:
    - Với mỗi track, lưu lại lịch sử tỉ lệ arm_len / torso.
    - Nếu độ lệch chuẩn (std) của tỉ lệ này trong một cửa sổ gần nhất quá lớn
      → nhiều khả năng có ID switch / gộp nhiều người vào 1 track.
    - Chỉ coi track là "ổn định" nếu:
        + Đủ độ dài (>= min_track_length)
        + std trong cửa sổ gần nhất <= max_proportion_std.
    """

    def __init__(
        self,
        min_track_length: int = 30,
        window_size: int = 30,
        max_proportion_std: float = 0.15,
        enabled: bool = True,
    ):
        self.min_track_length = int(min_track_length)
        self.window_size = int(window_size)
        self.max_proportion_std = float(max_proportion_std)
        self.enabled = enabled

        # track_id -> {
        #   "body_proportions": [float, ...],
        #   "start_frame": int,
        #   "last_frame": int,
        # }
        self.tracks_history: Dict[int, Dict] = {}

    def update_track(self, track_id: int, keypoints: Optional[np.ndarray], frame_num: int):
        """Cập nhật lịch sử body proportion cho 1 track."""
        if not self.enabled or keypoints is None:
            return

        if track_id not in self.tracks_history:
            self.tracks_history[track_id] = {
                "body_proportions": [],
                "start_frame": frame_num,
                "last_frame": frame_num,
            }

        history = self.tracks_history[track_id]
        history["last_frame"] = frame_num

        torso = _calculate_torso_length(keypoints)
        arm_len = _calculate_arm_length(keypoints)
        proportion = arm_len / (torso + 1e-6)

        history["body_proportions"].append(proportion)

        # Giữ kích thước lịch sử ở mức vừa phải
        if len(history["body_proportions"]) > max(self.window_size * 2, 60):
            history["body_proportions"] = history["body_proportions"][-max(self.window_size * 2, 60) :]

    def is_stable(self, track_id: int) -> bool:
        """
        Kiểm tra track có ổn định hay không.
        - False nếu chưa đủ độ dài (chưa đủ tự tin).
        - False nếu std của body proportion trong cửa sổ gần nhất > ngưỡng.
        """
        if not self.enabled:
            return True

        history = self.tracks_history.get(track_id)
        if history is None:
            return False

        proportions = history.get("body_proportions", [])
        if len(proportions) < self.min_track_length:
            return False

        window = proportions[-self.window_size :]
        if len(window) == 0:
            return False

        prop_std = float(np.std(window))
        return prop_std <= self.max_proportion_std

    def reset(self) -> None:
        """
        Reset toàn bộ lịch sử track.

        Được gọi khi tracker được reset giữa các video, đảm bảo
        không bị lẫn dữ liệu body_proportions của video trước.
        """
        self.tracks_history.clear()


class STrack:
    """Single Track for ByteTrack"""
    
    _count = 0
    
    def __init__(
        self,
        bbox: np.ndarray,
        score: float,
        keypoints: Optional[np.ndarray] = None,
        use_adaptive_kalman: bool = True,
        adaptive_kalman_config: Optional[Dict] = None
    ):
        """
        Args:
            bbox: [x1, y1, x2, y2]
            score: detection confidence
            keypoints: [17, 3] keypoints if available
            use_adaptive_kalman: Use AdaptiveKalmanFilter instead of simple KalmanFilter
            adaptive_kalman_config: Configuration for AdaptiveKalmanFilter
        """
        self.track_id = STrack._count
        STrack._count += 1
        
        # Convert bbox to [x, y, w, h]
        x1, y1, x2, y2 = bbox
        self.bbox_xywh = np.array([
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            x2 - x1,
            y2 - y1
        ])
        
        self.score = score
        self.keypoints = keypoints
        self.embedding: Optional[np.ndarray] = None
        
        # Use Adaptive Kalman Filter
        if use_adaptive_kalman:
            config = adaptive_kalman_config or {}
            self.kalman = AdaptiveKalmanFilter(
                adaptive_enabled=config.get("adaptive_enabled", True),
                base_process_noise=config.get("base_process_noise", 0.1),
                base_measurement_noise=config.get("base_measurement_noise", 1.0),
                motion_history_size=config.get("motion_history_size", 10),
                keypoint_prediction_enabled=config.get("keypoint_prediction_enabled", True)
            )
            # Initialize bbox state
            self.kalman.bbox_state[:4] = self.bbox_xywh
            # Initialize keypoints if available
            if keypoints is not None:
                self.kalman.initialize_keypoints(keypoints)
        else:
            # Fallback to simple KalmanFilter (legacy)
            from backend.app.services.adaptive_kalman_filter import AdaptiveKalmanFilter as SimpleKalman
            self.kalman = SimpleKalman(
                adaptive_enabled=False,
                keypoint_prediction_enabled=False
            )
            self.kalman.bbox_state[:4] = self.bbox_xywh
        
        # Track state
        self.state = 'new'  # new, tracked, lost, removed
        self.is_activated = False
        self.frame_id = 0
        self.tracklet_len = 0
        self.time_since_update = 0
        
        # History for smoothing
        self.bbox_history = deque(maxlen=30)
        self.score_history = deque(maxlen=30)
        
        # Statistics
        self.first_frame = 0
        self.last_frame = 0
        self.total_height = 0.0
        self.frames_seen = 0
    
    def predict(self):
        """Predict next bbox and keypoints using Kalman filter"""
        if self.state != 'tracked':
            self.kalman.bbox_state[4:] = 0  # Reset velocity if lost
            if hasattr(self.kalman, 'keypoint_state') and self.kalman.keypoint_state is not None:
                self.kalman.keypoint_state[34:] = 0  # Reset keypoint velocities
        
        # Predict bbox
        self.bbox_xywh = self.kalman.predict_bbox()
        
        # Predict keypoints if enabled
        if (hasattr(self.kalman, 'keypoint_prediction_enabled') and 
            self.kalman.keypoint_prediction_enabled and 
            self.kalman.keypoint_state is not None):
            predicted_keypoints = self.kalman.predict_keypoints()
            if predicted_keypoints is not None:
                self.keypoints = predicted_keypoints
    
    def update(self, new_track: 'STrack', frame_id: int):
        """Update with new detection"""
        self.frame_id = frame_id
        self.last_frame = frame_id
        self.tracklet_len += 1
        self.time_since_update = 0
        
        # Update Kalman filter (bbox)
        self.bbox_xywh = self.kalman.update_bbox(new_track.bbox_xywh)
        self.score = new_track.score
        
        # Update keypoints if available and prediction enabled
        if (
            hasattr(self.kalman, "keypoint_prediction_enabled")
            and self.kalman.keypoint_prediction_enabled
            and new_track.keypoints is not None
        ):
            updated_keypoints = self.kalman.update_keypoints(new_track.keypoints)
            if updated_keypoints is not None:
                self.keypoints = updated_keypoints
            else:
                self.keypoints = new_track.keypoints
        else:
            # No keypoint prediction or missing keypoints; take detection keypoints
            self.keypoints = new_track.keypoints
        
        # Update history
        self.bbox_history.append(self.bbox_xywh.copy())
        self.score_history.append(self.score)
        
        # Update statistics
        self.frames_seen += 1
        self.total_height += self.bbox_xywh[3]  # height
        
        self.state = 'tracked'
        self.is_activated = True
    
    def activate(self, frame_id: int):
        """Activate a new track"""
        self.frame_id = frame_id
        self.first_frame = frame_id
        self.last_frame = frame_id
        self.tracklet_len = 1
        self.time_since_update = 0
        self.frames_seen = 1
        self.total_height = self.bbox_xywh[3]
        
        self.state = 'tracked'
        self.is_activated = True
    
    def mark_lost(self):
        """Mark track as lost"""
        self.state = 'lost'
    
    def mark_removed(self):
        """Mark track as removed"""
        self.state = 'removed'
    
    def get_bbox_xyxy(self) -> np.ndarray:
        """Get bbox in [x1, y1, x2, y2] format"""
        x, y, w, h = self.bbox_xywh
        return np.array([
            x - w/2,
            y - h/2,
            x + w/2,
            y + h/2
        ])
    
    @staticmethod
    def tlwh_to_xyxy(bbox: np.ndarray) -> np.ndarray:
        """Convert [x, y, w, h] to [x1, y1, x2, y2]"""
        x, y, w, h = bbox
        return np.array([x, y, x + w, y + h])


class ByteTrackService:
    """
    ByteTrack multi-object tracker
    
    Key improvements over SORT:
    1. Two-stage association (high conf + low conf)
    2. Better occlusion handling
    3. Reduced ID switches
    4. More robust in crowded scenes
    """
    
    def __init__(
        self,
        track_thresh: float = 0.5,
        track_buffer: int = 30,
        match_thresh: float = 0.8,
        high_thresh: float = 0.6,
        low_thresh: float = 0.1,
        use_adaptive_kalman: bool = True,
        adaptive_kalman_config: Optional[Dict] = None,
        reid_config: Optional[Dict] = None,
        formation_config: Optional[Dict] = None,
    ):
        """
        Args:
            track_thresh: Detection threshold for tracking
            track_buffer: Number of frames to keep lost tracks
            match_thresh: IOU threshold for matching
            high_thresh: High confidence threshold
            low_thresh: Low confidence threshold (below this = ignore)
            use_adaptive_kalman: Use AdaptiveKalmanFilter instead of simple KalmanFilter
            adaptive_kalman_config: Configuration for AdaptiveKalmanFilter
            reid_config: Configuration for ReID service
            formation_config: Configuration for FormationTracker
        """
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.use_adaptive_kalman = use_adaptive_kalman
        self.adaptive_kalman_config = adaptive_kalman_config or {}
        self.reid_service = ReIDService(reid_config or {"enabled": False})
        self.reid_alpha = float((reid_config or {}).get("alpha", 0.5)) if reid_config else 0.5
        
        # Formation-based tracking (cho điều lệnh đội hình)
        formation_config = formation_config or {}
        if formation_config.get("enabled", False):
            self.formation_tracker = FormationTracker(
                expected_num_people=formation_config.get("expected_num_people", 2),
                init_frames=formation_config.get("init_frames", 30),
                match_threshold=formation_config.get("match_threshold", 200.0),
                ema_alpha=formation_config.get("ema_alpha", 0.1),
                enabled=True
            )
        else:
            self.formation_tracker = None
        
        # Temporal consistency validator (body proportion stability)
        temporal_min_len = MULTI_PERSON_CONFIG.get("min_track_length", 30)
        self.track_validator = TrackValidator(
            min_track_length=temporal_min_len,
            window_size=min(temporal_min_len, 30),
            max_proportion_std=0.15,
            enabled=True,
        )
        
        # Track management
        self.tracked_stracks: List[STrack] = []
        self.lost_stracks: List[STrack] = []
        self.removed_stracks: List[STrack] = []
        
        self.frame_id = 0
    
    def update(self, detections: List[Dict], frame_id: int, frame: Optional[np.ndarray] = None) -> List[STrack]:
        """
        Update tracker with new detections
        
        Args:
            detections: List of {"bbox": [x1,y1,x2,y2], "score": float, "keypoints": np.ndarray}
            frame_id: Current frame number
            frame: Current frame image (optional, for ReID)
        
        Returns:
            List of active tracks
        """
        self.frame_id = frame_id
        
        # Apply formation-based tracking nếu enabled (cho điều lệnh đội hình)
        if self.formation_tracker is not None:
            detections = self.formation_tracker.assign_to_formation(detections, frame_id)
        
        # Separate detections by confidence
        high_dets = []
        low_dets = []
        
        for det in detections:
            score = det["score"]
            emb = self.reid_service.get_embedding(frame, np.array(det["bbox"]), det.get("keypoints"))
            track = STrack(
                det["bbox"],
                score,
                det.get("keypoints"),
                use_adaptive_kalman=self.use_adaptive_kalman,
                adaptive_kalman_config=self.adaptive_kalman_config
            )
            track.embedding = emb
            
            if score >= self.high_thresh:
                high_dets.append(track)
            elif score >= self.low_thresh:
                low_dets.append(track)
        
        # Predict tracked tracks
        for track in self.tracked_stracks:
            track.predict()
        
        # Stage 1: Associate high conf detections with tracked tracks
        matches1, unmatched_tracks1, unmatched_dets1 = self._associate(
            self.tracked_stracks, high_dets, self.match_thresh
        )
        
        # Update matched tracks
        for track_idx, det_idx in matches1:
            track = self.tracked_stracks[track_idx]
            det = high_dets[det_idx]
            track.update(det, self.frame_id)
        
        # Stage 2: Associate remaining tracks with low conf detections
        remaining_tracks = [self.tracked_stracks[i] for i in unmatched_tracks1]
        matches2, unmatched_tracks2, unmatched_dets2 = self._associate(
            remaining_tracks, low_dets, 0.5  # Lower threshold for low conf
        )
        
        # Update matched tracks with low conf
        for track_idx, det_idx in matches2:
            track = remaining_tracks[track_idx]
            det = low_dets[det_idx]
            track.update(det, self.frame_id)
        
        # Mark unmatched tracks as lost
        for i in unmatched_tracks2:
            track = remaining_tracks[i]
            track.mark_lost()
        
        # Stage 3: Associate unmatched high conf detections with lost tracks
        unmatched_high_dets = [high_dets[i] for i in unmatched_dets1]
        matches3, unmatched_tracks3, unmatched_dets3 = self._associate(
            self.lost_stracks, unmatched_high_dets, self.match_thresh
        )
        
        # Reactivate matched lost tracks
        for track_idx, det_idx in matches3:
            track = self.lost_stracks[track_idx]
            det = unmatched_high_dets[det_idx]
            track.update(det, self.frame_id)
            self.tracked_stracks.append(track)
        
        # Remove lost tracks from lost list
        self.lost_stracks = [t for i, t in enumerate(self.lost_stracks) if i not in [m[0] for m in matches3]]
        
        # Initialize new tracks with unmatched high conf detections
        for i in unmatched_dets3:
            det = unmatched_high_dets[i]
            if det.score >= self.track_thresh:
                det.activate(self.frame_id)
                self.tracked_stracks.append(det)
        
        # Update lost tracks
        for track in self.lost_stracks:
            track.time_since_update += 1
            if track.time_since_update > self.track_buffer:
                track.mark_removed()
        
        # Cập nhật lịch sử temporal consistency cho tất cả tracked + lost tracks
        for track in self.tracked_stracks + self.lost_stracks:
            # Sử dụng keypoints hiện tại của track (sau Kalman + update)
            self.track_validator.update_track(track.track_id, track.keypoints, self.frame_id)
        
        # Remove dead tracks
        self.tracked_stracks = [t for t in self.tracked_stracks if t.state == 'tracked']
        self.lost_stracks = [t for t in self.lost_stracks if t.state == 'lost']
        
        # Move removed tracks
        removed = [t for t in self.lost_stracks if t.state == 'removed']
        self.lost_stracks = [t for t in self.lost_stracks if t.state != 'removed']
        self.removed_stracks.extend(removed)
        
        return self.tracked_stracks
    
    def _associate(
        self,
        tracks: List[STrack],
        detections: List[STrack],
        threshold: float
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Associate tracks with detections using Hungarian algorithm
        
        Returns:
            matches: List of (track_idx, det_idx) pairs
            unmatched_tracks: List of unmatched track indices
            unmatched_dets: List of unmatched detection indices
        """
        if len(tracks) == 0 or len(detections) == 0:
            return [], list(range(len(tracks))), list(range(len(detections)))
        
        # Compute IOU + ReID combined cost matrix
        cost_matrix = self._compute_combined_cost(tracks, detections)
        
        # Hungarian algorithm
        row_idx, col_idx = linear_sum_assignment(cost_matrix)
        
        matches = []
        unmatched_tracks = list(range(len(tracks)))
        unmatched_dets = list(range(len(detections)))
        
        for r, c in zip(row_idx, col_idx):
            if cost_matrix[r, c] < 1 - threshold:  # cost = 1 - IOU
                matches.append((r, c))
                if r in unmatched_tracks:
                    unmatched_tracks.remove(r)
                if c in unmatched_dets:
                    unmatched_dets.remove(c)
        
        return matches, unmatched_tracks, unmatched_dets
    
    def _compute_combined_cost(
        self,
        tracks: List[STrack],
        detections: List[STrack]
    ) -> np.ndarray:
        """
        Cost = alpha*(1-IOU) + (1-alpha)*(1-sim)
        Fallback: nếu thiếu embedding, chỉ dùng IOU.
        """
        num_tracks = len(tracks)
        num_dets = len(detections)
        cost_matrix = np.zeros((num_tracks, num_dets))
        
        for i, track in enumerate(tracks):
            bbox1 = track.get_bbox_xyxy()
            emb1 = getattr(track, "embedding", None)
            for j, det in enumerate(detections):
                bbox2 = det.get_bbox_xyxy()
                iou = self._calculate_iou(bbox1, bbox2)
                
                sim = 0.0
                emb2 = getattr(det, "embedding", None)
                if emb1 is not None and emb2 is not None:
                    sim = self.reid_service.cosine_similarity(emb1, emb2)
                
                if emb1 is None or emb2 is None:
                    cost = 1 - iou
                else:
                    alpha = self.reid_alpha
                    cost = alpha * (1 - iou) + (1 - alpha) * (1 - sim)
                cost_matrix[i, j] = cost
        
        return cost_matrix
    
    @staticmethod
    def _calculate_iou(bbox1: np.ndarray, bbox2: np.ndarray) -> float:
        """Calculate IOU between two bboxes [x1, y1, x2, y2]"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        inter = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - inter
        
        return float(inter / union) if union > 0 else 0.0
    
    def get_stable_track_ids(
        self,
        min_frames: int = 30,
        min_height: float = 50.0,
        min_frame_ratio: float = 0.85,
        max_persons: int = 5
    ) -> List[int]:
        """
        Get stable track IDs (real persons in video)
        
        Sử dụng 2 strategies:
        1. Absolute: Track có >= min_frames và đủ height
        2. Relative: Track có frames >= max_frames * min_frame_ratio
        
        Kết hợp cả 2 để handle cả video dài và video ngắn
        
        Args:
            min_frames: Minimum frames to be considered stable (absolute threshold)
            min_height: Minimum average height
            min_frame_ratio: Minimum ratio of frames seen vs max frames (relative threshold)
            max_persons: Maximum number of persons expected in video
        
        Returns:
            List of stable track IDs
        """
        # Collect all tracks (active + removed)
        all_tracks = self.tracked_stracks + self.lost_stracks + self.removed_stracks
        
        # Filter by absolute criteria first
        candidates = []
        for track in all_tracks:
            # Must have minimum frames
            if track.frames_seen < min_frames:
                continue
            
            # Must have minimum height
            avg_height = track.total_height / max(track.frames_seen, 1)
            if avg_height < min_height:
                continue

            # Temporal consistency: body proportions phải ổn định
            if not self.track_validator.is_stable(track.track_id):
                continue
            
            candidates.append((track.track_id, track.frames_seen, avg_height))
        
        if not candidates:
            return []
        
        # Sort by frames_seen descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Strategy 1: Relative threshold
        max_frames_seen = candidates[0][1]  # Highest frames_seen
        threshold = max_frames_seen * min_frame_ratio
        
        stable_ids = [
            track_id for track_id, frames, _ in candidates
            if frames >= threshold
        ]
        
        # Strategy 2: Top-N fallback
        # Nếu relative threshold quá strict, lấy top N tracks
        if len(stable_ids) < max_persons and len(candidates) > len(stable_ids):
            # Lấy thêm các tracks còn lại cho đến max_persons
            remaining_candidates = [
                (tid, f) for tid, f, _ in candidates 
                if tid not in stable_ids
            ]
            
            # Chỉ lấy thêm nếu frames_seen >= 30% max_frames
            relaxed_threshold = max_frames_seen * 0.30
            for tid, frames in remaining_candidates[:max_persons - len(stable_ids)]:
                if frames >= relaxed_threshold:
                    stable_ids.append(tid)
        
        return sorted(stable_ids)
    
    def reset(self):
        """Reset tracker state"""
        self.tracked_stracks = []
        self.lost_stracks = []
        self.removed_stracks = []
        self.frame_id = 0
        STrack._count = 0
        
        # Reset formation tracker nếu có
        if self.formation_tracker is not None:
            self.formation_tracker.reset()
        
        # Reset track validator
        self.track_validator.reset()
