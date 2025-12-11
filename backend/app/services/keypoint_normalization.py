"""
Service for normalizing keypoints by torso length to achieve scale-invariant comparison.

This module provides functions to normalize keypoints based on torso length (shoulder-to-hip distance),
making pose comparison fair regardless of person height or distance from camera.
"""
import numpy as np
from typing import Optional, Tuple, List
import backend.app.config as config


def calculate_torso_length(keypoints: np.ndarray) -> Optional[float]:
    """
    Calculate torso length as the average distance from shoulders to hips.
    
    Torso length is computed as the average of:
    - Left shoulder to left hip distance
    - Right shoulder to right hip distance
    
    This provides a robust scale reference that's less affected by pose variations.
    
    Args:
        keypoints: Array of shape [17, 2] or [17, 3] with (x, y) or (x, y, confidence)
        
    Returns:
        Average torso length in pixels, or None if keypoints are missing/invalid
        
    Examples:
        >>> kpts = np.array([[0,0,1], ..., [100,0,1], [100,150,1], ...])  # shoulder at y=0, hip at y=150
        >>> calculate_torso_length(kpts)
        150.0
    """
    if keypoints.shape[0] < 17:
        return None
    
    # Get shoulder and hip indices
    left_shoulder_idx = config.KEYPOINT_INDICES["left_shoulder"]
    right_shoulder_idx = config.KEYPOINT_INDICES["right_shoulder"]
    left_hip_idx = config.KEYPOINT_INDICES["left_hip"]
    right_hip_idx = config.KEYPOINT_INDICES["right_hip"]
    
    # Extract coordinates (x, y only)
    left_shoulder = keypoints[left_shoulder_idx, :2]
    right_shoulder = keypoints[right_shoulder_idx, :2]
    left_hip = keypoints[left_hip_idx, :2]
    right_hip = keypoints[right_hip_idx, :2]
    
    # Check confidence if available
    min_confidence = config.NORMALIZATION_CONFIG.get("min_confidence", 0.5)
    if keypoints.shape[1] > 2:
        if (keypoints[left_shoulder_idx, 2] < min_confidence or
            keypoints[right_shoulder_idx, 2] < min_confidence or
            keypoints[left_hip_idx, 2] < min_confidence or
            keypoints[right_hip_idx, 2] < min_confidence):
            return None
    
    # Calculate distances
    left_torso = np.linalg.norm(left_shoulder - left_hip)
    right_torso = np.linalg.norm(right_shoulder - right_hip)
    
    # Return average
    avg_torso = (left_torso + right_torso) / 2.0
    
    # Sanity check: torso length should be reasonable
    min_torso = config.NORMALIZATION_CONFIG.get("min_torso_length", 10.0)
    if avg_torso < min_torso:
        return None
    
    return avg_torso


def normalize_keypoints(
    keypoints: np.ndarray,
    torso_length: Optional[float] = None,
    reference_torso: Optional[float] = None
) -> Tuple[Optional[np.ndarray], Optional[float]]:
    """
    Normalize keypoints by scaling to a reference torso length (absolute normalization).
    
    This scales all coordinates so that the torso length matches the reference value,
    making comparisons independent of person size or camera distance.
    
    Args:
        keypoints: Array of shape [17, 2] or [17, 3]
        torso_length: Pre-computed torso length (if None, will calculate)
        reference_torso: Target torso length (if None, uses config default)
        
    Returns:
        Tuple of (normalized_keypoints, scale_factor)
        - normalized_keypoints: Scaled keypoints with same shape as input
        - scale_factor: The scaling factor applied
        Returns (None, None) if normalization fails
        
    Examples:
        >>> kpts = np.array([[100, 100, 1], [200, 200, 1], ...])  # torso=150px
        >>> norm_kpts, scale = normalize_keypoints(kpts, reference_torso=100.0)
        >>> scale
        0.6667  # 100/150
    """
    if torso_length is None:
        torso_length = calculate_torso_length(keypoints)
    
    if torso_length is None:
        return None, None
    
    if reference_torso is None:
        reference_torso = config.NORMALIZATION_CONFIG.get("reference_torso_length", 100.0)
    
    # Calculate scale factor
    scale = reference_torso / torso_length
    
    # Create normalized copy
    normalized = keypoints.copy()
    
    # Scale x, y coordinates (not confidence)
    normalized[:, :2] = keypoints[:, :2] * scale
    
    return normalized, scale


def normalize_keypoints_relative(
    keypoints: np.ndarray,
    torso_length: Optional[float] = None
) -> Optional[np.ndarray]:
    """
    Normalize keypoints to relative coordinates centered at torso midpoint.
    
    This normalization:
    1. Centers coordinates at the midpoint between shoulders and hips
    2. Scales by torso length so torso = 1.0 unit
    3. Results in approximate range [-1, 1] for most keypoints
    
    This is the recommended normalization for pose comparison as it's:
    - Translation invariant (centered)
    - Scale invariant (normalized by torso)
    - Rotation aware (preserves relative angles)
    
    Args:
        keypoints: Array of shape [17, 2] or [17, 3]
        torso_length: Pre-computed torso length (if None, will calculate)
        
    Returns:
        Normalized keypoints with same shape as input, or None if normalization fails
        
    Examples:
        >>> kpts = np.array([[100, 50, 1], [100, 200, 1], ...])  # shoulder-hip on same x
        >>> norm = normalize_keypoints_relative(kpts)
        >>> # Torso midpoint becomes origin, torso length becomes 1.0
    """
    if torso_length is None:
        torso_length = calculate_torso_length(keypoints)
    
    if torso_length is None:
        return None
    
    # Get shoulder and hip positions
    left_shoulder_idx = config.KEYPOINT_INDICES["left_shoulder"]
    right_shoulder_idx = config.KEYPOINT_INDICES["right_shoulder"]
    left_hip_idx = config.KEYPOINT_INDICES["left_hip"]
    right_hip_idx = config.KEYPOINT_INDICES["right_hip"]
    
    left_shoulder = keypoints[left_shoulder_idx, :2]
    right_shoulder = keypoints[right_shoulder_idx, :2]
    left_hip = keypoints[left_hip_idx, :2]
    right_hip = keypoints[right_hip_idx, :2]
    
    # Calculate torso midpoint (center between shoulder center and hip center)
    shoulder_center = (left_shoulder + right_shoulder) / 2.0
    hip_center = (left_hip + right_hip) / 2.0
    torso_center = (shoulder_center + hip_center) / 2.0
    
    # Create normalized copy
    normalized = keypoints.copy()
    
    # Translate to center at origin and scale by torso length
    normalized[:, :2] = (keypoints[:, :2] - torso_center) / torso_length
    
    return normalized


def denormalize_keypoints(
    normalized_keypoints: np.ndarray,
    scale: float,
    center: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Convert normalized keypoints back to original pixel coordinates.
    
    This reverses the normalization applied by normalize_keypoints() or 
    normalize_keypoints_relative().
    
    Args:
        normalized_keypoints: Normalized keypoints [17, 2] or [17, 3]
        scale: Scale factor used in normalization (from normalize_keypoints)
        center: Center point for relative normalization (if used)
        
    Returns:
        Denormalized keypoints in pixel coordinates
        
    Examples:
        >>> norm_kpts, scale = normalize_keypoints(original, reference_torso=100)
        >>> recovered = denormalize_keypoints(norm_kpts, scale)
        >>> np.allclose(recovered[:, :2], original[:, :2])
        True
    """
    denormalized = normalized_keypoints.copy()
    
    if center is not None:
        # Reverse relative normalization: scale then translate
        denormalized[:, :2] = normalized_keypoints[:, :2] * (1.0 / scale) + center
    else:
        # Reverse absolute normalization: just scale
        denormalized[:, :2] = normalized_keypoints[:, :2] / scale
    
    return denormalized


def batch_normalize_keypoints(
    keypoints_list: List[np.ndarray],
    method: str = "relative"
) -> List[Optional[np.ndarray]]:
    """
    Normalize multiple frames of keypoints.
    
    This is useful for processing video sequences where you want consistent
    normalization across all frames.
    
    Args:
        keypoints_list: List of keypoint arrays, each [17, 2] or [17, 3]
        method: "relative" or "absolute" normalization
        
    Returns:
        List of normalized keypoints (None for frames that failed normalization)
        
    Examples:
        >>> frames = [frame1_kpts, frame2_kpts, frame3_kpts]
        >>> normalized_frames = batch_normalize_keypoints(frames, method="relative")
    """
    normalized_list = []
    
    for keypoints in keypoints_list:
        if method == "relative":
            normalized = normalize_keypoints_relative(keypoints)
        elif method == "absolute":
            normalized, _ = normalize_keypoints(keypoints)
        else:
            raise ValueError(f"Unknown normalization method: {method}")
        
        normalized_list.append(normalized)
    
    return normalized_list
