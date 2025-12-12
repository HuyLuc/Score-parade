"""
Multi-person tracking and matching service for pose estimation
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy.optimize import linear_sum_assignment
from sklearn.metrics.pairwise import cosine_similarity

# Constants for numerical stability and bbox calculations
MIN_BBOX_SIZE = 1.0  # Minimum bounding box size to handle degenerate cases
EPSILON = 1e-8  # Small value for numerical stability in divisions


class PersonTracker:
    """Track multiple persons across frames using IoU-based matching with optional re-identification"""
    
    def __init__(self, max_disappeared: int = 30, iou_threshold: float = 0.5, enable_reid: bool = False):
        """
        Initialize person tracker
        
        Args:
            max_disappeared: Maximum frames a person can be missing before deregistration
            iou_threshold: Minimum IoU for matching detections to existing tracks
            enable_reid: Enable person re-identification after occlusion
        """
        self.max_disappeared = max_disappeared
        self.iou_threshold = iou_threshold
        self.enable_reid = enable_reid
        
        # Tracking state
        self.next_person_id = 0
        self.persons = {}  # {person_id: {"keypoints": np.ndarray, "frame_num": int}}
        self.disappeared = {}  # {person_id: disappeared_count}
        
        # Re-identification support
        self.reidentifier = None
        if enable_reid:
            from backend.app.services.person_reidentification import PersonReIdentifier
            self.reidentifier = PersonReIdentifier()
    
    def register(self, keypoints: np.ndarray, frame_num: int) -> int:
        """
        Register a new person
        
        Args:
            keypoints: Keypoints array [17, 3]
            frame_num: Current frame number
            
        Returns:
            person_id: Newly assigned person ID
        """
        person_id = self.next_person_id
        self.persons[person_id] = {
            "keypoints": keypoints,
            "frame_num": frame_num
        }
        self.disappeared[person_id] = 0
        self.next_person_id += 1
        return person_id
    
    def deregister(self, person_id: int):
        """Remove a person from tracking"""
        if person_id in self.persons:
            del self.persons[person_id]
        if person_id in self.disappeared:
            del self.disappeared[person_id]
    
    def update(self, detections: List[np.ndarray], frame_num: int) -> Dict[int, np.ndarray]:
        """
        Update tracker with new detections (with optional re-identification)
        
        Args:
            detections: List of keypoints arrays, each [17, 3]
            frame_num: Current frame number
            
        Returns:
            Dict mapping person_id to keypoints for this frame
        """
        # If no existing persons, register all detections as new
        if len(self.persons) == 0:
            for keypoints in detections:
                self.register(keypoints, frame_num)
            return {pid: data["keypoints"] for pid, data in self.persons.items()}
        
        # If no new detections, increment disappeared counter
        if len(detections) == 0:
            for person_id in list(self.persons.keys()):
                self.disappeared[person_id] += 1
                
                # Register for re-identification if enabled
                if self.enable_reid and self.reidentifier and self.disappeared[person_id] == 1:
                    self.reidentifier.register_disappeared(person_id, self.persons[person_id]["keypoints"])
                
                if self.disappeared[person_id] > self.max_disappeared:
                    self.deregister(person_id)
            
            # Update re-identifier
            if self.enable_reid and self.reidentifier:
                self.reidentifier.update_disappeared()
            
            return {}
        
        # Attempt re-identification first if enabled
        unmatched_detections = list(range(len(detections)))
        if self.enable_reid and self.reidentifier:
            reidentified = self.reidentifier.attempt_reidentification(detections)
            
            for person_id, (keypoints, confidence) in reidentified.items():
                # Find which detection was used
                det_idx = next((i for i, det in enumerate(detections) if np.array_equal(det, keypoints)), None)
                if det_idx is not None and det_idx in unmatched_detections:
                    # Re-register the person with same ID
                    self.persons[person_id] = {
                        "keypoints": keypoints,
                        "frame_num": frame_num
                    }
                    self.disappeared[person_id] = 0
                    unmatched_detections.remove(det_idx)
        
        # Match remaining detections to existing persons using Hungarian algorithm
        person_ids = list(self.persons.keys())
        remaining_detections = [detections[i] for i in unmatched_detections]
        
        if len(person_ids) > 0 and len(remaining_detections) > 0:
            cost_matrix = self._compute_cost_matrix(remaining_detections, person_ids)
            
            # Solve assignment problem
            row_indices, col_indices = linear_sum_assignment(cost_matrix)
            
            # Track which persons and detections are matched
            matched_persons = set()
            matched_detections = set()
            
            # Update matched persons
            for row_idx, col_idx in zip(row_indices, col_indices):
                # Check if IoU is above threshold
                iou = 1.0 - cost_matrix[row_idx, col_idx]  # Convert cost back to IoU
                if iou >= self.iou_threshold:
                    person_id = person_ids[col_idx]
                    det_idx = unmatched_detections[row_idx]
                    self.persons[person_id]["keypoints"] = detections[det_idx]
                    self.persons[person_id]["frame_num"] = frame_num
                    self.disappeared[person_id] = 0
                    matched_persons.add(person_id)
                    matched_detections.add(det_idx)
            
            # Handle unmatched persons (increment disappeared counter)
            for person_id in person_ids:
                if person_id not in matched_persons:
                    self.disappeared[person_id] += 1
                    
                    # Register for re-identification if enabled
                    if self.enable_reid and self.reidentifier and self.disappeared[person_id] == 1:
                        self.reidentifier.register_disappeared(person_id, self.persons[person_id]["keypoints"])
                    
                    if self.disappeared[person_id] > self.max_disappeared:
                        self.deregister(person_id)
            
            # Register unmatched detections as new persons
            for det_idx in unmatched_detections:
                if det_idx not in matched_detections:
                    self.register(detections[det_idx], frame_num)
        else:
            # No persons to match, all detections are new
            for det_idx in unmatched_detections:
                self.register(detections[det_idx], frame_num)
        
        # Update re-identifier
        if self.enable_reid and self.reidentifier:
            self.reidentifier.update_disappeared()
        
        # Return current tracked persons
        return {pid: data["keypoints"] for pid, data in self.persons.items()}
    
    def _compute_cost_matrix(self, detections: List[np.ndarray], person_ids: List[int]) -> np.ndarray:
        """
        Compute cost matrix for Hungarian algorithm using IoU
        
        Args:
            detections: List of detection keypoints
            person_ids: List of existing person IDs
            
        Returns:
            Cost matrix [n_detections, n_persons] where cost = 1 - IoU
        """
        n_detections = len(detections)
        n_persons = len(person_ids)
        cost_matrix = np.ones((n_detections, n_persons))
        
        for i, det_keypoints in enumerate(detections):
            det_bbox = self._get_bbox(det_keypoints)
            for j, person_id in enumerate(person_ids):
                person_keypoints = self.persons[person_id]["keypoints"]
                person_bbox = self._get_bbox(person_keypoints)
                iou = self._calculate_iou(det_bbox, person_bbox)
                cost_matrix[i, j] = 1.0 - iou  # Convert IoU to cost
        
        return cost_matrix
    
    def _get_bbox(self, keypoints: np.ndarray) -> Tuple[float, float, float, float]:
        """
        Get bounding box from keypoints
        
        Args:
            keypoints: Keypoints array [17, 3]
            
        Returns:
            Tuple (x1, y1, x2, y2) representing bounding box
        """
        # Filter valid keypoints (confidence > 0)
        valid_mask = keypoints[:, 2] > 0
        if not np.any(valid_mask):
            return (0, 0, 0, 0)
        
        valid_points = keypoints[valid_mask, :2]
        x1, y1 = valid_points.min(axis=0)
        x2, y2 = valid_points.max(axis=0)
        
        # Add small padding to handle degenerate cases where all points are at same location
        # This ensures bbox has some area for IoU calculation
        if x2 - x1 < MIN_BBOX_SIZE:
            x2 = x1 + MIN_BBOX_SIZE
        if y2 - y1 < MIN_BBOX_SIZE:
            y2 = y1 + MIN_BBOX_SIZE
        
        return (x1, y1, x2, y2)
    
    def _calculate_iou(self, bbox1: Tuple[float, float, float, float], 
                       bbox2: Tuple[float, float, float, float]) -> float:
        """
        Calculate Intersection over Union (IoU) between two bounding boxes
        
        Args:
            bbox1: First bounding box (x1, y1, x2, y2)
            bbox2: Second bounding box (x1, y1, x2, y2)
            
        Returns:
            IoU value between 0 and 1
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection area
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union area
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        if union <= 0:
            return 0.0
        
        return intersection / union
    
    def reset(self):
        """Reset tracker state"""
        self.next_person_id = 0
        self.persons = {}
        self.disappeared = {}
        
        # Reset re-identifier if enabled
        if self.enable_reid and self.reidentifier:
            self.reidentifier.reset()


class MultiPersonManager:
    """Manage multiple golden templates and match test persons to them"""
    
    def __init__(self, similarity_threshold: float = 0.6):
        """
        Initialize multi-person manager
        
        Args:
            similarity_threshold: Minimum pose similarity for matching
        """
        self.similarity_threshold = similarity_threshold
        self.golden_templates = {}  # {template_id: {"keypoints": np.ndarray, "profile": dict}}
        self.matches = {}  # {test_person_id: template_id}
    
    def add_golden_template(self, template_id: str, keypoints: np.ndarray, profile: Optional[Dict] = None):
        """
        Add a golden template
        
        Args:
            template_id: Unique identifier for template
            keypoints: Golden keypoints sequence [n_frames, 17, 3] or average [17, 3]
            profile: Optional profile information (statistics, etc.)
        """
        self.golden_templates[template_id] = {
            "keypoints": keypoints,
            "profile": profile or {}
        }
    
    def match_test_to_golden(self, test_persons: Dict[int, np.ndarray]) -> Dict[int, str]:
        """
        Match test persons to golden templates based on pose similarity
        
        Args:
            test_persons: Dict mapping test_person_id to keypoints [17, 3]
            
        Returns:
            Dict mapping test_person_id to best matching template_id
        """
        if len(self.golden_templates) == 0:
            return {}
        
        matches = {}
        
        # For each test person, find best matching template
        for test_id, test_keypoints in test_persons.items():
            best_template = None
            best_similarity = -1.0
            
            for template_id, template_data in self.golden_templates.items():
                template_keypoints = template_data["keypoints"]
                
                # If template has multiple frames, use average
                if template_keypoints.ndim == 3:
                    template_keypoints = np.mean(template_keypoints, axis=0)
                
                similarity = self._calculate_similarity(test_keypoints, template_keypoints)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_template = template_id
            
            # Only match if similarity is above threshold
            if best_similarity >= self.similarity_threshold:
                matches[test_id] = best_template
        
        self.matches = matches
        return matches
    
    def _calculate_similarity(self, keypoints1: np.ndarray, keypoints2: np.ndarray) -> float:
        """
        Calculate pose similarity using normalized L2 distance
        
        Args:
            keypoints1: First pose keypoints [17, 3]
            keypoints2: Second pose keypoints [17, 3]
            
        Returns:
            Similarity score between 0 and 1
        """
        # Extract valid keypoints (confidence > 0) from both poses
        valid_mask1 = keypoints1[:, 2] > 0
        valid_mask2 = keypoints2[:, 2] > 0
        common_mask = valid_mask1 & valid_mask2
        
        if not np.any(common_mask):
            return 0.0
        
        # Use only x, y coordinates (ignore confidence)
        points1 = keypoints1[common_mask, :2]
        points2 = keypoints2[common_mask, :2]
        
        # Normalize poses to unit scale (center at origin and scale)
        mean1 = np.mean(points1, axis=0)
        mean2 = np.mean(points2, axis=0)
        
        points1_centered = points1 - mean1
        points2_centered = points2 - mean2
        
        # Scale to unit variance (add EPSILON for numerical stability)
        scale1 = np.std(points1_centered) + EPSILON
        scale2 = np.std(points2_centered) + EPSILON
        
        points1_normalized = points1_centered / scale1
        points2_normalized = points2_centered / scale2
        
        # Calculate normalized L2 distance
        distance = np.linalg.norm(points1_normalized - points2_normalized)
        max_distance = np.sqrt(2 * len(points1_normalized))  # Maximum possible distance
        
        # Convert distance to similarity (0 = identical, higher = more different)
        similarity = 1.0 - min(distance / max_distance, 1.0)
        
        return similarity
    
    def get_template_for_person(self, test_person_id: int) -> Optional[str]:
        """Get matched template ID for a test person"""
        return self.matches.get(test_person_id)
    
    def get_template_data(self, template_id: str) -> Optional[Dict]:
        """Get template data by ID"""
        return self.golden_templates.get(template_id)
    
    def reset_matches(self):
        """Reset person-to-template matches"""
        self.matches = {}
    
    def reset_all(self):
        """Reset all templates and matches"""
        self.golden_templates = {}
        self.matches = {}
