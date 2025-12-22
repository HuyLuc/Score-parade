"""
Temporal smoothing service for noise reduction in pose estimation

Reduces noise from keypoint jitter and temporary occlusions by smoothing
values across multiple frames using various methods:
- moving_average: Simple mean
- median: Robust to outliers
- gaussian: Weighted average with Gaussian kernel
- savitzky_golay: Polynomial smoothing (best for preserving features)
"""
from collections import deque
from typing import Optional, Literal, Tuple
import numpy as np
from scipy import signal


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
        window_size: int = 7,
        method: Literal["moving_average", "median", "gaussian", "savitzky_golay"] = "moving_average"
    ):
        """
        Initialize temporal smoother
        
        Args:
            window_size: Number of frames to smooth over (default: 7)
            method: Smoothing method:
                - "moving_average": Simple mean (fast, basic)
                - "median": Robust to outliers (good for noisy data)
                - "gaussian": Weighted average with Gaussian kernel (smooth, preserves trends)
                - "savitzky_golay": Polynomial smoothing (best for preserving features)
        """
        self.window_size = window_size
        self.method = method
        self.values = deque(maxlen=window_size)
        
        # Pre-compute Gaussian weights if using gaussian method
        if method == "gaussian":
            self.gaussian_weights = self._compute_gaussian_weights(window_size)
        else:
            self.gaussian_weights = None
    
    def add_value(self, value: Optional[float]) -> None:
        """
        Add a new value to the smoothing window
        
        Args:
            value: Scalar value to add (e.g., angle in degrees)
        
        Note:
            Non-finite values (inf, -inf, NaN) are ignored to prevent
            corrupting smoothing calculations.
        """
        if value is not None and np.isfinite(value):
            self.values.append(value)
    
    def _compute_gaussian_weights(self, size: int, sigma: Optional[float] = None) -> np.ndarray:
        """
        Compute Gaussian weights for smoothing
        
        Args:
            size: Window size
            sigma: Standard deviation (if None, auto-calculate as size/3)
        
        Returns:
            Normalized Gaussian weights array
        """
        if sigma is None:
            sigma = max(1.0, size / 3.0)
        
        x = np.arange(size)
        center = (size - 1) / 2.0
        weights = np.exp(-0.5 * ((x - center) / sigma) ** 2)
        weights = weights / weights.sum()  # Normalize
        
        return weights
    
    def get_smoothed_value(self) -> Optional[float]:
        """
        Get the smoothed value using the configured method
        
        Returns:
            Smoothed value, or None if no values have been added
        """
        if len(self.values) == 0:
            return None
        
        values_array = np.array(list(self.values))
        
        if self.method == "moving_average":
            return float(np.mean(values_array))
        elif self.method == "median":
            return float(np.median(values_array))
        elif self.method == "gaussian":
            # Weighted average with Gaussian kernel
            if len(values_array) < self.window_size:
                # If window not full, use available weights
                weights = self._compute_gaussian_weights(len(values_array))
            else:
                weights = self.gaussian_weights
            return float(np.average(values_array, weights=weights))
        elif self.method == "savitzky_golay":
            # Savitzky-Golay filter (polynomial smoothing)
            if len(values_array) < 3:
                # Need at least 3 points for SG filter
                return float(np.mean(values_array))
            try:
                # Use polynomial order 2, window length = min(window_size, len(values))
                window_length = min(self.window_size, len(values_array))
                if window_length % 2 == 0:
                    window_length -= 1  # Must be odd
                if window_length < 3:
                    window_length = 3
                polyorder = min(2, window_length - 1)  # Order must be < window_length
                smoothed = signal.savgol_filter(values_array, window_length, polyorder)
                return float(smoothed[-1])  # Return most recent smoothed value
            except (ValueError, np.linalg.LinAlgError):
                # Fallback to moving average if SG filter fails
                return float(np.mean(values_array))
        else:
            # Default to moving average
            return float(np.mean(values_array))
    
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
        window_size: int = 7,
        num_keypoints: int = 17,
        method: Literal["moving_average", "median", "gaussian", "savitzky_golay"] = "moving_average"
    ):
        """
        Initialize keypoint smoother
        
        Args:
            window_size: Number of frames to smooth over (default: 7)
            num_keypoints: Number of keypoints (default: 17 for COCO format)
            method: Smoothing method:
                - "moving_average": Simple mean (fast, basic)
                - "median": Robust to outliers (good for noisy data)
                - "gaussian": Weighted average with Gaussian kernel (smooth, preserves trends)
                - "savitzky_golay": Polynomial smoothing (best for preserving features)
        """
        self.window_size = window_size
        self.num_keypoints = num_keypoints
        self.method = method
        # Store keypoints for each frame, shape: (window_size, num_keypoints, 3)
        self.keypoints_buffer = deque(maxlen=window_size)
        
        # Pre-compute Gaussian weights if using gaussian method
        if method == "gaussian":
            self.gaussian_weights = self._compute_gaussian_weights(window_size)
        else:
            self.gaussian_weights = None
    
    def _compute_gaussian_weights(self, size: int, sigma: Optional[float] = None) -> np.ndarray:
        """
        Compute Gaussian weights for smoothing
        
        Args:
            size: Window size
            sigma: Standard deviation (if None, auto-calculate as size/3)
        
        Returns:
            Normalized Gaussian weights array
        """
        if sigma is None:
            sigma = max(1.0, size / 3.0)
        
        x = np.arange(size)
        center = (size - 1) / 2.0
        weights = np.exp(-0.5 * ((x - center) / sigma) ** 2)
        weights = weights / weights.sum()  # Normalize
        
        return weights
    
    def add_keypoints(self, keypoints: np.ndarray) -> None:
        """
        Add keypoints from a new frame
        
        Args:
            keypoints: Keypoints array of shape (num_keypoints, 3) with [x, y, confidence]
        """
        if (keypoints is None or 
            keypoints.shape[0] != self.num_keypoints or 
            len(keypoints.shape) < 2 or 
            keypoints.shape[1] < 3):
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
        num_frames = xs.shape[0]
        
        if self.method == "moving_average":
            smoothed_x = np.mean(xs, axis=0)
            smoothed_y = np.mean(ys, axis=0)
        elif self.method == "median":
            smoothed_x = np.median(xs, axis=0)
            smoothed_y = np.median(ys, axis=0)
        elif self.method == "gaussian":
            # Weighted average with Gaussian kernel
            if num_frames < self.window_size:
                # If window not full, use available weights
                weights = self._compute_gaussian_weights(num_frames)
            else:
                weights = self.gaussian_weights
            
            # Apply weights along time axis (axis=0)
            smoothed_x = np.average(xs, axis=0, weights=weights)
            smoothed_y = np.average(ys, axis=0, weights=weights)
        elif self.method == "savitzky_golay":
            # Savitzky-Golay filter (polynomial smoothing)
            if num_frames < 3:
                # Need at least 3 points for SG filter
                smoothed_x = np.mean(xs, axis=0)
                smoothed_y = np.mean(ys, axis=0)
            else:
                try:
                    # Use polynomial order 2, window length = min(window_size, num_frames)
                    window_length = min(self.window_size, num_frames)
                    if window_length % 2 == 0:
                        window_length -= 1  # Must be odd
                    if window_length < 3:
                        window_length = 3
                    polyorder = min(2, window_length - 1)  # Order must be < window_length
                    
                    # Apply SG filter to each keypoint independently
                    smoothed_x = np.zeros(self.num_keypoints)
                    smoothed_y = np.zeros(self.num_keypoints)
                    for kp_idx in range(self.num_keypoints):
                        smoothed_x[kp_idx] = signal.savgol_filter(xs[:, kp_idx], window_length, polyorder)[-1]
                        smoothed_y[kp_idx] = signal.savgol_filter(ys[:, kp_idx], window_length, polyorder)[-1]
                except (ValueError, np.linalg.LinAlgError):
                    # Fallback to moving average if SG filter fails
                    smoothed_x = np.mean(xs, axis=0)
                    smoothed_y = np.mean(ys, axis=0)
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
