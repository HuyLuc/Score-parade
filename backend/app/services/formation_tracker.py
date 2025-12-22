"""
Formation-based Tracking for Military Parade Formation
Gán người vào vị trí cố định trong đội hình để giảm ID switching
"""
import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import deque
import logging

from backend.app.config import KEYPOINT_INDICES

logger = logging.getLogger(__name__)


def _calculate_torso_length(keypoints: np.ndarray) -> float:
    """
    Tính chiều dài torso (vai → hông) cho 1 frame.
    Sử dụng trung bình vai trái/phải và hông trái/phải.
    """
    ls = KEYPOINT_INDICES["left_shoulder"]
    rs = KEYPOINT_INDICES["right_shoulder"]
    lh = KEYPOINT_INDICES["left_hip"]
    rh = KEYPOINT_INDICES["right_hip"]

    # Get shoulder center
    if (keypoints[ls, 2] >= 0.3 and keypoints[rs, 2] >= 0.3):
        shoulder_center = (
            (keypoints[ls, 0] + keypoints[rs, 0]) / 2,
            (keypoints[ls, 1] + keypoints[rs, 1]) / 2
        )
    elif keypoints[ls, 2] >= 0.3:
        shoulder_center = (keypoints[ls, 0], keypoints[ls, 1])
    elif keypoints[rs, 2] >= 0.3:
        shoulder_center = (keypoints[rs, 0], keypoints[rs, 1])
    else:
        return 0.0

    # Get hip center
    if (keypoints[lh, 2] >= 0.3 and keypoints[rh, 2] >= 0.3):
        hip_center = (
            (keypoints[lh, 0] + keypoints[rh, 0]) / 2,
            (keypoints[lh, 1] + keypoints[rh, 1]) / 2
        )
    elif keypoints[lh, 2] >= 0.3:
        hip_center = (keypoints[lh, 0], keypoints[lh, 1])
    elif keypoints[rh, 2] >= 0.3:
        hip_center = (keypoints[rh, 0], keypoints[rh, 1])
    else:
        return 0.0

    return float(np.sqrt(
        (shoulder_center[0] - hip_center[0]) ** 2 +
        (shoulder_center[1] - hip_center[1]) ** 2
    ))


def _get_bbox_center(bbox: np.ndarray) -> np.ndarray:
    """Lấy tọa độ trung tâm của bbox [x1, y1, x2, y2]"""
    x1, y1, x2, y2 = bbox
    return np.array([(x1 + x2) / 2, (y1 + y2) / 2])


class FormationTracker:
    """
    Formation-based Tracking cho điều lệnh đội hình.
    
    Ý tưởng:
    - Trong 30 frame đầu: khởi tạo formation dựa trên vị trí x (trái → phải)
    - Frame sau: match detections với vị trí formation gần nhất
    - Sử dụng khoảng cách không gian + body proportion để match
    - EMA smoothing để cập nhật vị trí formation theo thời gian
    """
    
    def __init__(
        self,
        expected_num_people: int = 2,
        init_frames: int = 30,
        match_threshold: float = 200.0,
        ema_alpha: float = 0.1,
        enabled: bool = True
    ):
        """
        Args:
            expected_num_people: Số người mong đợi trong đội hình
            init_frames: Số frame để khởi tạo formation
            match_threshold: Ngưỡng khoảng cách tối đa để match với formation position
            ema_alpha: Hệ số EMA smoothing cho cập nhật vị trí (0.0-1.0)
            enabled: Bật/tắt formation tracking
        """
        self.expected_num_people = expected_num_people
        self.init_frames = init_frames
        self.match_threshold = match_threshold
        self.ema_alpha = ema_alpha
        self.enabled = enabled
        
        # Formation positions: {position_id: {'bbox_center': np.array, 'torso_length': float}}
        self.formation_positions: Dict[str, Dict] = {}
        
        # Track initialization state
        self.initialized = False
        self.init_frame_count = 0
        
        # History for EMA smoothing
        self.position_history: Dict[str, deque] = {}
    
    def reset(self):
        """Reset formation tracker state"""
        self.formation_positions = {}
        self.initialized = False
        self.init_frame_count = 0
        self.position_history = {}
    
    def assign_to_formation(
        self,
        detections: List[Dict],
        frame_num: int
    ) -> List[Dict]:
        """
        Gán detections vào các vị trí formation.
        
        Args:
            detections: List of {"bbox": [x1,y1,x2,y2], "score": float, "keypoints": np.ndarray}
            frame_num: Current frame number
        
        Returns:
            List of detections assigned to formation positions (có thêm field 'formation_id')
        """
        if not self.enabled:
            return detections
        
        # Phase 1: Khởi tạo formation trong init_frames đầu
        if not self.initialized and frame_num < self.init_frames:
            return self._initialize_formation(detections, frame_num)
        
        # Phase 2: Match với formation positions đã có
        if self.initialized:
            return self._match_to_formation(detections, frame_num)
        
        # Fallback: chưa khởi tạo xong, trả về detections gốc
        return detections
    
    def _initialize_formation(
        self,
        detections: List[Dict],
        frame_num: int
    ) -> List[Dict]:
        """
        Khởi tạo formation trong init_frames đầu.
        Sắp xếp detections theo tọa độ x (trái → phải).
        """
        if not detections:
            return []
        
        # Sắp xếp theo tọa độ x (trái → phải)
        sorted_det = sorted(
            detections,
            key=lambda d: _get_bbox_center(d['bbox'])[0]
        )
        
        # Chỉ lấy expected_num_people detections đầu tiên
        selected_det = sorted_det[:self.expected_num_people]
        
        # Khởi tạo formation positions
        for i, det in enumerate(selected_det):
            position_id = f"position_{i}"
            bbox_center = _get_bbox_center(det['bbox'])
            torso_length = _calculate_torso_length(det.get('keypoints'))
            
            if torso_length == 0.0:
                continue
            
            # Khởi tạo position
            if position_id not in self.formation_positions:
                self.formation_positions[position_id] = {
                    'bbox_center': bbox_center.copy(),
                    'torso_length': torso_length
                }
                self.position_history[position_id] = deque(maxlen=10)
            else:
                # EMA update cho các frame tiếp theo trong giai đoạn init
                old_center = self.formation_positions[position_id]['bbox_center']
                old_torso = self.formation_positions[position_id]['torso_length']
                
                self.formation_positions[position_id]['bbox_center'] = (
                    self.ema_alpha * bbox_center + (1 - self.ema_alpha) * old_center
                )
                self.formation_positions[position_id]['torso_length'] = (
                    self.ema_alpha * torso_length + (1 - self.ema_alpha) * old_torso
                )
            
            # Lưu history
            self.position_history[position_id].append({
                'bbox_center': bbox_center.copy(),
                'torso_length': torso_length
            })
            
            # Gán formation_id cho detection
            det['formation_id'] = position_id
        
        # Sau init_frames, đánh dấu đã khởi tạo xong
        self.init_frame_count += 1
        if self.init_frame_count >= self.init_frames:
            self.initialized = True
            logger.info(f"Formation initialized with {len(self.formation_positions)} positions")
        
        return selected_det
    
    def _match_to_formation(
        self,
        detections: List[Dict],
        frame_num: int
    ) -> List[Dict]:
        """
        Match detections với formation positions đã có.
        Sử dụng khoảng cách không gian + body proportion.
        """
        if not detections or not self.formation_positions:
            return []
        
        assigned = []
        used_positions = set()
        
        for det in detections:
            bbox_center = _get_bbox_center(det['bbox'])
            torso_length = _calculate_torso_length(det.get('keypoints'))
            
            if torso_length == 0.0:
                continue
            
            best_pos = None
            min_dist = float('inf')
            
            # Tìm position gần nhất
            for pos_id, pos_data in self.formation_positions.items():
                if pos_id in used_positions:
                    continue
                
                # Khoảng cách không gian (Euclidean)
                spatial_dist = np.linalg.norm(
                    bbox_center - pos_data['bbox_center']
                )
                
                # Chênh lệch body proportion (torso length)
                torso_diff = abs(torso_length - pos_data['torso_length'])
                
                # Tổng khoảng cách (spatial + body proportion)
                # Nhân torso_diff với 100 để cân bằng với spatial_dist (pixels)
                total_dist = spatial_dist + torso_diff * 100.0
                
                if total_dist < min_dist:
                    min_dist = total_dist
                    best_pos = pos_id
            
            # Match nếu khoảng cách < threshold
            if best_pos and min_dist < self.match_threshold:
                det['formation_id'] = best_pos
                assigned.append(det)
                used_positions.add(best_pos)
                
                # EMA update position
                old_center = self.formation_positions[best_pos]['bbox_center']
                old_torso = self.formation_positions[best_pos]['torso_length']
                
                self.formation_positions[best_pos]['bbox_center'] = (
                    self.ema_alpha * bbox_center + (1 - self.ema_alpha) * old_center
                )
                self.formation_positions[best_pos]['torso_length'] = (
                    self.ema_alpha * torso_length + (1 - self.ema_alpha) * old_torso
                )
                
                # Lưu history
                if best_pos not in self.position_history:
                    self.position_history[best_pos] = deque(maxlen=10)
                self.position_history[best_pos].append({
                    'bbox_center': bbox_center.copy(),
                    'torso_length': torso_length
                })
        
        # Chỉ trả về đúng số người expected (ưu tiên các match tốt nhất)
        # Sắp xếp lại theo formation_id để đảm bảo thứ tự
        assigned_sorted = sorted(
            assigned,
            key=lambda d: int(d['formation_id'].split('_')[1])
        )
        
        return assigned_sorted[:self.expected_num_people]
    
    def get_formation_positions(self) -> Dict[str, Dict]:
        """Lấy thông tin các formation positions hiện tại"""
        return self.formation_positions.copy()
    
    def is_initialized(self) -> bool:
        """Kiểm tra xem formation đã được khởi tạo chưa"""
        return self.initialized

