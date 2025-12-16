from typing import List, Tuple, Dict

import numpy as np
from scipy.optimize import linear_sum_assignment


class Detection:
    """Một detection trong 1 frame (bbox + score + keypoints)."""

    def __init__(self, bbox: Tuple[float, float, float, float], score: float, keypoints: np.ndarray):
        self.bbox = bbox  # (x1,y1,x2,y2)
        self.score = score
        self.keypoints = keypoints


class TrackResult:
    """Kết quả tracking cho 1 frame (track_id ổn định + bbox + keypoints)."""

    def __init__(self, track_id: int, bbox: Tuple[float, float, float, float], keypoints: np.ndarray):
        self.track_id = track_id
        self.bbox = bbox
        self.keypoints = keypoints


class TrackerService:
    """
    Tracker đa đối tượng đơn giản theo phong cách SORT/ByteTrack (dùng IoU + Hungarian).

    Mục tiêu: gán ID ổn định cho từng người dựa trên bbox giữa các frame,
    để backend biết trong video có bao nhiêu người và chấm điểm riêng từng người.
    """

    def __init__(self, max_disappeared: int = 30, iou_threshold: float = 0.3):
        # Tham số kiểm soát vòng đời track
        self.max_disappeared = max_disappeared
        self.iou_threshold = iou_threshold

        # Trạng thái tracking
        self.next_track_id: int = 0
        # {track_id: {"bbox": np.ndarray[4], "frame_num": int}}
        self.tracks: Dict[int, Dict] = {}
        # {track_id: disappeared_count}
        self.disappeared: Dict[int, int] = {}
        # Thống kê toàn video cho từng track_id
        # {track_id: {"frames_seen": int, "first_frame": int, "last_frame": int, "total_height": float}}
        self.stats: Dict[int, Dict] = {}

    # ============== API chính ==============

    def update(self, detections: List[Detection], frame_num: int) -> List[TrackResult]:
        """
        Nhận danh sách detection trong 1 frame, trả lại danh sách track với track_id ổn định.
        """
        # 0. Không có detection mới
        if len(detections) == 0:
            self._increment_disappeared()
            return []

        det_bboxes = np.array([d.bbox for d in detections], dtype=np.float32)

        # 1. Nếu chưa có track nào → tạo mới toàn bộ
        if len(self.tracks) == 0:
            for i, det in enumerate(detections):
                self._register(det.bbox, frame_num)
            return [
                TrackResult(track_id=tid, bbox=track["bbox"].tolist(), keypoints=det.keypoints)
                for tid, track, det in zip(self.tracks.keys(), self.tracks.values(), detections)
            ]

        # 2. Có track và detection → ghép bằng Hungarian trên cost = 1 - IoU
        track_ids = list(self.tracks.keys())
        track_bboxes = np.array([self.tracks[tid]["bbox"] for tid in track_ids], dtype=np.float32)

        cost_matrix = self._compute_cost_matrix(det_bboxes, track_bboxes)
        row_idx, col_idx = linear_sum_assignment(cost_matrix)

        matched_tracks = set()
        matched_dets = set()

        for r, c in zip(row_idx, col_idx):
            iou = 1.0 - cost_matrix[r, c]
            if iou < self.iou_threshold:
                continue

            det = detections[r]
            track_id = track_ids[c]

            # Cập nhật track với bbox mới
            self.tracks[track_id]["bbox"] = np.array(det.bbox, dtype=np.float32)
            self.tracks[track_id]["frame_num"] = frame_num
            self.disappeared[track_id] = 0

            self._update_stats(track_id, det.bbox, frame_num)

            matched_tracks.add(track_id)
            matched_dets.add(r)

        # 3. Tăng disappeared cho track không match
        for tid in track_ids:
            if tid not in matched_tracks:
                self.disappeared[tid] += 1
                if self.disappeared[tid] > self.max_disappeared:
                    self._deregister(tid)

        # 4. Tạo track mới cho detection chưa match
        for i, det in enumerate(detections):
            if i in matched_dets:
                continue
            self._register(det.bbox, frame_num)

        # 5. Trả lại kết quả cho frame hiện tại
        results: List[TrackResult] = []
        for tid, track in self.tracks.items():
            # Tìm detection gần nhất với track này trong frame hiện tại để lấy keypoints
            # (đơn giản: chọn detection có IoU cao nhất với bbox của track)
            best_kpts = None
            best_iou = 0.0
            for det in detections:
                iou = self._calculate_iou(np.array(det.bbox, dtype=np.float32), track["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_kpts = det.keypoints
            if best_kpts is not None:
                results.append(TrackResult(track_id=tid, bbox=tuple(track["bbox"].tolist()), keypoints=best_kpts))

        return results

    # ============== Hàm truy vấn thống kê ==============

    def get_stable_track_ids(
        self,
        min_frames: int = 30,
        min_height: float = 50.0,
        min_frame_ratio: float = 0.9,
    ) -> List[int]:
        """
        Lấy danh sách track_id được coi là "người thật" trong video.

        - Bỏ các track quá ngắn (frames_seen < min_frames).
        - Bỏ các track có bbox trung bình quá nhỏ (min_height).
        - Chỉ giữ track có frames_seen >= min_frame_ratio * max_frames_seen
          (số frame xuất hiện xấp xỉ nhau giữa các người thật).
        """
        candidates: List[Tuple[int, int, float]] = []
        for tid, stat in self.stats.items():
            frames_seen = int(stat.get("frames_seen", 0))
            total_height = float(stat.get("total_height", 0.0))
            if frames_seen < min_frames:
                continue
            avg_height = total_height / max(frames_seen, 1)
            if avg_height < min_height:
                continue
            candidates.append((tid, frames_seen, avg_height))

        if not candidates:
            return []

        max_frames_seen = max(frames_seen for _, frames_seen, _ in candidates)
        if max_frames_seen <= 0:
            return []

        threshold = max_frames_seen * float(min_frame_ratio)

        stable_ids: List[int] = []
        for tid, frames_seen, _ in candidates:
            if frames_seen >= threshold:
                stable_ids.append(tid)

        return sorted(stable_ids)

    # ============== Hỗ trợ nội bộ ==============

    def _register(self, bbox: Tuple[float, float, float, float], frame_num: int):
        track_id = self.next_track_id
        self.next_track_id += 1

        self.tracks[track_id] = {
            "bbox": np.array(bbox, dtype=np.float32),
            "frame_num": frame_num,
        }
        self.disappeared[track_id] = 0

        # Khởi tạo stats
        x1, y1, x2, y2 = bbox
        height = max(y2 - y1, 0.0)
        self.stats[track_id] = {
            "frames_seen": 1,
            "first_frame": frame_num,
            "last_frame": frame_num,
            "total_height": float(height),
        }

    def _deregister(self, track_id: int):
        if track_id in self.tracks:
            del self.tracks[track_id]
        if track_id in self.disappeared:
            del self.disappeared[track_id]
        # Giữ lại self.stats để có thể dùng thống kê toàn video

    def _increment_disappeared(self):
        """Tăng disappeared cho tất cả track khi không có detection mới."""
        for tid in list(self.tracks.keys()):
            self.disappeared[tid] += 1
            if self.disappeared[tid] > self.max_disappeared:
                self._deregister(tid)

    def _update_stats(self, track_id: int, bbox: Tuple[float, float, float, float], frame_num: int):
        x1, y1, x2, y2 = bbox
        height = max(y2 - y1, 0.0)

        if track_id not in self.stats:
            self.stats[track_id] = {
                "frames_seen": 0,
                "first_frame": frame_num,
                "last_frame": frame_num,
                "total_height": 0.0,
            }

        stat = self.stats[track_id]
        stat["frames_seen"] += 1
        stat["last_frame"] = frame_num
        stat["total_height"] += float(height)

    @staticmethod
    def _calculate_iou(bbox1: np.ndarray, bbox2: np.ndarray) -> float:
        """
        Tính IoU giữa 2 bbox [x1,y1,x2,y2].
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i < x1_i or y2_i < y1_i:
            return 0.0

        inter = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - inter

        if union <= 0:
            return 0.0

        return float(inter / union)

    @staticmethod
    def _compute_cost_matrix(dets: np.ndarray, tracks: np.ndarray) -> np.ndarray:
        """
        Cost = 1 - IoU giữa từng detection và track.
        """
        num_dets = dets.shape[0]
        num_tracks = tracks.shape[0]
        cost = np.ones((num_dets, num_tracks), dtype=np.float32)

        for i in range(num_dets):
            for j in range(num_tracks):
                cost[i, j] = 1.0 - TrackerService._calculate_iou(dets[i], tracks[j])

        return cost