"""
Pose estimation service - Wrapper cho PoseEstimator
"""
from typing import List, Dict
import numpy as np
from backend.app.services.pose_estimation import PoseEstimator


class PoseService:
    """Service cho pose estimation"""
    
    def __init__(self, model_type: str = None):
        self.estimator = PoseEstimator(model_type)
    
    def predict(self, frame):
        """Dự đoán pose từ frame"""
        return self.estimator.predict(frame)
    
    def predict_batch(self, frames):
        """Dự đoán pose từ nhiều frames"""
        return self.estimator.predict_batch(frames)
    
    def predict_multi_person(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect all persons in frame with additional metadata
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            List of detections, each containing:
            {
                "keypoints": np.ndarray [17, 3],
                "confidence": float,
                "bbox": tuple (x1, y1, x2, y2)
            }
        """
        keypoints_list = self.estimator.predict(frame)
        
        detections = []
        for keypoints in keypoints_list:
            # Calculate average confidence
            valid_mask = keypoints[:, 2] > 0
            avg_confidence = np.mean(keypoints[valid_mask, 2]) if np.any(valid_mask) else 0.0
            
            # Calculate bounding box
            if np.any(valid_mask):
                valid_points = keypoints[valid_mask, :2]
                x1, y1 = valid_points.min(axis=0)
                x2, y2 = valid_points.max(axis=0)
                bbox = (float(x1), float(y1), float(x2), float(y2))
            else:
                bbox = (0.0, 0.0, 0.0, 0.0)
            
            detections.append({
                "keypoints": keypoints,
                "confidence": float(avg_confidence),
                "bbox": bbox
            })
        
        return detections
    
    def predict_batch_multi_person(self, frames: List[np.ndarray], batch_size: int = None) -> List[List[Dict]]:
        """
        Batch process multiple frames with GPU acceleration for multi-person detection
        
        Args:
            frames: List of input frames
            batch_size: Number of frames to process at once
            
        Returns:
            List of frame results, each containing list of person detections
        """
        batch_keypoints = self.estimator.predict_batch(frames, batch_size)
        
        all_detections = []
        for keypoints_list in batch_keypoints:
            frame_detections = []
            for keypoints in keypoints_list:
                # Calculate average confidence
                valid_mask = keypoints[:, 2] > 0
                avg_confidence = np.mean(keypoints[valid_mask, 2]) if np.any(valid_mask) else 0.0
                
                # Calculate bounding box
                if np.any(valid_mask):
                    valid_points = keypoints[valid_mask, :2]
                    x1, y1 = valid_points.min(axis=0)
                    x2, y2 = valid_points.max(axis=0)
                    bbox = (float(x1), float(y1), float(x2), float(y2))
                else:
                    bbox = (0.0, 0.0, 0.0, 0.0)
                
                frame_detections.append({
                    "keypoints": keypoints,
                    "confidence": float(avg_confidence),
                    "bbox": bbox
                })
            
            all_detections.append(frame_detections)
        
        return all_detections

