"""
Adaptive Kalman Filter for Multi-Person Tracking
Cải thiện Kalman Filter với:
1. Keypoint prediction (không chỉ bbox)
2. Adaptive noise adjustment dựa trên motion
3. Tuned process/measurement noise
"""
import numpy as np
from typing import Optional, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)


class AdaptiveKalmanFilter:
    """
    Adaptive Kalman Filter với keypoint prediction
    
    Features:
    - Predict cả bbox và keypoints
    - Tự điều chỉnh process noise dựa trên motion characteristics
    - Tuned noise parameters cho tracking tốt hơn
    """
    
    def __init__(
        self,
        adaptive_enabled: bool = True,
        base_process_noise: float = 0.1,
        base_measurement_noise: float = 1.0,
        motion_history_size: int = 10,
        keypoint_prediction_enabled: bool = True
    ):
        """
        Args:
            adaptive_enabled: Enable adaptive noise adjustment
            base_process_noise: Base process noise (Q)
            base_measurement_noise: Base measurement noise (R)
            motion_history_size: Number of frames to keep for motion analysis
            keypoint_prediction_enabled: Enable keypoint prediction
        """
        self.adaptive_enabled = adaptive_enabled
        self.base_process_noise = base_process_noise
        self.base_measurement_noise = base_measurement_noise
        self.motion_history_size = motion_history_size
        self.keypoint_prediction_enabled = keypoint_prediction_enabled
        
        # State: [x, y, w, h, vx, vy, vw, vh] for bbox
        self.bbox_state = np.zeros(8)
        self.bbox_covariance = np.eye(8) * 10
        
        # Keypoint state: [17, 3] -> [17*3 = 51] (x, y, confidence for each keypoint)
        # Only track x, y (not confidence) -> [17*2 = 34]
        self.keypoint_state = None  # Will be initialized when first keypoints received
        self.keypoint_covariance = None
        self.num_keypoints = 17
        
        # Motion history for adaptive noise
        self.motion_history: deque = deque(maxlen=motion_history_size)
        self.velocity_history: deque = deque(maxlen=motion_history_size)
        
        # Transition matrices
        self._init_transition_matrices()
        
        # Current noise values (will be adapted)
        self.Q_bbox = np.eye(8) * base_process_noise
        self.R_bbox = np.eye(4) * base_measurement_noise
        
        if keypoint_prediction_enabled:
            self.Q_keypoint = None  # Will be initialized
            self.R_keypoint = None
    
    def _init_transition_matrices(self):
        """Initialize transition matrices for bbox and keypoints"""
        # Bbox transition matrix (constant velocity model)
        self.F_bbox = np.eye(8)
        for i in range(4):
            self.F_bbox[i, i+4] = 1
        
        # Bbox measurement matrix
        self.H_bbox = np.eye(4, 8)
        
        # Keypoint transition matrix (constant velocity model)
        # State: [x1, y1, x2, y2, ..., x17, y17, vx1, vy1, vx2, vy2, ..., vx17, vy17]
        # Total: 17 keypoints * 2 (x, y) + 17 keypoints * 2 (vx, vy) = 68 states
        if self.keypoint_prediction_enabled:
            self.F_keypoint = np.eye(68)
            for i in range(17):
                pos_idx = i * 2  # Position index
                vel_idx = 34 + i * 2  # Velocity index
                # Position += velocity
                self.F_keypoint[pos_idx, vel_idx] = 1  # x += vx
                self.F_keypoint[pos_idx + 1, vel_idx + 1] = 1  # y += vy
            
            # Keypoint measurement matrix (observe x, y positions only)
            self.H_keypoint = np.zeros((34, 68))
            for i in range(17):
                pos_idx = i * 2
                self.H_keypoint[pos_idx, pos_idx] = 1  # Observe x
                self.H_keypoint[pos_idx + 1, pos_idx + 1] = 1  # Observe y
    
    def initialize_keypoints(self, keypoints: np.ndarray):
        """Initialize keypoint state from first observation"""
        if not self.keypoint_prediction_enabled:
            return
        
        # Extract x, y from keypoints [17, 3]
        kp_xy = keypoints[:, :2].flatten()  # [34]
        kp_velocities = np.zeros(34)  # Initial velocities = 0
        
        self.keypoint_state = np.concatenate([kp_xy, kp_velocities])  # [68]
        self.keypoint_covariance = np.eye(68) * 10
        
        # Initialize noise matrices
        self.Q_keypoint = np.eye(68) * self.base_process_noise
        self.R_keypoint = np.eye(34) * self.base_measurement_noise
    
    def _calculate_motion_characteristics(self) -> Tuple[float, float]:
        """
        Calculate motion characteristics from history
        
        Returns:
            (average_velocity, velocity_variance)
        """
        if len(self.velocity_history) < 2:
            return 0.0, 0.0
        
        velocities = np.array(list(self.velocity_history))
        avg_velocity = np.mean(np.linalg.norm(velocities, axis=1))
        velocity_variance = np.var(np.linalg.norm(velocities, axis=1))
        
        return avg_velocity, velocity_variance
    
    def _adapt_noise(self):
        """Adapt process and measurement noise based on motion"""
        if not self.adaptive_enabled or len(self.velocity_history) < 3:
            return
        
        avg_velocity, velocity_variance = self._calculate_motion_characteristics()
        
        # High velocity -> higher process noise (more uncertainty)
        # High variance -> higher measurement noise (more jitter)
        velocity_factor = min(avg_velocity / 10.0, 2.0)  # Scale to 0-2x
        variance_factor = min(velocity_variance / 100.0, 2.0)  # Scale to 0-2x
        
        # Adapt bbox noise
        self.Q_bbox = np.eye(8) * self.base_process_noise * (1.0 + velocity_factor * 0.5)
        self.R_bbox = np.eye(4) * self.base_measurement_noise * (1.0 + variance_factor * 0.3)
        
        # Adapt keypoint noise
        if self.keypoint_prediction_enabled and self.Q_keypoint is not None:
            self.Q_keypoint = np.eye(68) * self.base_process_noise * (1.0 + velocity_factor * 0.5)
            self.R_keypoint = np.eye(34) * self.base_measurement_noise * (1.0 + variance_factor * 0.3)
    
    def predict_bbox(self) -> np.ndarray:
        """Predict next bbox state"""
        self.bbox_state = self.F_bbox @ self.bbox_state
        self.bbox_covariance = self.F_bbox @ self.bbox_covariance @ self.F_bbox.T + self.Q_bbox
        return self.bbox_state[:4]  # Return [x, y, w, h]
    
    def update_bbox(self, measurement: np.ndarray):
        """Update bbox with measurement [x, y, w, h]"""
        y = measurement - self.H_bbox @ self.bbox_state
        S = self.H_bbox @ self.bbox_covariance @ self.H_bbox.T + self.R_bbox
        K = self.bbox_covariance @ self.H_bbox.T @ np.linalg.inv(S)
        
        self.bbox_state = self.bbox_state + K @ y
        self.bbox_covariance = (np.eye(8) - K @ self.H_bbox) @ self.bbox_covariance
        
        # Update velocity history for adaptive noise
        velocity = self.bbox_state[4:8]
        self.velocity_history.append(velocity.copy())
        
        # Adapt noise
        self._adapt_noise()
        
        return self.bbox_state[:4]
    
    def predict_keypoints(self) -> Optional[np.ndarray]:
        """Predict next keypoints state"""
        if not self.keypoint_prediction_enabled or self.keypoint_state is None:
            return None
        
        self.keypoint_state = self.F_keypoint @ self.keypoint_state
        self.keypoint_covariance = self.F_keypoint @ self.keypoint_covariance @ self.F_keypoint.T + self.Q_keypoint
        
        # Extract predicted positions [34] -> [17, 2]
        predicted_xy = self.keypoint_state[:34].reshape(17, 2)
        
        # Return as [17, 3] with confidence = 0.5 (moderate)
        predicted_keypoints = np.zeros((17, 3))
        predicted_keypoints[:, :2] = predicted_xy
        predicted_keypoints[:, 2] = 0.5  # Moderate confidence for predicted keypoints
        
        return predicted_keypoints
    
    def update_keypoints(self, measurement: np.ndarray):
        """
        Update keypoints with measurement [17, 3]
        
        Args:
            measurement: Keypoints array [17, 3] (x, y, confidence)
        """
        if not self.keypoint_prediction_enabled:
            return None
        
        if self.keypoint_state is None:
            self.initialize_keypoints(measurement)
            return measurement
        
        # Extract x, y from measurement
        meas_xy = measurement[:, :2].flatten()  # [34]
        
        # Only update keypoints with sufficient confidence
        confidence_mask = measurement[:, 2] >= 0.3
        valid_indices = np.where(confidence_mask)[0]
        
        if len(valid_indices) == 0:
            # No valid keypoints, just predict
            return self.predict_keypoints()
        
        # Update only valid keypoints
        # H_keypoint is (34, 68), keypoint_state is (68,)
        # Extract predicted positions from state
        predicted_xy = self.keypoint_state[:34]
        y = meas_xy - predicted_xy
        
        # Adjust measurement noise for low-confidence keypoints
        R_adjusted = self.R_keypoint.copy()
        for i, conf in enumerate(measurement[:, 2]):
            if conf < 0.5:
                # Increase measurement noise for low-confidence keypoints
                idx = i * 2
                R_adjusted[idx, idx] *= (1.0 + (0.5 - conf) * 2.0)
                R_adjusted[idx+1, idx+1] *= (1.0 + (0.5 - conf) * 2.0)
        
        # Extract covariance for positions only (34x34)
        P_pos = self.keypoint_covariance[:34, :34]
        
        # H_keypoint is (34, 68), but we only use position part (34, 34)
        # So we use H_pos = I (34x34) since we observe positions directly
        H_pos = np.eye(34)
        
        S = H_pos @ P_pos @ H_pos.T + R_adjusted
        try:
            K = P_pos @ H_pos.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            # Fallback if matrix is singular
            K = P_pos @ H_pos.T @ np.linalg.pinv(S)
        
        # Update position state
        self.keypoint_state[:34] = self.keypoint_state[:34] + K @ y
        
        # Update covariance (only position part)
        I_minus_KH = np.eye(34) - K @ H_pos
        self.keypoint_covariance[:34, :34] = I_minus_KH @ P_pos
        
        # Update velocities (approximate from position change)
        if len(self.motion_history) > 0:
            prev_keypoints = self.motion_history[-1]
            if prev_keypoints is not None:
                prev_xy = prev_keypoints[:, :2].flatten()
                velocity = meas_xy - prev_xy
                self.keypoint_state[34:] = velocity * 0.3 + self.keypoint_state[34:] * 0.7  # Smooth update
        
        # Store in history
        self.motion_history.append(measurement.copy())
        
        # Adapt noise
        self._adapt_noise()
        
        # Return updated keypoints
        updated_xy = self.keypoint_state[:34].reshape(17, 2)
        updated_keypoints = measurement.copy()
        updated_keypoints[:, :2] = updated_xy
        
        return updated_keypoints
    
    def reset(self):
        """Reset filter state"""
        self.bbox_state = np.zeros(8)
        self.bbox_covariance = np.eye(8) * 10
        self.keypoint_state = None
        self.keypoint_covariance = None
        self.motion_history.clear()
        self.velocity_history.clear()
        self.Q_bbox = np.eye(8) * self.base_process_noise
        self.R_bbox = np.eye(4) * self.base_measurement_noise

