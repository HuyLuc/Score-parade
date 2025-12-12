"""
Person re-identification service for maintaining consistent IDs after occlusion
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from backend.app.config import ERROR_RECOVERY_CONFIG


class PersonReIdentifier:
    """
    Re-identify persons after they disappear and reappear in the video.
    Uses pose similarity and spatial proximity to match disappeared persons with new detections.
    """
    
    def __init__(
        self,
        similarity_threshold: float = None,
        max_disappeared_frames: int = None,
        spatial_weight: float = None,
        pose_weight: float = None
    ):
        """
        Initialize person re-identifier
        
        Args:
            similarity_threshold: Minimum similarity score for re-identification (0-1)
            max_disappeared_frames: Maximum frames before giving up on re-identification
            spatial_weight: Weight for spatial proximity (0-1)
            pose_weight: Weight for pose similarity (0-1)
        """
        # Use config defaults if not provided
        self.similarity_threshold = similarity_threshold or ERROR_RECOVERY_CONFIG["reid_similarity_threshold"]
        self.max_disappeared_frames = max_disappeared_frames or ERROR_RECOVERY_CONFIG["max_disappeared_frames"]
        self.spatial_weight = spatial_weight or ERROR_RECOVERY_CONFIG["spatial_distance_weight"]
        self.pose_weight = pose_weight or ERROR_RECOVERY_CONFIG["pose_similarity_weight"]
        
        # Tracking state
        self.disappeared_persons = {}  # {person_id: {"keypoints": np.ndarray, "position": (x, y), "frames_gone": int}}
    
    def register_disappeared(self, person_id: int, keypoints: np.ndarray):
        """
        Register a person as disappeared
        
        Args:
            person_id: Person ID that disappeared
            keypoints: Last known keypoints [17, 3]
        """
        # Calculate center position
        valid_mask = keypoints[:, 2] > 0
        if np.any(valid_mask):
            valid_points = keypoints[valid_mask, :2]
            center_x = np.mean(valid_points[:, 0])
            center_y = np.mean(valid_points[:, 1])
        else:
            center_x, center_y = 0, 0
        
        self.disappeared_persons[person_id] = {
            "keypoints": keypoints.copy(),
            "position": (center_x, center_y),
            "frames_gone": 0
        }
    
    def update_disappeared(self):
        """Update disappeared counter and remove expired persons"""
        expired_ids = []
        
        for person_id in self.disappeared_persons:
            self.disappeared_persons[person_id]["frames_gone"] += 1
            
            # Remove if disappeared too long
            if self.disappeared_persons[person_id]["frames_gone"] > self.max_disappeared_frames:
                expired_ids.append(person_id)
        
        for person_id in expired_ids:
            del self.disappeared_persons[person_id]
    
    def attempt_reidentification(
        self,
        new_detections: List[np.ndarray]
    ) -> Dict[int, Tuple[np.ndarray, float]]:
        """
        Attempt to re-identify disappeared persons from new detections
        
        Args:
            new_detections: List of new detection keypoints [17, 3]
            
        Returns:
            Dict mapping person_id to (keypoints, confidence_score) for re-identified persons
        """
        if len(self.disappeared_persons) == 0 or len(new_detections) == 0:
            return {}
        
        reidentified = {}
        used_detections = set()
        
        # For each disappeared person, try to find best match
        for person_id, person_data in list(self.disappeared_persons.items()):
            best_detection_idx = None
            best_score = -1.0
            
            for det_idx, det_keypoints in enumerate(new_detections):
                if det_idx in used_detections:
                    continue
                
                # Calculate combined similarity score
                score = self._calculate_reidentification_score(
                    person_data["keypoints"],
                    person_data["position"],
                    det_keypoints
                )
                
                if score > best_score:
                    best_score = score
                    best_detection_idx = det_idx
            
            # Re-identify if score is above threshold
            if best_score >= self.similarity_threshold and best_detection_idx is not None:
                reidentified[person_id] = (new_detections[best_detection_idx], best_score)
                used_detections.add(best_detection_idx)
                
                # Remove from disappeared list
                del self.disappeared_persons[person_id]
        
        return reidentified
    
    def _calculate_reidentification_score(
        self,
        old_keypoints: np.ndarray,
        old_position: Tuple[float, float],
        new_keypoints: np.ndarray
    ) -> float:
        """
        Calculate re-identification score combining pose similarity and spatial proximity
        
        Args:
            old_keypoints: Previous keypoints [17, 3]
            old_position: Previous center position (x, y)
            new_keypoints: New detection keypoints [17, 3]
            
        Returns:
            Combined score between 0 and 1
        """
        # Calculate pose similarity
        pose_sim = self._calculate_pose_similarity(old_keypoints, new_keypoints)
        
        # Calculate spatial proximity
        spatial_sim = self._calculate_spatial_similarity(old_position, new_keypoints)
        
        # Weighted combination
        combined_score = (self.pose_weight * pose_sim) + (self.spatial_weight * spatial_sim)
        
        return combined_score
    
    def _calculate_pose_similarity(
        self,
        keypoints1: np.ndarray,
        keypoints2: np.ndarray
    ) -> float:
        """
        Calculate pose similarity using normalized L2 distance
        
        Args:
            keypoints1: First pose keypoints [17, 3]
            keypoints2: Second pose keypoints [17, 3]
            
        Returns:
            Similarity score between 0 and 1
        """
        # Extract valid keypoints from both poses
        valid_mask1 = keypoints1[:, 2] > 0
        valid_mask2 = keypoints2[:, 2] > 0
        common_mask = valid_mask1 & valid_mask2
        
        if not np.any(common_mask):
            return 0.0
        
        # Use only x, y coordinates
        points1 = keypoints1[common_mask, :2]
        points2 = keypoints2[common_mask, :2]
        
        # Normalize poses (center and scale)
        mean1 = np.mean(points1, axis=0)
        mean2 = np.mean(points2, axis=0)
        
        points1_centered = points1 - mean1
        points2_centered = points2 - mean2
        
        # Scale to unit variance
        scale1 = np.std(points1_centered) + 1e-8
        scale2 = np.std(points2_centered) + 1e-8
        
        points1_normalized = points1_centered / scale1
        points2_normalized = points2_centered / scale2
        
        # Calculate normalized L2 distance
        distance = np.linalg.norm(points1_normalized - points2_normalized)
        max_distance = np.sqrt(2 * len(points1_normalized))
        
        # Convert to similarity
        similarity = 1.0 - min(distance / max_distance, 1.0)
        
        return similarity
    
    def _calculate_spatial_similarity(
        self,
        old_position: Tuple[float, float],
        new_keypoints: np.ndarray
    ) -> float:
        """
        Calculate spatial proximity similarity
        
        Args:
            old_position: Previous center position (x, y)
            new_keypoints: New detection keypoints [17, 3]
            
        Returns:
            Spatial similarity score between 0 and 1
        """
        # Calculate new center position
        valid_mask = new_keypoints[:, 2] > 0
        if not np.any(valid_mask):
            return 0.0
        
        valid_points = new_keypoints[valid_mask, :2]
        new_center_x = np.mean(valid_points[:, 0])
        new_center_y = np.mean(valid_points[:, 1])
        
        # Calculate Euclidean distance
        distance = np.sqrt(
            (old_position[0] - new_center_x) ** 2 +
            (old_position[1] - new_center_y) ** 2
        )
        
        # Normalize by typical frame size (assume 1920x1080)
        # Maximum reasonable distance is about 1/4 of frame diagonal
        max_distance = np.sqrt(1920**2 + 1080**2) / 4
        
        # Convert distance to similarity
        similarity = max(0.0, 1.0 - (distance / max_distance))
        
        return similarity
    
    def get_disappeared_count(self) -> int:
        """Get number of disappeared persons being tracked"""
        return len(self.disappeared_persons)
    
    def reset(self):
        """Reset re-identifier state"""
        self.disappeared_persons = {}
