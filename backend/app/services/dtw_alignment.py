"""
DTW (Dynamic Time Warping) Alignment Service

Xử lý căn chỉnh chuỗi frame giữa video test và golden template khi có tempo variation.
Giúp tránh penalty không công bằng khi test video nhanh hơn hoặc chậm hơn golden video.
"""
import numpy as np
from typing import List, Tuple, Optional, Dict
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean, cityblock, cosine
from backend.app.services.geometry import (
    calculate_arm_angle,
    calculate_leg_angle,
    calculate_arm_height,
    calculate_leg_height,
    calculate_head_angle,
)

# Constants
NUM_KEYPOINTS = 17  # COCO format has 17 keypoints
MIN_KEYPOINT_DIMENSIONS = 3  # x, y, confidence


class DTWAligner:
    """
    Dynamic Time Warping Aligner cho pose sequences
    
    Căn chỉnh chuỗi poses từ test video với golden video để xử lý tempo variations.
    """
    
    def __init__(self, window_size: int = 50, distance_metric: str = "euclidean"):
        """
        Khởi tạo DTW Aligner
        
        Args:
            window_size: Window size cho DTW (giới hạn warping path)
            distance_metric: Metric để tính khoảng cách ("euclidean", "manhattan", "cosine")
        """
        self.window_size = window_size
        self.distance_metric = distance_metric
        self.alignment_path = None
        self.test_to_golden_map = None
        
        # Map metric name to scipy distance function
        self.distance_functions = {
            "euclidean": euclidean,
            "manhattan": cityblock,
            "cosine": lambda a, b: cosine(a, b) if not (np.all(a == 0) or np.all(b == 0)) else 1.0
        }
    
    def extract_pose_features(self, keypoints: np.ndarray) -> np.ndarray:
        """
        Trích xuất features từ keypoints để dùng cho DTW alignment
        
        Features bao gồm:
        - Arm angles (left, right)
        - Leg angles (left, right)
        - Head angle
        - Arm heights (left, right)
        - Leg heights (left, right)
        - Relative positions of key joints
        
        Args:
            keypoints: Array of shape [17, 3] (x, y, confidence)
            
        Returns:
            Feature vector dạng 1D numpy array
        """
        features = []
        
        # 1. Arm angles
        left_arm_angle = calculate_arm_angle(keypoints, side="left")
        right_arm_angle = calculate_arm_angle(keypoints, side="right")
        features.extend([
            left_arm_angle if left_arm_angle is not None else 0.0,
            right_arm_angle if right_arm_angle is not None else 0.0
        ])
        
        # 2. Leg angles
        left_leg_angle = calculate_leg_angle(keypoints, side="left")
        right_leg_angle = calculate_leg_angle(keypoints, side="right")
        features.extend([
            left_leg_angle if left_leg_angle is not None else 0.0,
            right_leg_angle if right_leg_angle is not None else 0.0
        ])
        
        # 3. Head angle
        head_angle = calculate_head_angle(keypoints)
        features.append(head_angle if head_angle is not None else 0.0)
        
        # 4. Arm heights
        left_arm_height = calculate_arm_height(keypoints, side="left")
        right_arm_height = calculate_arm_height(keypoints, side="right")
        features.extend([
            left_arm_height if left_arm_height is not None else 0.0,
            right_arm_height if right_arm_height is not None else 0.0
        ])
        
        # 5. Leg heights
        left_leg_height = calculate_leg_height(keypoints, side="left")
        right_leg_height = calculate_leg_height(keypoints, side="right")
        features.extend([
            left_leg_height if left_leg_height is not None else 0.0,
            right_leg_height if right_leg_height is not None else 0.0
        ])
        
        # 6. Relative positions of key joints (normalized by torso length)
        # Shoulders
        left_shoulder = keypoints[5]  # left_shoulder
        right_shoulder = keypoints[6]  # right_shoulder
        
        # Hips
        left_hip = keypoints[11]  # left_hip
        right_hip = keypoints[12]  # right_hip
        
        # Calculate torso length for normalization
        if left_shoulder[2] > 0 and left_hip[2] > 0:
            torso_length_left = np.linalg.norm(left_shoulder[:2] - left_hip[:2])
        else:
            torso_length_left = 1.0
            
        if right_shoulder[2] > 0 and right_hip[2] > 0:
            torso_length_right = np.linalg.norm(right_shoulder[:2] - right_hip[:2])
        else:
            torso_length_right = 1.0
        
        avg_torso_length = (torso_length_left + torso_length_right) / 2.0
        if avg_torso_length < 10.0:  # Minimum threshold
            avg_torso_length = 100.0  # Default
        
        # Normalize and add wrist positions relative to shoulders
        for wrist_idx in [9, 10]:  # left_wrist, right_wrist
            shoulder_idx = 5 if wrist_idx == 9 else 6
            if keypoints[wrist_idx][2] > 0 and keypoints[shoulder_idx][2] > 0:
                rel_x = (keypoints[wrist_idx][0] - keypoints[shoulder_idx][0]) / avg_torso_length
                rel_y = (keypoints[wrist_idx][1] - keypoints[shoulder_idx][1]) / avg_torso_length
                features.extend([rel_x, rel_y])
            else:
                features.extend([0.0, 0.0])
        
        # Normalize and add ankle positions relative to hips
        for ankle_idx in [15, 16]:  # left_ankle, right_ankle
            hip_idx = 11 if ankle_idx == 15 else 12
            if keypoints[ankle_idx][2] > 0 and keypoints[hip_idx][2] > 0:
                rel_x = (keypoints[ankle_idx][0] - keypoints[hip_idx][0]) / avg_torso_length
                rel_y = (keypoints[ankle_idx][1] - keypoints[hip_idx][1]) / avg_torso_length
                features.extend([rel_x, rel_y])
            else:
                features.extend([0.0, 0.0])
        
        return np.array(features, dtype=np.float32)
    
    def align_sequences(
        self,
        test_keypoints_sequence: List[np.ndarray],
        golden_keypoints_sequence: List[np.ndarray]
    ) -> Tuple[float, List[Tuple[int, int]]]:
        """
        Căn chỉnh test sequence với golden sequence sử dụng DTW
        
        Args:
            test_keypoints_sequence: List of keypoints arrays từ test video
            golden_keypoints_sequence: List of keypoints arrays từ golden video
            
        Returns:
            Tuple (distance, path):
                - distance: DTW distance giữa 2 sequences
                - path: List of (test_idx, golden_idx) pairs representing alignment
        """
        # Extract features from both sequences
        test_features = []
        feature_dim = None  # Will be set from first valid frame
        
        for kps in test_keypoints_sequence:
            if kps.shape[0] >= NUM_KEYPOINTS and kps.shape[1] >= MIN_KEYPOINT_DIMENSIONS:
                features = self.extract_pose_features(kps)
                if feature_dim is None:
                    feature_dim = len(features)
                test_features.append(features)
            else:
                # Invalid keypoints, use zero vector
                if feature_dim is None:
                    feature_dim = 17  # Default feature dimension
                test_features.append(np.zeros(feature_dim, dtype=np.float32))
        
        golden_features = []
        for kps in golden_keypoints_sequence:
            if kps.shape[0] >= NUM_KEYPOINTS and kps.shape[1] >= MIN_KEYPOINT_DIMENSIONS:
                features = self.extract_pose_features(kps)
                if feature_dim is None:
                    feature_dim = len(features)
                golden_features.append(features)
            else:
                # Invalid keypoints, use zero vector
                if feature_dim is None:
                    feature_dim = 17  # Default feature dimension
                golden_features.append(np.zeros(feature_dim, dtype=np.float32))
        
        # Convert to numpy arrays
        test_features_array = np.array(test_features)
        golden_features_array = np.array(golden_features)
        
        # Get distance function
        dist_func = self.distance_functions.get(self.distance_metric, euclidean)
        
        # Perform DTW alignment with radius constraint
        distance, path = fastdtw(
            test_features_array,
            golden_features_array,
            radius=self.window_size,
            dist=dist_func
        )
        
        # Store alignment
        self.alignment_path = path
        
        # Create test_to_golden mapping for quick lookup
        self.test_to_golden_map = {}
        for test_idx, golden_idx in path:
            if test_idx not in self.test_to_golden_map:
                self.test_to_golden_map[test_idx] = []
            self.test_to_golden_map[test_idx].append(golden_idx)
        
        return distance, path
    
    def get_aligned_frame(self, test_frame_idx: int) -> Optional[int]:
        """
        Lấy golden frame index tương ứng với test frame index sau khi align
        
        Args:
            test_frame_idx: Index của frame trong test video
            
        Returns:
            Index của frame tương ứng trong golden video, hoặc None nếu không có mapping
        """
        if self.test_to_golden_map is None:
            return None
        
        if test_frame_idx not in self.test_to_golden_map:
            return None
        
        # Nếu có nhiều golden frames map tới test frame này, lấy golden frame đầu tiên
        # (có thể customize logic này nếu cần)
        golden_indices = self.test_to_golden_map[test_frame_idx]
        return golden_indices[0] if golden_indices else None
    
    def get_alignment_info(self) -> Optional[Dict]:
        """
        Lấy thông tin về alignment path
        
        Returns:
            Dictionary chứa thông tin alignment:
            {
                "test_frames": số lượng test frames,
                "golden_frames": số lượng golden frames,
                "path_length": độ dài alignment path,
                "tempo_ratio": tỉ lệ tempo (test/golden)
            }
        """
        if self.alignment_path is None or self.test_to_golden_map is None:
            return None
        
        test_frames = len(self.test_to_golden_map)
        golden_indices = set()
        for indices in self.test_to_golden_map.values():
            golden_indices.update(indices)
        golden_frames = len(golden_indices)
        
        # Tempo ratio: test frames / golden frames
        # > 1.0 means test is faster, < 1.0 means test is slower
        tempo_ratio = test_frames / golden_frames if golden_frames > 0 else 1.0
        
        return {
            "test_frames": test_frames,
            "golden_frames": golden_frames,
            "path_length": len(self.alignment_path),
            "tempo_ratio": tempo_ratio
        }
