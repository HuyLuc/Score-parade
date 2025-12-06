"""
Utilities cho làm mượt dữ liệu skeleton
"""
import numpy as np
from scipy.signal import savgol_filter
from typing import Optional
import src.config as config


def smooth_sequence(
    data: np.ndarray,
    method: str = "savgol",
    window_length: Optional[int] = None,
    polyorder: Optional[int] = None
) -> np.ndarray:
    """
    Làm mượt chuỗi dữ liệu
    
    Args:
        data: Array [n_frames, n_features] hoặc [n_frames, n_keypoints, 2]
        method: "savgol" hoặc "moving_average"
        window_length: Độ dài cửa sổ (mặc định từ config)
        polyorder: Bậc đa thức cho Savitzky-Golay (mặc định từ config)
        
    Returns:
        Dữ liệu đã được làm mượt
    """
    if window_length is None:
        window_length = config.SMOOTHING_CONFIG["window_length"]
    if polyorder is None:
        polyorder = config.SMOOTHING_CONFIG["polyorder"]
    
    # Đảm bảo window_length là số lẻ và nhỏ hơn số frame
    n_frames = data.shape[0]
    if window_length >= n_frames:
        window_length = n_frames if n_frames % 2 == 1 else n_frames - 1
    if window_length < 3:
        window_length = 3
    if window_length % 2 == 0:
        window_length -= 1
    
    if method == "savgol":
        return _savgol_smooth(data, window_length, polyorder)
    elif method == "moving_average":
        return _moving_average_smooth(data, window_length)
    else:
        raise ValueError(f"Method không được hỗ trợ: {method}")


def _savgol_smooth(
    data: np.ndarray,
    window_length: int,
    polyorder: int
) -> np.ndarray:
    """
    Làm mượt bằng Savitzky-Golay filter
    """
    # Đảm bảo polyorder < window_length
    if polyorder >= window_length:
        polyorder = window_length - 1
    
    if data.ndim == 2:
        # [n_frames, n_features]
        smoothed = np.zeros_like(data)
        for i in range(data.shape[1]):
            smoothed[:, i] = savgol_filter(
                data[:, i],
                window_length,
                polyorder
            )
        return smoothed
    elif data.ndim == 3:
        # [n_frames, n_keypoints, 2]
        smoothed = np.zeros_like(data)
        for kp_idx in range(data.shape[1]):
            for coord_idx in range(data.shape[2]):
                smoothed[:, kp_idx, coord_idx] = savgol_filter(
                    data[:, kp_idx, coord_idx],
                    window_length,
                    polyorder
                )
        return smoothed
    else:
        raise ValueError(f"Data shape không được hỗ trợ: {data.shape}")


def _moving_average_smooth(
    data: np.ndarray,
    window_length: int
) -> np.ndarray:
    """
    Làm mượt bằng moving average
    """
    if data.ndim == 2:
        # [n_frames, n_features]
        smoothed = np.zeros_like(data)
        for i in range(data.shape[1]):
            smoothed[:, i] = np.convolve(
                data[:, i],
                np.ones(window_length) / window_length,
                mode='same'
            )
        return smoothed
    elif data.ndim == 3:
        # [n_frames, n_keypoints, 2]
        smoothed = np.zeros_like(data)
        for kp_idx in range(data.shape[1]):
            for coord_idx in range(data.shape[2]):
                smoothed[:, kp_idx, coord_idx] = np.convolve(
                    data[:, kp_idx, coord_idx],
                    np.ones(window_length) / window_length,
                    mode='same'
                )
        return smoothed
    else:
        raise ValueError(f"Data shape không được hỗ trợ: {data.shape}")


def smooth_keypoints_sequence(keypoints_sequence: np.ndarray) -> np.ndarray:
    """
    Làm mượt chuỗi keypoints
    
    Args:
        keypoints_sequence: Array [n_frames, n_keypoints, 2] hoặc [n_frames, n_keypoints, 3]
        
    Returns:
        Keypoints đã được làm mượt
    """
    method = config.SMOOTHING_CONFIG["method"]
    window_length = config.SMOOTHING_CONFIG["window_length"]
    polyorder = config.SMOOTHING_CONFIG["polyorder"]
    
    # Chỉ làm mượt tọa độ x, y, giữ nguyên confidence nếu có
    if keypoints_sequence.shape[2] == 3:
        coords = keypoints_sequence[:, :, :2]
        confidence = keypoints_sequence[:, :, 2:3]
        smoothed_coords = smooth_sequence(coords, method, window_length, polyorder)
        return np.concatenate([smoothed_coords, confidence], axis=2)
    else:
        return smooth_sequence(keypoints_sequence, method, window_length, polyorder)

