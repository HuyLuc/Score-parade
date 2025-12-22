"""
Post-Processing Filters for Multi-Person Tracking
Implements filters to reduce false positives, ID switching, and improve tracking accuracy

Filters:
1. Spatial Consistency Filter - Filters detections with invalid bbox size/position
2. Keypoint Geometric Consistency Filter - Validates anatomical constraints
3. Velocity-Based Filter - Detects and filters tracks with unrealistic motion
4. Occlusion Detection - Identifies and handles occlusion cases
"""
import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)

# Keypoint indices (YOLOv8-pose format: 17 keypoints)
KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]

KEYPOINT_INDICES = {
    "nose": 0, "left_eye": 1, "right_eye": 2, "left_ear": 3, "right_ear": 4,
    "left_shoulder": 5, "right_shoulder": 6,
    "left_elbow": 7, "right_elbow": 8,
    "left_wrist": 9, "right_wrist": 10,
    "left_hip": 11, "right_hip": 12,
    "left_knee": 13, "right_knee": 14,
    "left_ankle": 15, "right_ankle": 16,
}


class SpatialConsistencyFilter:
    """
    Filters detections based on spatial constraints:
    - Bbox size (too small/large)
    - Aspect ratio (person should be standing, not lying)
    - Position (not too close to edges)
    """
    
    def __init__(
        self,
        min_height: float = 50.0,
        max_height_ratio: float = 0.9,
        min_aspect_ratio: float = 0.3,
        max_aspect_ratio: float = 0.7,
        edge_margin_ratio: float = 0.1,
        enabled: bool = True
    ):
        """
        Args:
            min_height: Minimum bbox height in pixels
            max_height_ratio: Maximum height as ratio of frame height
            min_aspect_ratio: Minimum width/height ratio (person standing)
            max_aspect_ratio: Maximum width/height ratio
            edge_margin_ratio: Margin from edges (0.1 = 10% margin)
            enabled: Enable/disable filter
        """
        self.min_height = min_height
        self.max_height_ratio = max_height_ratio
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.edge_margin_ratio = edge_margin_ratio
        self.enabled = enabled
    
    def filter(self, detections: List[Dict], frame_shape: Tuple[int, int]) -> List[Dict]:
        """
        Filter detections based on spatial consistency
        
        Args:
            detections: List of {"bbox": [x1,y1,x2,y2], "score": float, "keypoints": np.ndarray}
            frame_shape: (height, width) of frame
        
        Returns:
            Filtered list of detections
        """
        if not self.enabled:
            return detections
        
        frame_height, frame_width = frame_shape
        filtered = []
        
        for det in detections:
            bbox = det.get("bbox")
            if bbox is None:
                continue
            
            x1, y1, x2, y2 = bbox
            width = x2 - x1
            height = y2 - y1
            
            # Check minimum height
            if height < self.min_height:
                logger.debug(f"Spatial filter: Rejected detection (height too small: {height:.1f}px)")
                continue
            
            # Check maximum height ratio
            if height > frame_height * self.max_height_ratio:
                logger.debug(f"Spatial filter: Rejected detection (height too large: {height:.1f}px)")
                continue
            
            # Check aspect ratio (width/height)
            if height > 0:
                aspect_ratio = width / height
                if aspect_ratio < self.min_aspect_ratio or aspect_ratio > self.max_aspect_ratio:
                    logger.debug(f"Spatial filter: Rejected detection (invalid aspect ratio: {aspect_ratio:.2f})")
                    continue
            
            # Check position (not too close to edges)
            margin_x = frame_width * self.edge_margin_ratio
            margin_y = frame_height * self.edge_margin_ratio
            
            if (x1 < margin_x or x2 > frame_width - margin_x or
                y1 < margin_y or y2 > frame_height - margin_y):
                # Only warn, don't reject (person might be entering/leaving frame)
                logger.debug(f"Spatial filter: Warning - detection near edge")
            
            filtered.append(det)
        
        return filtered


class KeypointGeometricConsistencyFilter:
    """
    Validates keypoints based on anatomical constraints:
    - Torso/leg ratio
    - Head position relative to shoulders
    - Left-right symmetry
    - Limb length constraints
    """
    
    def __init__(
        self,
        min_torso_leg_ratio: float = 0.4,
        max_torso_leg_ratio: float = 0.6,
        max_head_shoulder_ratio: float = 0.3,
        min_symmetry_score: float = 0.7,
        min_confidence: float = 0.3,
        enabled: bool = True
    ):
        """
        Args:
            min_torso_leg_ratio: Minimum torso length / leg length ratio
            max_torso_leg_ratio: Maximum torso length / leg length ratio
            max_head_shoulder_ratio: Maximum head height above shoulders / person height
            min_symmetry_score: Minimum left-right symmetry score (0-1)
            min_confidence: Minimum keypoint confidence to consider
            enabled: Enable/disable filter
        """
        self.min_torso_leg_ratio = min_torso_leg_ratio
        self.max_torso_leg_ratio = max_torso_leg_ratio
        self.max_head_shoulder_ratio = max_head_shoulder_ratio
        self.min_symmetry_score = min_symmetry_score
        self.min_confidence = min_confidence
        self.enabled = enabled
    
    def _calculate_torso_length(self, keypoints: np.ndarray) -> Optional[float]:
        """Calculate torso length (shoulder to hip)"""
        ls_idx = KEYPOINT_INDICES["left_shoulder"]
        rs_idx = KEYPOINT_INDICES["right_shoulder"]
        lh_idx = KEYPOINT_INDICES["left_hip"]
        rh_idx = KEYPOINT_INDICES["right_hip"]
        
        # Get shoulder center
        if (keypoints[ls_idx, 2] >= self.min_confidence and
            keypoints[rs_idx, 2] >= self.min_confidence):
            shoulder_center = (
                (keypoints[ls_idx, 0] + keypoints[rs_idx, 0]) / 2,
                (keypoints[ls_idx, 1] + keypoints[rs_idx, 1]) / 2
            )
        elif keypoints[ls_idx, 2] >= self.min_confidence:
            shoulder_center = (keypoints[ls_idx, 0], keypoints[ls_idx, 1])
        elif keypoints[rs_idx, 2] >= self.min_confidence:
            shoulder_center = (keypoints[rs_idx, 0], keypoints[rs_idx, 1])
        else:
            return None
        
        # Get hip center
        if (keypoints[lh_idx, 2] >= self.min_confidence and
            keypoints[rh_idx, 2] >= self.min_confidence):
            hip_center = (
                (keypoints[lh_idx, 0] + keypoints[rh_idx, 0]) / 2,
                (keypoints[lh_idx, 1] + keypoints[rh_idx, 1]) / 2
            )
        elif keypoints[lh_idx, 2] >= self.min_confidence:
            hip_center = (keypoints[lh_idx, 0], keypoints[lh_idx, 1])
        elif keypoints[rh_idx, 2] >= self.min_confidence:
            hip_center = (keypoints[rh_idx, 0], keypoints[rh_idx, 1])
        else:
            return None
        
        return np.sqrt(
            (shoulder_center[0] - hip_center[0]) ** 2 +
            (shoulder_center[1] - hip_center[1]) ** 2
        )
    
    def _calculate_leg_length(self, keypoints: np.ndarray) -> Optional[float]:
        """Calculate leg length (hip to ankle)"""
        lh_idx = KEYPOINT_INDICES["left_hip"]
        rh_idx = KEYPOINT_INDICES["right_hip"]
        la_idx = KEYPOINT_INDICES["left_ankle"]
        ra_idx = KEYPOINT_INDICES["right_ankle"]
        
        # Use average of left and right legs
        leg_lengths = []
        
        # Left leg
        if (keypoints[lh_idx, 2] >= self.min_confidence and
            keypoints[la_idx, 2] >= self.min_confidence):
            left_leg = np.sqrt(
                (keypoints[lh_idx, 0] - keypoints[la_idx, 0]) ** 2 +
                (keypoints[lh_idx, 1] - keypoints[la_idx, 1]) ** 2
            )
            leg_lengths.append(left_leg)
        
        # Right leg
        if (keypoints[rh_idx, 2] >= self.min_confidence and
            keypoints[ra_idx, 2] >= self.min_confidence):
            right_leg = np.sqrt(
                (keypoints[rh_idx, 0] - keypoints[ra_idx, 0]) ** 2 +
                (keypoints[rh_idx, 1] - keypoints[ra_idx, 1]) ** 2
            )
            leg_lengths.append(right_leg)
        
        if not leg_lengths:
            return None
        
        return np.mean(leg_lengths)
    
    def _calculate_symmetry_score(self, keypoints: np.ndarray) -> float:
        """Calculate left-right symmetry score (0-1)"""
        # Compare left and right body parts
        pairs = [
            ("left_shoulder", "right_shoulder"),
            ("left_elbow", "right_elbow"),
            ("left_wrist", "right_wrist"),
            ("left_hip", "right_hip"),
            ("left_knee", "right_knee"),
            ("left_ankle", "right_ankle"),
        ]
        
        similarities = []
        for left_name, right_name in pairs:
            left_idx = KEYPOINT_INDICES[left_name]
            right_idx = KEYPOINT_INDICES[right_name]
            
            if (keypoints[left_idx, 2] >= self.min_confidence and
                keypoints[right_idx, 2] >= self.min_confidence):
                # Compare Y position (height) - should be similar for standing person
                y_diff = abs(keypoints[left_idx, 1] - keypoints[right_idx, 1])
                # Normalize by person height (approximate)
                person_height = abs(keypoints[KEYPOINT_INDICES["left_ankle"], 1] - 
                                   keypoints[KEYPOINT_INDICES["nose"], 1])
                if person_height > 0:
                    similarity = 1.0 - min(y_diff / person_height, 1.0)
                    similarities.append(similarity)
        
        if not similarities:
            return 0.5  # Default if no pairs available
        
        return np.mean(similarities)
    
    def _check_head_position(self, keypoints: np.ndarray) -> bool:
        """Check if head position is reasonable relative to shoulders"""
        nose_idx = KEYPOINT_INDICES["nose"]
        ls_idx = KEYPOINT_INDICES["left_shoulder"]
        rs_idx = KEYPOINT_INDICES["right_shoulder"]
        
        if keypoints[nose_idx, 2] < self.min_confidence:
            return True  # Can't check
        
        # Get shoulder center Y
        if (keypoints[ls_idx, 2] >= self.min_confidence and
            keypoints[rs_idx, 2] >= self.min_confidence):
            shoulder_y = (keypoints[ls_idx, 1] + keypoints[rs_idx, 1]) / 2
        elif keypoints[ls_idx, 2] >= self.min_confidence:
            shoulder_y = keypoints[ls_idx, 1]
        elif keypoints[rs_idx, 2] >= self.min_confidence:
            shoulder_y = keypoints[rs_idx, 1]
        else:
            return True  # Can't check
        
        # Calculate person height (approximate)
        ankle_y = max(
            keypoints[KEYPOINT_INDICES["left_ankle"], 1] if keypoints[KEYPOINT_INDICES["left_ankle"], 2] >= self.min_confidence else 0,
            keypoints[KEYPOINT_INDICES["right_ankle"], 1] if keypoints[KEYPOINT_INDICES["right_ankle"], 2] >= self.min_confidence else 0
        )
        
        if ankle_y == 0:
            return True  # Can't check
        
        person_height = abs(ankle_y - keypoints[nose_idx, 1])
        head_above_shoulders = abs(keypoints[nose_idx, 1] - shoulder_y)
        
        if person_height > 0:
            ratio = head_above_shoulders / person_height
            return ratio <= self.max_head_shoulder_ratio
        
        return True
    
    def filter(self, detections: List[Dict]) -> List[Dict]:
        """
        Filter detections based on geometric consistency
        
        Args:
            detections: List of {"bbox": [x1,y1,x2,y2], "score": float, "keypoints": np.ndarray}
        
        Returns:
            Filtered list of detections
        """
        if not self.enabled:
            return detections
        
        filtered = []
        
        for det in detections:
            keypoints = det.get("keypoints")
            if keypoints is None or keypoints.shape[0] < 17:
                continue
            
            # Check torso/leg ratio
            torso_length = self._calculate_torso_length(keypoints)
            leg_length = self._calculate_leg_length(keypoints)
            
            if torso_length is not None and leg_length is not None and leg_length > 0:
                ratio = torso_length / leg_length
                if ratio < self.min_torso_leg_ratio or ratio > self.max_torso_leg_ratio:
                    logger.debug(f"Geometric filter: Rejected detection (invalid torso/leg ratio: {ratio:.2f})")
                    continue
            
            # Check head position
            if not self._check_head_position(keypoints):
                logger.debug(f"Geometric filter: Rejected detection (head position invalid)")
                continue
            
            # Check symmetry
            symmetry_score = self._calculate_symmetry_score(keypoints)
            if symmetry_score < self.min_symmetry_score:
                logger.debug(f"Geometric filter: Rejected detection (low symmetry: {symmetry_score:.2f})")
                continue
            
            filtered.append(det)
        
        return filtered


class VelocityBasedFilter:
    """
    Filters tracks based on motion velocity:
    - Maximum velocity threshold
    - Sudden position jumps (ID switching detection)
    - Abrupt appearance/disappearance
    """
    
    def __init__(
        self,
        max_velocity: float = 50.0,  # pixels per frame
        max_jump_distance: float = 100.0,  # pixels
        min_track_length: int = 5,
        enabled: bool = True
    ):
        """
        Args:
            max_velocity: Maximum allowed velocity (pixels/frame)
            max_jump_distance: Maximum allowed position jump in one frame
            min_track_length: Minimum track length to apply velocity check
            enabled: Enable/disable filter
        """
        self.max_velocity = max_velocity
        self.max_jump_distance = max_jump_distance
        self.min_track_length = min_track_length
        self.enabled = enabled
        
        # Track history: track_id -> deque of (frame_id, bbox_center)
        self.track_history: Dict[int, deque] = {}
    
    def _calculate_velocity(self, bbox1: np.ndarray, bbox2: np.ndarray) -> float:
        """Calculate velocity between two bboxes (pixels/frame)"""
        center1 = np.array([(bbox1[0] + bbox1[2]) / 2, (bbox1[1] + bbox1[3]) / 2])
        center2 = np.array([(bbox2[0] + bbox2[2]) / 2, (bbox2[1] + bbox2[3]) / 2])
        return np.linalg.norm(center2 - center1)
    
    def filter_tracks(
        self,
        tracks: List,
        frame_id: int
    ) -> List:
        """
        Filter tracks based on velocity constraints
        
        Args:
            tracks: List of track objects with bbox and track_id
            frame_id: Current frame number
        
        Returns:
            Filtered list of tracks
        """
        if not self.enabled:
            return tracks
        
        filtered = []
        
        for track in tracks:
            track_id = track.track_id if hasattr(track, 'track_id') else getattr(track, 'id', None)
            if track_id is None:
                filtered.append(track)
                continue
            
            # Get bbox
            if hasattr(track, 'get_bbox_xyxy'):
                bbox = track.get_bbox_xyxy()
            elif hasattr(track, 'bbox'):
                bbox = track.bbox
            else:
                filtered.append(track)
                continue
            
            # Initialize history if needed
            if track_id not in self.track_history:
                self.track_history[track_id] = deque(maxlen=10)
            
            history = self.track_history[track_id]
            
            if len(history) > 0:
                # Check velocity
                last_frame_id, last_bbox = history[-1]
                frames_diff = frame_id - last_frame_id
                
                if frames_diff > 0:
                    velocity = self._calculate_velocity(last_bbox, bbox) / frames_diff
                    
                    # Check maximum velocity
                    if velocity > self.max_velocity:
                        logger.debug(f"Velocity filter: Rejected track {track_id} (velocity too high: {velocity:.1f} px/frame)")
                        continue
                    
                    # Check sudden jump (ID switching indicator)
                    if frames_diff == 1:  # Consecutive frames
                        jump_distance = self._calculate_velocity(last_bbox, bbox)
                        if jump_distance > self.max_jump_distance:
                            logger.debug(f"Velocity filter: Rejected track {track_id} (sudden jump: {jump_distance:.1f} px)")
                            continue
            
            # Update history
            bbox_center = np.array([
                (bbox[0] + bbox[2]) / 2,
                (bbox[1] + bbox[3]) / 2
            ])
            history.append((frame_id, bbox))
            
            filtered.append(track)
        
        # Clean up old tracks
        active_track_ids = {t.track_id if hasattr(t, 'track_id') else getattr(t, 'id', None) for t in filtered}
        self.track_history = {tid: hist for tid, hist in self.track_history.items() if tid in active_track_ids}
        
        return filtered


class OcclusionDetector:
    """
    Detects occlusion cases and provides handling strategies:
    - Partial occlusion (>50% visible)
    - Full occlusion (person disappears)
    - Keypoint interpolation for partially occluded keypoints
    """
    
    def __init__(
        self,
        occlusion_threshold: float = 0.5,
        interpolation_window: int = 5,
        enabled: bool = True
    ):
        """
        Args:
            occlusion_threshold: Minimum visible ratio to consider as occlusion
            interpolation_window: Frames to use for keypoint interpolation
            enabled: Enable/disable detector
        """
        self.occlusion_threshold = occlusion_threshold
        self.interpolation_window = interpolation_window
        self.enabled = enabled
    
    def detect_occlusion(self, keypoints: np.ndarray, min_confidence: float = 0.3) -> Tuple[bool, float]:
        """
        Detect if person is occluded
        
        Args:
            keypoints: [17, 3] keypoints array
            min_confidence: Minimum confidence to consider keypoint visible
        
        Returns:
            (is_occluded, occlusion_ratio)
        """
        if not self.enabled:
            return False, 0.0
        
        visible_keypoints = np.sum(keypoints[:, 2] >= min_confidence)
        total_keypoints = keypoints.shape[0]
        visible_ratio = visible_keypoints / total_keypoints
        
        is_occluded = visible_ratio < (1.0 - self.occlusion_threshold)
        occlusion_ratio = 1.0 - visible_ratio
        
        return is_occluded, occlusion_ratio
    
    def interpolate_keypoints(
        self,
        keypoints_history: List[np.ndarray],
        current_keypoints: np.ndarray,
        min_confidence: float = 0.3
    ) -> np.ndarray:
        """
        Interpolate missing keypoints from history
        
        Args:
            keypoints_history: List of previous keypoints arrays
            current_keypoints: Current keypoints array
            min_confidence: Minimum confidence threshold
        
        Returns:
            Interpolated keypoints array
        """
        if not self.enabled or len(keypoints_history) == 0:
            return current_keypoints
        
        interpolated = current_keypoints.copy()
        
        # For each keypoint with low confidence, interpolate from history
        for kp_idx in range(current_keypoints.shape[0]):
            if current_keypoints[kp_idx, 2] < min_confidence:
                # Find valid values in history
                valid_values = []
                for hist_kp in keypoints_history[-self.interpolation_window:]:
                    if hist_kp[kp_idx, 2] >= min_confidence:
                        valid_values.append(hist_kp[kp_idx, :2])
                
                if len(valid_values) > 0:
                    # Use average of valid values
                    interpolated[kp_idx, :2] = np.mean(valid_values, axis=0)
                    interpolated[kp_idx, 2] = 0.5  # Set moderate confidence
        
        return interpolated


class GhostDetectionFilter:
    """
    Lọc "người ảo" (ghost detections) bằng các heuristics:
    1. Số keypoint hợp lệ (ít nhất 8/17)
    2. Body structure hợp lý (torso length trong khoảng hợp lý)
    3. Symmetry (đối xứng tay/chân)
    4. Overlap với detections khác (NMS bổ sung)
    """
    
    def __init__(
        self,
        min_visible_keypoints: int = 8,
        min_torso_length: float = 50.0,
        max_torso_length: float = 500.0,
        max_arm_asymmetry_ratio: float = 0.3,
        nms_iou_threshold: float = 0.5,
        min_confidence: float = 0.5,
        enabled: bool = True
    ):
        """
        Args:
            min_visible_keypoints: Số keypoint tối thiểu phải visible (8/17)
            min_torso_length: Torso length tối thiểu (pixels)
            max_torso_length: Torso length tối đa (pixels)
            max_arm_asymmetry_ratio: Tỷ lệ chênh lệch tay trái/phải tối đa (0.3 = 30%)
            nms_iou_threshold: IoU threshold cho NMS (0.5)
            min_confidence: Confidence tối thiểu cho keypoint (0.5)
            enabled: Enable/disable filter
        """
        self.min_visible_keypoints = min_visible_keypoints
        self.min_torso_length = min_torso_length
        self.max_torso_length = max_torso_length
        self.max_arm_asymmetry_ratio = max_arm_asymmetry_ratio
        self.nms_iou_threshold = nms_iou_threshold
        self.min_confidence = min_confidence
        self.enabled = enabled
    
    def _calculate_torso_length(self, keypoints: np.ndarray) -> Optional[float]:
        """Calculate torso length (shoulder to hip)"""
        ls_idx = KEYPOINT_INDICES["left_shoulder"]
        rs_idx = KEYPOINT_INDICES["right_shoulder"]
        lh_idx = KEYPOINT_INDICES["left_hip"]
        rh_idx = KEYPOINT_INDICES["right_hip"]
        
        # Get shoulder center
        if (keypoints[ls_idx, 2] >= self.min_confidence and
            keypoints[rs_idx, 2] >= self.min_confidence):
            shoulder_center = (
                (keypoints[ls_idx, 0] + keypoints[rs_idx, 0]) / 2,
                (keypoints[ls_idx, 1] + keypoints[rs_idx, 1]) / 2
            )
        elif keypoints[ls_idx, 2] >= self.min_confidence:
            shoulder_center = (keypoints[ls_idx, 0], keypoints[ls_idx, 1])
        elif keypoints[rs_idx, 2] >= self.min_confidence:
            shoulder_center = (keypoints[rs_idx, 0], keypoints[rs_idx, 1])
        else:
            return None
        
        # Get hip center
        if (keypoints[lh_idx, 2] >= self.min_confidence and
            keypoints[rh_idx, 2] >= self.min_confidence):
            hip_center = (
                (keypoints[lh_idx, 0] + keypoints[rh_idx, 0]) / 2,
                (keypoints[lh_idx, 1] + keypoints[rh_idx, 1]) / 2
            )
        elif keypoints[lh_idx, 2] >= self.min_confidence:
            hip_center = (keypoints[lh_idx, 0], keypoints[lh_idx, 1])
        elif keypoints[rh_idx, 2] >= self.min_confidence:
            hip_center = (keypoints[rh_idx, 0], keypoints[rh_idx, 1])
        else:
            return None
        
        return np.sqrt(
            (shoulder_center[0] - hip_center[0]) ** 2 +
            (shoulder_center[1] - hip_center[1]) ** 2
        )
    
    def _calculate_arm_length(self, keypoints: np.ndarray, side: str = "left") -> Optional[float]:
        """
        Calculate arm length (shoulder to wrist)
        
        Args:
            keypoints: [17, 3] keypoints array
            side: "left" or "right"
        
        Returns:
            Arm length in pixels or None if not available
        """
        if side == "left":
            shoulder_idx = KEYPOINT_INDICES["left_shoulder"]
            wrist_idx = KEYPOINT_INDICES["left_wrist"]
        else:
            shoulder_idx = KEYPOINT_INDICES["right_shoulder"]
            wrist_idx = KEYPOINT_INDICES["right_wrist"]
        
        if (keypoints[shoulder_idx, 2] >= self.min_confidence and
            keypoints[wrist_idx, 2] >= self.min_confidence):
            return np.sqrt(
                (keypoints[shoulder_idx, 0] - keypoints[wrist_idx, 0]) ** 2 +
                (keypoints[shoulder_idx, 1] - keypoints[wrist_idx, 1]) ** 2
            )
        return None
    
    @staticmethod
    def _calculate_iou(bbox1: np.ndarray, bbox2: np.ndarray) -> float:
        """Calculate IoU between two bboxes [x1, y1, x2, y2]"""
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
    
    def filter_ghosts(
        self,
        detections: List[Dict],
        frame: Optional[np.ndarray] = None
    ) -> List[Dict]:
        """
        Lọc các ghost detections bằng heuristics
        
        Args:
            detections: List of {"bbox": [x1,y1,x2,y2], "score": float, "keypoints": np.ndarray}
            frame: Current frame image (optional, không dùng trong implementation hiện tại)
        
        Returns:
            List of valid detections (ghost detections đã bị lọc)
        """
        if not self.enabled:
            return detections
        
        valid_detections = []
        
        for det in detections:
            kpts = det.get('keypoints')
            bbox = det.get('bbox')
            
            if kpts is None or bbox is None:
                continue
            
            # Check 1: Số điểm keypoint hợp lệ
            visible_kpts = np.sum(kpts[:, 2] >= self.min_confidence)
            if visible_kpts < self.min_visible_keypoints:
                logger.debug(f"Ghost filter: Rejected detection (insufficient keypoints: {visible_kpts}/{len(kpts)})")
                continue
            
            # Check 2: Body structure hợp lý (torso length)
            torso = self._calculate_torso_length(kpts)
            if torso is None:
                logger.debug(f"Ghost filter: Rejected detection (cannot calculate torso)")
                continue
            
            if torso < self.min_torso_length or torso > self.max_torso_length:
                logger.debug(f"Ghost filter: Rejected detection (invalid torso length: {torso:.1f}px)")
                continue
            
            # Check 3: Symmetry (đối xứng tay/chân)
            left_arm = self._calculate_arm_length(kpts, side='left')
            right_arm = self._calculate_arm_length(kpts, side='right')
            
            if left_arm is not None and right_arm is not None:
                arm_diff_ratio = abs(left_arm - right_arm) / (left_arm + 1e-6)
                if arm_diff_ratio > self.max_arm_asymmetry_ratio:
                    logger.debug(f"Ghost filter: Rejected detection (arm asymmetry: {arm_diff_ratio:.2f})")
                    continue
            
            # Check 4: Overlap với detections khác (NMS bổ sung)
            is_overlap = False
            for valid_det in valid_detections:
                valid_bbox = valid_det.get('bbox')
                if valid_bbox is None:
                    continue
                
                iou = self._calculate_iou(np.array(bbox), np.array(valid_bbox))
                if iou > self.nms_iou_threshold:
                    # Nếu overlap cao, giữ detection có score cao hơn
                    if det.get('score', 0.0) > valid_det.get('score', 0.0):
                        # Thay thế detection cũ bằng detection mới (score cao hơn)
                        valid_detections.remove(valid_det)
                        is_overlap = False  # Cho phép thêm detection mới
                        break
                    else:
                        is_overlap = True
                        break
            
            if not is_overlap:
                valid_detections.append(det)
        
        return valid_detections


class PostProcessingFilters:
    """
    Main class combining all post-processing filters
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize all filters
        
        Args:
            config: Configuration dictionary (optional)
        """
        if config is None:
            config = {}
        
        filter_config = config.get("post_processing_filters", {})
        
        self.spatial_filter = SpatialConsistencyFilter(
            min_height=filter_config.get("min_height", 50.0),
            max_height_ratio=filter_config.get("max_height_ratio", 0.9),
            min_aspect_ratio=filter_config.get("min_aspect_ratio", 0.3),
            max_aspect_ratio=filter_config.get("max_aspect_ratio", 0.7),
            edge_margin_ratio=filter_config.get("edge_margin_ratio", 0.1),
            enabled=filter_config.get("spatial_enabled", True)
        )
        
        self.geometric_filter = KeypointGeometricConsistencyFilter(
            min_torso_leg_ratio=filter_config.get("min_torso_leg_ratio", 0.4),
            max_torso_leg_ratio=filter_config.get("max_torso_leg_ratio", 0.6),
            max_head_shoulder_ratio=filter_config.get("max_head_shoulder_ratio", 0.3),
            min_symmetry_score=filter_config.get("min_symmetry_score", 0.7),
            min_confidence=filter_config.get("min_confidence", 0.3),
            enabled=filter_config.get("geometric_enabled", True)
        )
        
        self.velocity_filter = VelocityBasedFilter(
            max_velocity=filter_config.get("max_velocity", 50.0),
            max_jump_distance=filter_config.get("max_jump_distance", 100.0),
            min_track_length=filter_config.get("min_track_length", 5),
            enabled=filter_config.get("velocity_enabled", True)
        )
        
        self.occlusion_detector = OcclusionDetector(
            occlusion_threshold=filter_config.get("occlusion_threshold", 0.5),
            interpolation_window=filter_config.get("interpolation_window", 5),
            enabled=filter_config.get("occlusion_enabled", True)
        )
        
        self.ghost_filter = GhostDetectionFilter(
            min_visible_keypoints=filter_config.get("min_visible_keypoints", 8),
            min_torso_length=filter_config.get("ghost_min_torso_length", 50.0),
            max_torso_length=filter_config.get("ghost_max_torso_length", 500.0),
            max_arm_asymmetry_ratio=filter_config.get("max_arm_asymmetry_ratio", 0.3),
            nms_iou_threshold=filter_config.get("ghost_nms_iou_threshold", 0.5),
            min_confidence=filter_config.get("ghost_min_confidence", 0.5),
            enabled=filter_config.get("ghost_enabled", True)
        )
    
    def filter_detections(
        self,
        detections: List[Dict],
        frame_shape: Tuple[int, int]
    ) -> List[Dict]:
        """
        Apply all filters to detections
        
        Args:
            detections: List of detection dictionaries
            frame_shape: (height, width) of frame
        
        Returns:
            Filtered detections
        """
        # Apply spatial filter first (fastest)
        filtered = self.spatial_filter.filter(detections, frame_shape)
        
        # Apply geometric filter
        filtered = self.geometric_filter.filter(filtered)
        
        return filtered
    
    def filter_tracks(
        self,
        tracks: List,
        frame_id: int
    ) -> List:
        """
        Apply velocity filter to tracks
        
        Args:
            tracks: List of track objects
            frame_id: Current frame number
        
        Returns:
            Filtered tracks
        """
        return self.velocity_filter.filter_tracks(tracks, frame_id)
    
    def detect_occlusion(self, keypoints: np.ndarray) -> Tuple[bool, float]:
        """Detect occlusion for keypoints"""
        return self.occlusion_detector.detect_occlusion(keypoints)
    
    def interpolate_keypoints(
        self,
        keypoints_history: List[np.ndarray],
        current_keypoints: np.ndarray
    ) -> np.ndarray:
        """Interpolate missing keypoints"""
        return self.occlusion_detector.interpolate_keypoints(
            keypoints_history,
            current_keypoints
        )

