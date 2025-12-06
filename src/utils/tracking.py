"""
Multi-person tracking sử dụng OC-SORT hoặc simple tracking
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import src.config as config


class SimpleTracker:
    """
    Simple tracker dựa trên IoU và distance matching
    Không cần OC-SORT phức tạp, phù hợp cho tracking ổn định
    """
    
    def __init__(
        self,
        max_age: int = None,
        min_hits: int = None,
        iou_threshold: float = None
    ):
        self.max_age = max_age or config.TRACKING_CONFIG["max_age"]
        self.min_hits = min_hits or config.TRACKING_CONFIG["min_hits"]
        self.iou_threshold = iou_threshold or config.TRACKING_CONFIG["iou_threshold"]
        
        self.tracks = {}  # {track_id: Track}
        self.next_id = 0
        self.frame_count = 0
    
    def update(self, detections: List[np.ndarray]) -> Dict[int, np.ndarray]:
        """
        Update tracks với detections mới
        
        Args:
            detections: List các keypoints [17, 3] cho mỗi người
            
        Returns:
            Dict {track_id: keypoints} cho các track đã được xác nhận
        """
        self.frame_count += 1
        
        if len(detections) == 0:
            # Không có detection, tăng age cho tất cả tracks
            for track_id in list(self.tracks.keys()):
                self.tracks[track_id].age += 1
                if self.tracks[track_id].age > self.max_age:
                    del self.tracks[track_id]
            return {}
        
        # Tính bounding box cho mỗi detection
        detection_boxes = [self._keypoints_to_bbox(kpts) for kpts in detections]
        
        # Match detections với tracks hiện tại
        matched, unmatched_dets, unmatched_trks = self._associate(
            detection_boxes, list(self.tracks.keys())
        )
        
        # Update matched tracks
        for det_idx, trk_id in matched:
            self.tracks[trk_id].update(detections[det_idx], self.frame_count)
        
        # Tạo tracks mới cho unmatched detections
        for det_idx in unmatched_dets:
            if self.next_id < config.TRACKING_CONFIG["max_people"]:
                track = Track(self.next_id, detections[det_idx], self.frame_count)
                self.tracks[self.next_id] = track
                self.next_id += 1
        
        # Xóa tracks quá cũ
        for trk_id in unmatched_trks:
            self.tracks[trk_id].age += 1
            if self.tracks[trk_id].age > self.max_age:
                del self.tracks[trk_id]
        
        # Trả về các track đã được xác nhận (hits >= min_hits)
        confirmed_tracks = {}
        for trk_id, track in self.tracks.items():
            if track.hits >= self.min_hits:
                confirmed_tracks[trk_id] = track.keypoints
        
        return confirmed_tracks
    
    def _keypoints_to_bbox(self, keypoints: np.ndarray) -> np.ndarray:
        """Chuyển keypoints thành bounding box [x1, y1, x2, y2]"""
        valid_kpts = keypoints[keypoints[:, 2] > 0]  # Chỉ lấy keypoints có confidence > 0
        if len(valid_kpts) == 0:
            return np.array([0, 0, 0, 0])
        
        x_coords = valid_kpts[:, 0]
        y_coords = valid_kpts[:, 1]
        
        x1 = np.min(x_coords)
        y1 = np.min(y_coords)
        x2 = np.max(x_coords)
        y2 = np.max(y_coords)
        
        return np.array([x1, y1, x2, y2])
    
    def _calculate_iou(self, box1: np.ndarray, box2: np.ndarray) -> float:
        """Tính IoU giữa 2 bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Tính diện tích giao nhau
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        inter_area = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Diện tích mỗi box
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        # IoU
        union_area = box1_area + box2_area - inter_area
        if union_area == 0:
            return 0.0
        
        return inter_area / union_area
    
    def _associate(
        self,
        detections: List[np.ndarray],
        track_ids: List[int]
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Match detections với tracks
        
        Returns:
            (matched, unmatched_dets, unmatched_trks)
        """
        if len(track_ids) == 0:
            return [], list(range(len(detections))), []
        
        if len(detections) == 0:
            return [], [], track_ids
        
        # Tính IoU matrix
        iou_matrix = np.zeros((len(detections), len(track_ids)))
        for i, det_box in enumerate(detections):
            for j, trk_id in enumerate(track_ids):
                trk_box = self._keypoints_to_bbox(self.tracks[trk_id].keypoints)
                iou_matrix[i, j] = self._calculate_iou(det_box, trk_box)
        
        # Greedy matching
        matched = []
        unmatched_dets = []
        unmatched_trks = list(range(len(track_ids)))
        
        # Sắp xếp theo IoU giảm dần
        matches = []
        for i in range(len(detections)):
            for j in range(len(track_ids)):
                if iou_matrix[i, j] > self.iou_threshold:
                    matches.append((i, j, iou_matrix[i, j]))
        
        matches.sort(key=lambda x: x[2], reverse=True)
        
        used_dets = set()
        used_trks = set()
        
        for det_idx, trk_idx, iou in matches:
            if det_idx not in used_dets and trk_idx not in used_trks:
                matched.append((det_idx, track_ids[trk_idx]))
                used_dets.add(det_idx)
                used_trks.add(trk_idx)
        
        unmatched_dets = [i for i in range(len(detections)) if i not in used_dets]
        unmatched_trks = [track_ids[j] for j in range(len(track_ids)) if j not in used_trks]
        
        return matched, unmatched_dets, unmatched_trks


class Track:
    """Đại diện cho một track (người)"""
    
    def __init__(self, track_id: int, keypoints: np.ndarray, frame_id: int):
        self.track_id = track_id
        self.keypoints = keypoints
        self.hits = 1  # Số lần được match
        self.age = 0  # Số frame không được match
        self.last_seen = frame_id
    
    def update(self, keypoints: np.ndarray, frame_id: int):
        """Update track với keypoints mới"""
        self.keypoints = keypoints
        self.hits += 1
        self.age = 0
        self.last_seen = frame_id


def track_people_in_video(
    skeletons_per_frame: List[List[np.ndarray]]
) -> Dict[int, List[np.ndarray]]:
    """
    Track nhiều người qua các frame
    
    Args:
        skeletons_per_frame: List các frame, mỗi frame là list keypoints
        
    Returns:
        Dict {person_id: [keypoints_frame0, keypoints_frame1, ...]}
    """
    tracker = SimpleTracker()
    
    tracked_people = defaultdict(list)
    
    for frame_idx, detections in enumerate(skeletons_per_frame):
        confirmed_tracks = tracker.update(detections)
        
        # Thêm keypoints vào track tương ứng
        for person_id, keypoints in confirmed_tracks.items():
            tracked_people[person_id].append(keypoints)
    
    # Chuyển list thành numpy array cho mỗi người
    result = {}
    for person_id, keypoints_list in tracked_people.items():
        result[person_id] = np.array(keypoints_list)
    
    return result

