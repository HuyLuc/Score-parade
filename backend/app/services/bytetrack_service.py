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


class KalmanFilter:
    """Simplified Kalman Filter for bbox tracking"""
    
    def __init__(self):
        # State: [x, y, w, h, vx, vy, vw, vh]
        self.state = np.zeros(8)
        self.covariance = np.eye(8) * 10
        
        # Transition matrix (constant velocity model)
        self.F = np.eye(8)
        for i in range(4):
            self.F[i, i+4] = 1
        
        # Measurement matrix
        self.H = np.eye(4, 8)
        
        # Process noise
        self.Q = np.eye(8) * 0.1
        
        # Measurement noise
        self.R = np.eye(4) * 1.0
    
    def predict(self):
        """Predict next state"""
        self.state = self.F @ self.state
        self.covariance = self.F @ self.covariance @ self.F.T + self.Q
        return self.state[:4]
    
    def update(self, measurement: np.ndarray):
        """Update with measurement [x, y, w, h]"""
        y = measurement - self.H @ self.state
        S = self.H @ self.covariance @ self.H.T + self.R
        K = self.covariance @ self.H.T @ np.linalg.inv(S)
        
        self.state = self.state + K @ y
        self.covariance = (np.eye(8) - K @ self.H) @ self.covariance
        
        return self.state[:4]


class STrack:
    """Single Track for ByteTrack"""
    
    _count = 0
    
    def __init__(self, bbox: np.ndarray, score: float, keypoints: Optional[np.ndarray] = None):
        """
        Args:
            bbox: [x1, y1, x2, y2]
            score: detection confidence
            keypoints: [17, 3] keypoints if available
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
        
        # Kalman filter
        self.kalman = KalmanFilter()
        self.kalman.state[:4] = self.bbox_xywh
        
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
        """Predict next bbox using Kalman filter"""
        if self.state != 'tracked':
            self.kalman.state[4:] = 0  # Reset velocity if lost
        self.bbox_xywh = self.kalman.predict()
    
    def update(self, new_track: 'STrack', frame_id: int):
        """Update with new detection"""
        self.frame_id = frame_id
        self.last_frame = frame_id
        self.tracklet_len += 1
        self.time_since_update = 0
        
        # Update Kalman filter
        self.bbox_xywh = self.kalman.update(new_track.bbox_xywh)
        self.score = new_track.score
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
        low_thresh: float = 0.1
    ):
        """
        Args:
            track_thresh: Detection threshold for tracking
            track_buffer: Number of frames to keep lost tracks
            match_thresh: IOU threshold for matching
            high_thresh: High confidence threshold
            low_thresh: Low confidence threshold (below this = ignore)
        """
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        
        # Track management
        self.tracked_stracks: List[STrack] = []
        self.lost_stracks: List[STrack] = []
        self.removed_stracks: List[STrack] = []
        
        self.frame_id = 0
    
    def update(self, detections: List[Dict], frame_id: int) -> List[STrack]:
        """
        Update tracker with new detections
        
        Args:
            detections: List of {"bbox": [x1,y1,x2,y2], "score": float, "keypoints": np.ndarray}
            frame_id: Current frame number
        
        Returns:
            List of active tracks
        """
        self.frame_id = frame_id
        
        # Separate detections by confidence
        high_dets = []
        low_dets = []
        
        for det in detections:
            score = det["score"]
            track = STrack(det["bbox"], score, det.get("keypoints"))
            
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
        
        # Compute IOU cost matrix
        cost_matrix = self._compute_iou_cost(tracks, detections)
        
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
    
    def _compute_iou_cost(
        self,
        tracks: List[STrack],
        detections: List[STrack]
    ) -> np.ndarray:
        """Compute IOU-based cost matrix"""
        num_tracks = len(tracks)
        num_dets = len(detections)
        cost_matrix = np.zeros((num_tracks, num_dets))
        
        for i, track in enumerate(tracks):
            for j, det in enumerate(detections):
                iou = self._calculate_iou(
                    track.get_bbox_xyxy(),
                    det.get_bbox_xyxy()
                )
                cost_matrix[i, j] = 1 - iou  # Convert to cost
        
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
