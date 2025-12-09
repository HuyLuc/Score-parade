"""
Multi-person tracking sử dụng OC-SORT hoặc simple tracking
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import src.config as config


class SimpleTracker:
    """
    Enhanced tracker với pose similarity và Kalman filter
    Tracking chính xác hơn bằng cách kết hợp IoU và pose similarity
    """
    
    def __init__(
        self,
        max_age: int = None,
        min_hits: int = None,
        iou_threshold: float = None,
        pose_similarity_threshold: float = None,
        pose_weight: float = None,
        use_kalman: bool = None
    ):
        self.max_age = max_age or config.TRACKING_CONFIG["max_age"]
        self.min_hits = min_hits or config.TRACKING_CONFIG["min_hits"]
        self.iou_threshold = iou_threshold or config.TRACKING_CONFIG["iou_threshold"]
        self.pose_similarity_threshold = pose_similarity_threshold or config.TRACKING_CONFIG["pose_similarity_threshold"]
        self.pose_weight = pose_weight or config.TRACKING_CONFIG["pose_weight"]
        self.use_kalman = use_kalman if use_kalman is not None else config.TRACKING_CONFIG["use_kalman"]
        self.merge_similar_tracks = config.TRACKING_CONFIG.get("merge_similar_tracks", True)
        self.merge_threshold = config.TRACKING_CONFIG.get("merge_threshold", 0.7)
        
        self.tracks = {}  # {track_id: Track}
        self.next_id = 0
        self.frame_count = 0
        self.merged_tracks = {}  # {old_id: new_id} - mapping các track đã merge
    
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
        
        # Merge các tracks tương tự nhau (định kỳ mỗi 10 frames)
        if self.frame_count % 10 == 0:
            self._merge_similar_tracks()
        
        # Trả về các track đã được xác nhận (hits >= min_hits)
        confirmed_tracks = {}
        for trk_id, track in self.tracks.items():
            if track.hits >= self.min_hits:
                confirmed_tracks[trk_id] = track.keypoints
        
        return confirmed_tracks
    
    def _keypoints_to_bbox(self, keypoints: np.ndarray) -> np.ndarray:
        """Chuyển keypoints thành bounding box [x1, y1, x2, y2]"""
        # Đảm bảo keypoints là array
        keypoints = np.asarray(keypoints)
        
        # Kiểm tra nếu đã là bbox [4] hoặc [1, 4] thì trả về luôn
        if keypoints.size == 4:
            return keypoints.flatten()
        
        # Đảm bảo keypoints là array 2D [n_keypoints, 3]
        keypoints = np.atleast_2d(keypoints)
        
        # Nếu shape là (1, n) với n = 51 (17*3), reshape thành (17, 3)
        if keypoints.shape[0] == 1 and keypoints.shape[1] == 51:
            keypoints = keypoints.reshape(17, 3)
        
        # Kiểm tra shape hợp lệ [17, 3] hoặc [n, 3]
        if keypoints.ndim != 2 or keypoints.shape[1] != 3:
            print(f"⚠️  Warning: Invalid keypoints shape {keypoints.shape}, returning default bbox")
            return np.array([0, 0, 0, 0])
        
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
    
    def _calculate_pose_similarity(self, kpts1: np.ndarray, kpts2: np.ndarray) -> float:
        """
        Tính độ tương đồng giữa 2 poses dựa trên keypoints
        
        Args:
            kpts1, kpts2: Keypoints [17, 3] với (x, y, confidence)
            
        Returns:
            Similarity score từ 0-1 (1 = giống nhất)
        """
        # Đảm bảo keypoints là array 2D
        kpts1 = np.asarray(kpts1)
        kpts2 = np.asarray(kpts2)
        
        kpts1 = np.atleast_2d(kpts1)
        kpts2 = np.atleast_2d(kpts2)
        
        # Nếu shape là (1, 51), reshape thành (17, 3)
        if kpts1.shape[0] == 1 and kpts1.shape[1] == 51:
            kpts1 = kpts1.reshape(17, 3)
        if kpts2.shape[0] == 1 and kpts2.shape[1] == 51:
            kpts2 = kpts2.reshape(17, 3)
        
        # Kiểm tra shape hợp lệ
        if kpts1.ndim != 2 or kpts1.shape[1] != 3 or kpts2.ndim != 2 or kpts2.shape[1] != 3:
            return 0.0
        
        # Chỉ lấy keypoints có confidence > 0.3
        valid_mask1 = kpts1[:, 2] > 0.3
        valid_mask2 = kpts2[:, 2] > 0.3
        valid_mask = valid_mask1 & valid_mask2
        
        if not np.any(valid_mask):
            return 0.0
        
        # Normalize keypoints về center (0, 0)
        kpts1_valid = kpts1[valid_mask, :2]
        kpts2_valid = kpts2[valid_mask, :2]
        
        center1 = np.mean(kpts1_valid, axis=0)
        center2 = np.mean(kpts2_valid, axis=0)
        
        kpts1_norm = kpts1_valid - center1
        kpts2_norm = kpts2_valid - center2
        
        # Scale về cùng kích thước (dựa trên bounding box)
        scale1 = np.max(np.abs(kpts1_norm)) + 1e-6
        scale2 = np.max(np.abs(kpts2_norm)) + 1e-6
        
        kpts1_norm /= scale1
        kpts2_norm /= scale2
        
        # Tính khoảng cách Euclidean trung bình
        distances = np.linalg.norm(kpts1_norm - kpts2_norm, axis=1)
        avg_distance = np.mean(distances)
        
        # Chuyển về similarity (0-1), sử dụng sigmoid
        similarity = 1.0 / (1.0 + avg_distance * 2.0)
        
        return similarity
    
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
        Match detections với tracks sử dụng cả IoU và pose similarity
        
        Returns:
            (matched, unmatched_dets, unmatched_trks)
        """
        if len(track_ids) == 0:
            return [], list(range(len(detections))), []
        
        if len(detections) == 0:
            return [], [], track_ids
        
        # Tính IoU matrix và pose similarity matrix
        iou_matrix = np.zeros((len(detections), len(track_ids)))
        pose_sim_matrix = np.zeros((len(detections), len(track_ids)))
        
        detection_boxes = [self._keypoints_to_bbox(det) for det in detections]
        
        for i, det_kpts in enumerate(detections):
            for j, trk_id in enumerate(track_ids):
                # Tính IoU
                trk_box = self._keypoints_to_bbox(self.tracks[trk_id].keypoints)
                iou_matrix[i, j] = self._calculate_iou(detection_boxes[i], trk_box)
                
                # Tính pose similarity
                pose_sim_matrix[i, j] = self._calculate_pose_similarity(
                    det_kpts, self.tracks[trk_id].keypoints
                )
        
        # Kết hợp IoU và pose similarity
        combined_score = (
            (1 - self.pose_weight) * iou_matrix + 
            self.pose_weight * pose_sim_matrix
        )
        
        # Greedy matching với combined score
        matched = []
        matches = []
        
        for i in range(len(detections)):
            for j in range(len(track_ids)):
                # Yêu cầu cả IoU và pose similarity đều đạt ngưỡng tối thiểu
                if (iou_matrix[i, j] > self.iou_threshold * 0.7 and  # Giảm IoU threshold một chút
                    pose_sim_matrix[i, j] > self.pose_similarity_threshold):
                    matches.append((i, j, combined_score[i, j]))
        
        matches.sort(key=lambda x: x[2], reverse=True)
        
        used_dets = set()
        used_trks = set()
        
        for det_idx, trk_idx, score in matches:
            if det_idx not in used_dets and trk_idx not in used_trks:
                matched.append((det_idx, track_ids[trk_idx]))
                used_dets.add(det_idx)
                used_trks.add(trk_idx)
        
        unmatched_dets = [i for i in range(len(detections)) if i not in used_dets]
        unmatched_trks = [track_ids[j] for j in range(len(track_ids)) if j not in used_trks]
        
        return matched, unmatched_dets, unmatched_trks
    
    def _merge_similar_tracks(self):
        """Merge các tracks có pose rất giống nhau (có thể là cùng 1 người)"""
        if not self.merge_similar_tracks or len(self.tracks) < 2:
            return
        
        track_ids = list(self.tracks.keys())
        merged = set()
        
        for i, id1 in enumerate(track_ids):
            if id1 in merged:
                continue
            
            for id2 in track_ids[i+1:]:
                if id2 in merged:
                    continue
                
                # Tính pose similarity giữa 2 tracks
                similarity = self._calculate_pose_similarity(
                    self.tracks[id1].keypoints,
                    self.tracks[id2].keypoints
                )
                
                # Nếu rất giống nhau, merge track mới vào track cũ
                if similarity > self.merge_threshold:
                    # Giữ track có hits cao hơn (đáng tin cậy hơn)
                    if self.tracks[id1].hits >= self.tracks[id2].hits:
                        keep_id, remove_id = id1, id2
                    else:
                        keep_id, remove_id = id2, id1
                    
                    # Merge: cập nhật track giữ lại với thông tin từ track bị remove
                    self.tracks[keep_id].hits += self.tracks[remove_id].hits
                    self.tracks[keep_id].age = 0  # Reset age
                    
                    # Lưu mapping để trace sau này
                    self.merged_tracks[remove_id] = keep_id
                    
                    # Xóa track trùng
                    del self.tracks[remove_id]
                    merged.add(remove_id)
                    
                    print(f"  ⚠️  Merged track {remove_id} into {keep_id} (similarity: {similarity:.2f})")


class Track:
    """Đại diện cho một track (người) với Kalman filter"""
    
    def __init__(self, track_id: int, keypoints: np.ndarray, frame_id: int, use_kalman: bool = True):
        self.track_id = track_id
        
        # Đảm bảo keypoints là array 2D [17, 3]
        keypoints = np.asarray(keypoints)
        keypoints = np.atleast_2d(keypoints)
        
        # Nếu shape là (1, 51), reshape thành (17, 3)
        if keypoints.shape[0] == 1 and keypoints.shape[1] == 51:
            keypoints = keypoints.reshape(17, 3)
        
        self.keypoints = keypoints
        self.hits = 1  # Số lần được match
        self.age = 0  # Số frame không được match
        self.last_seen = frame_id
        self.use_kalman = use_kalman
        
        # Lưu lịch sử keypoints để dự đoán
        self.keypoints_history = [keypoints.copy()]
        self.max_history = 5
    
    def predict(self) -> np.ndarray:
        """Dự đoán vị trí keypoints cho frame tiếp theo"""
        if not self.use_kalman or len(self.keypoints_history) < 2:
            return self.keypoints
        
        # Simple linear prediction dựa trên velocity
        recent_kpts = np.array(self.keypoints_history[-2:])
        velocity = recent_kpts[-1] - recent_kpts[-2]
        predicted = recent_kpts[-1] + velocity * 0.8  # Damping factor
        
        return predicted
    
    def update(self, keypoints: np.ndarray, frame_id: int):
        """Update track với keypoints mới"""
        # Đảm bảo keypoints là array 2D
        keypoints = np.asarray(keypoints)
        keypoints = np.atleast_2d(keypoints)
        
        # Nếu shape là (1, 51), reshape thành (17, 3)
        if keypoints.shape[0] == 1 and keypoints.shape[1] == 51:
            keypoints = keypoints.reshape(17, 3)
        
        # Smooth update: kết hợp predicted và measured
        if self.use_kalman and len(self.keypoints_history) >= 2:
            predicted = self.predict()
            # Weighted average (70% measured, 30% predicted)
            self.keypoints = 0.7 * keypoints + 0.3 * predicted
        else:
            self.keypoints = keypoints
        
        self.hits += 1
        self.age = 0
        self.last_seen = frame_id
        
        # Cập nhật history
        self.keypoints_history.append(self.keypoints.copy())
        if len(self.keypoints_history) > self.max_history:
            self.keypoints_history.pop(0)


def track_people_in_video(
    skeletons_per_frame: List[List[np.ndarray]]
) -> Dict[int, Dict]:
    """
    Track nhiều người qua các frame với enhanced tracking
    
    Args:
        skeletons_per_frame: List các frame, mỗi frame là list keypoints
        
    Returns:
        Dict {person_id: {
            'keypoints': [keypoints_frame0, keypoints_frame1, ...],
            'frame_indices': [frame_idx0, frame_idx1, ...]
        }}
    """
    tracker = SimpleTracker()
    
    tracked_people = defaultdict(list)
    frame_presence = defaultdict(list)  # Track frame indices where person appears
    
    for frame_idx, detections in enumerate(skeletons_per_frame):
        confirmed_tracks = tracker.update(detections)
        
        # Thêm keypoints và frame index vào track tương ứng
        for person_id, keypoints in confirmed_tracks.items():
            tracked_people[person_id].append(keypoints)
            frame_presence[person_id].append(frame_idx)
    
    # Lọc ra những người xuất hiện đủ lâu (ít nhất 2% số frame hoặc tối thiểu 10 frames)
    min_frames = max(10, len(skeletons_per_frame) * 0.02)
    
    # Chuyển list thành numpy array cho mỗi người và thêm frame indices
    result = {}
    for person_id, keypoints_list in tracked_people.items():
        if len(keypoints_list) >= min_frames:
            result[person_id] = {
                'keypoints': np.array(keypoints_list),
                'frame_indices': np.array(frame_presence[person_id])
            }
        else:
            print(f"  Bỏ qua person {person_id}: chỉ xuất hiện {len(keypoints_list)} frames (< {min_frames})")
    
    # Nếu chỉ có 1 người trong video, chỉ giữ track dài nhất
    if len(result) > 1:
        print(f"\n⚠️  Phát hiện {len(result)} tracks, kiểm tra xem có phải cùng 1 người không...")
        
        # Tìm track dài nhất
        longest_track_id = max(result.keys(), key=lambda pid: len(result[pid]['keypoints']))
        longest_track_len = len(result[longest_track_id]['keypoints'])
        
        # Merge các tracks tương tự vào track dài nhất
        merged_result = {longest_track_id: result[longest_track_id]}
        
        for person_id in result.keys():
            if person_id == longest_track_id:
                continue
            
            # So sánh với track dài nhất
            # Nếu overlap về thời gian < 20%, có thể là cùng người nhưng bị mất tracking
            frames1 = set(result[longest_track_id]['frame_indices'])
            frames2 = set(result[person_id]['frame_indices'])
            overlap = len(frames1 & frames2) / len(frames1 | frames2)
            
            if overlap < 0.2:  # Ít overlap = có thể cùng người
                print(f"  → Có thể track {person_id} và {longest_track_id} là cùng người (overlap: {overlap:.1%})")
                print(f"    Chỉ giữ track dài nhất: {longest_track_id} ({longest_track_len} frames)")
            else:
                print(f"  → Track {person_id} overlap {overlap:.1%} với {longest_track_id}, có thể là người khác")
        
        # Nếu tổng frames của tất cả tracks ~ tổng frames video, chỉ giữ track dài nhất
        total_tracked_frames = sum(len(result[pid]['keypoints']) for pid in result)
        if total_tracked_frames < len(skeletons_per_frame) * 1.5:  # Không quá 150% => khả năng cao là 1 người
            print(f"\n  ✅ Chỉ giữ track dài nhất (khả năng cao chỉ có 1 người trong video)")
            result = merged_result
    
    return result

