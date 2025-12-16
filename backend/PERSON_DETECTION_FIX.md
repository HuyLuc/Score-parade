# Sửa lỗi phát hiện số người trong video

## Vấn đề đã phát hiện

Hệ thống không nhận diện đúng số người trong video do các lỗi sau:

1. **Tracker không được khởi tạo và cập nhật đúng cách**
   - `tracker` legacy trong `GlobalController` được khai báo nhưng luôn là `None`
   - Chỉ có `tracker_service` được tạo nhưng không có fallback cho `tracker`
   - Dẫn đến không có thống kê để xác định số người thật

2. **Config quá chặt chẽ**
   - `conf_threshold` = 0.25 quá cao
   - `keypoint_confidence_threshold` = 0.3 quá cao
   - `min_valid_keypoints` = 6 quá nhiều
   - `max_persons` = 3 quá ít

3. **Logic detection không tối ưu**
   - Chỉ dựa vào confidence, không xét đến kích thước người
   - Không xử lý trường hợp người ở xa camera (confidence thấp hơn)

## Các thay đổi đã thực hiện

### 1. GlobalController (backend/app/controllers/global_controller.py)

#### Khởi tạo tracker đúng cách:
```python
if self.multi_person_enabled:
    # Khởi tạo cả hai tracker để đảm bảo tương thích
    self.tracker = PersonTracker(
        max_disappeared=MULTI_PERSON_CONFIG.get("max_disappeared", 30),
        iou_threshold=MULTI_PERSON_CONFIG.get("iou_threshold", 0.3),
        enable_reid=False
    )
    self.tracker_service = TrackerService(
        max_disappeared=MULTI_PERSON_CONFIG.get("max_disappeared", 30),
        iou_threshold=MULTI_PERSON_CONFIG.get("iou_threshold", 0.3),
    )
```

#### Cập nhật cả hai tracker trong process_frame:
```python
# Update tracker_service
if self.tracker_service:
    tracks = self.tracker_service.update(detections_for_tracker, frame_number)
    for tr in tracks:
        persons[tr.track_id] = tr.keypoints

# Update legacy tracker để có thống kê
if self.tracker and len(keypoints_list) > 0:
    self.tracker.update(keypoints_list, frame_number)
```

#### Cải thiện logic lấy stable_person_ids:
- Giảm `min_frame_ratio` từ 0.9 xuống 0.85 để linh hoạt hơn
- Thêm fallback giữa tracker_service và tracker legacy
- Thêm error handling và logging chi tiết

### 2. Config (backend/app/config.py)

#### Giảm ngưỡng phát hiện:
```python
POSE_CONFIG = {
    "conf_threshold": 0.20,  # Giảm từ 0.25 xuống 0.20
    "keypoint_confidence_threshold": 0.25,  # Giảm từ 0.3 xuống 0.25
    "min_valid_keypoints": 5,  # Giảm từ 6 xuống 5
}
```

#### Tăng max_persons và điều chỉnh tracking:
```python
MULTI_PERSON_CONFIG = {
    "max_persons": 5,  # Tăng từ 3 lên 5
    "max_disappeared": 60,  # Giảm từ 90 xuống 60 (~2s @30fps)
    "iou_threshold": 0.25,  # Giảm từ 0.3 xuống 0.25
}
```

### 3. Pose Estimation (backend/app/services/pose_estimation.py)

#### Cải thiện scoring trong _predict_yolov8:
```python
# Tính score combination của confidence và size
x1, y1, x2, y2 = boxes[i, :4]
bbox_area = (x2 - x1) * (y2 - y1)
# 70% confidence + 30% size
score = float(box_conf) * 0.7 + (bbox_area / (frame.shape[0] * frame.shape[1])) * 0.3
candidates.append((score, kpts))
```

### 4. Scripts test

#### Test phát hiện người (backend/tests/test_person_detection.py):
```bash
python backend/tests/test_person_detection.py <video_path>
```

Hiển thị:
- Số người phát hiện trung bình/tối đa/tối thiểu mỗi frame
- Số track trung bình/tối đa
- Danh sách stable person IDs (người thật)
- Thống kê chi tiết cho từng người (frames seen, height, etc.)

#### Debug YOLOv8 (backend/tests/debug_yolov8.py):
```bash
python backend/tests/debug_yolov8.py <video_path> [num_frames]
```

Hiển thị:
- Số người phát hiện mỗi 10 frames
- Chi tiết keypoints và confidence cho mỗi người
- Distribution của số người qua các frame

## Cách sử dụng

### 1. Kiểm tra cấu hình
Mở `backend/app/config.py` và xem lại:
- `POSE_CONFIG`: Các ngưỡng phát hiện
- `MULTI_PERSON_CONFIG`: Cấu hình tracking

### 2. Test với video của bạn

```bash
# Test detection cơ bản
cd backend/tests
python debug_yolov8.py ../../data/input_videos/your_video.mp4 100

# Test tracking đầy đủ
python test_person_detection.py ../../data/input_videos/your_video.mp4
```

### 3. Điều chỉnh nếu cần

Nếu vẫn không phát hiện đúng số người, có thể điều chỉnh:

**Phát hiện quá nhiều người (false positives):**
- Tăng `conf_threshold` lên 0.25 hoặc 0.30
- Tăng `min_valid_keypoints` lên 6 hoặc 7
- Tăng `min_frame_ratio` trong `get_stable_track_ids` lên 0.90

**Phát hiện quá ít người (false negatives):**
- Giảm `conf_threshold` xuống 0.15
- Giảm `min_valid_keypoints` xuống 4
- Giảm `min_frame_ratio` xuống 0.80
- Tăng `max_persons` lên 10

## Kết quả mong đợi

Sau các thay đổi này:
1. Hệ thống sẽ phát hiện đúng số người trong video
2. `stable_person_ids` sẽ chứa đúng danh sách người thật (không có ID ảo)
3. `total_persons` trong response sẽ chính xác
4. Mỗi người sẽ có score và errors riêng biệt

## Kiểm tra trong production

Sau khi triển khai, kiểm tra response từ API:

```json
{
  "success": true,
  "timestamp": 1.5,
  "frame_number": 45,
  "multi_person": true,
  "persons": [
    {
      "person_id": 0,
      "errors": [...],
      "score": 95.5
    },
    {
      "person_id": 1,
      "errors": [...],
      "score": 92.3
    }
  ],
  "person_ids": [0, 1],
  "stable_person_ids": [0, 1],
  "total_persons": 2
}
```

Nếu `stable_person_ids` không khớp với số người thật, xem lại config và thống kê từ script test.
