"""
Temporal smoothing service for noise reduction in pose estimation

Reduces noise from keypoint jitter and temporary occlusions by smoothing
values across multiple frames using moving average or median filters.
"""
from collections import deque
from typing import Optional, Literal, Tuple
import numpy as np


class TemporalSmoother:
    """
    Smooth scalar metrics (angles, heights) across frames using moving average or median
    
    Example:
        smoother = TemporalSmoother(window_size=5, method="moving_average")
        smoother.add_value(45.0)
        smoother.add_value(65.0)  # noise spike
        smoother.add_value(47.0)
        smoothed = smoother.get_smoothed_value()  # Returns ~52.3 instead of 65.0
    """
    
    def __init__(
        self,
        window_size: int = 5,
        method: Literal["moving_average", "median"] = "moving_average"
    ):
        """
        Initialize temporal smoother
        
        Args:
            window_size: Number of frames to smooth over (default: 5)
            method: Smoothing method - "moving_average" or "median"
        """
        self.window_size = window_size
        self.method = method
        self.values = deque(maxlen=window_size)
    
    def add_value(self, value: Optional[float]) -> None:
        """
        Add a new value to the smoothing window
        
        Args:
            value: Scalar value to add (e.g., angle in degrees)
        """
        if value is not None:
            self.values.append(value)
    
    def get_smoothed_value(self) -> Optional[float]:
        """
        Get the smoothed value using the configured method
        
        Returns:
            Smoothed value, or None if no values have been added
        """
        if len(self.values) == 0:
            return None
        
        if self.method == "moving_average":
            return float(np.mean(self.values))
        elif self.method == "median":
            return float(np.median(self.values))
        else:
            # Default to moving average
            return float(np.mean(self.values))
    
    def reset(self) -> None:
        """Clear all stored values"""
        self.values.clear()
    
    def is_ready(self) -> bool:
        """
        Check if the smoother has enough values for full smoothing
        
        Returns:
            True if window is full, False otherwise
        """
        return len(self.values) >= self.window_size


class KeypointSmoother:
    """
    Smooth keypoint (x, y) coordinates across frames to reduce jitter
    
    Example:
        smoother = KeypointSmoother(window_size=5, num_keypoints=17)
        smoother.add_keypoints(keypoints)  # shape (17, 3) with x, y, confidence
        smoothed = smoother.get_smoothed_keypoints()  # Smoothed coordinates
    """
    
    def __init__(
        self,
        window_size: int = 5,
        num_keypoints: int = 17,
        method: Literal["moving_average", "median"] = "moving_average"
    ):
        """
        Initialize keypoint smoother
        
        Args:
            window_size: Number of frames to smooth over
            num_keypoints: Number of keypoints (default: 17 for COCO format)
            method: Smoothing method - "moving_average" or "median"
        """
        self.window_size = window_size
        self.num_keypoints = num_keypoints
        self.method = method
        # Store keypoints for each frame, shape: (window_size, num_keypoints, 3)
        self.keypoints_buffer = deque(maxlen=window_size)
    
    def add_keypoints(self, keypoints: np.ndarray) -> None:
        """
        Add keypoints from a new frame
        
        Args:
            keypoints: Keypoints array of shape (num_keypoints, 3) with [x, y, confidence]
        """
        if keypoints is None or keypoints.shape[0] < self.num_keypoints:
            return
        
        # Store a copy to avoid mutations
        self.keypoints_buffer.append(keypoints.copy())
    
    def get_smoothed_keypoints(self) -> Optional[np.ndarray]:
        """
        Get smoothed keypoints by averaging/medianing x, y coordinates across frames
        
        Confidence values are taken from the most recent frame (not smoothed)
        
        Returns:
            Smoothed keypoints array of shape (num_keypoints, 3), or None if empty
        """
        if len(self.keypoints_buffer) == 0:
            return None
        
        # Stack keypoints from all frames: (num_frames, num_keypoints, 3)
        stacked = np.stack(list(self.keypoints_buffer), axis=0)
        
        # Extract x, y, confidence
        xs = stacked[:, :, 0]  # (num_frames, num_keypoints)
        ys = stacked[:, :, 1]
        confidences = stacked[-1, :, 2]  # Use most recent confidence
        
        # Smooth x and y coordinates
        if self.method == "moving_average":
            smoothed_x = np.mean(xs, axis=0)
            smoothed_y = np.mean(ys, axis=0)
        elif self.method == "median":
            smoothed_x = np.median(xs, axis=0)
            smoothed_y = np.median(ys, axis=0)
        else:
            # Default to moving average
            smoothed_x = np.mean(xs, axis=0)
            smoothed_y = np.mean(ys, axis=0)
        
        # Combine smoothed x, y with original confidence
        smoothed_keypoints = np.stack([smoothed_x, smoothed_y, confidences], axis=1)
        
        return smoothed_keypoints
    
    def reset(self) -> None:
        """Clear all stored keypoints"""
        self.keypoints_buffer.clear()
    
    def is_ready(self) -> bool:
        """
        Check if the smoother has enough frames for full smoothing
        
        Returns:
            True if window is full, False otherwise
        """
        return len(self.keypoints_buffer) >= self.window_size
