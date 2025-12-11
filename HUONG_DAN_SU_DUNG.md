# Hướng dẫn sử dụng Script Chấm Điểm Video

Script đơn giản để chấm điểm video điều lệnh, không cần Docker, không cần đăng nhập.

## Cài đặt

```bash
pip install -r backend/requirements.txt
```

## Sử dụng

### 1. Tạo Golden Template (Video mẫu)

Phân tích video mẫu để tạo golden template:

```bash
python score_video.py create_golden "data/golden_template/golden_video.mp4"
```

Hoặc chỉ định thư mục output:

```bash
python score_video.py create_golden "path/to/golden_video.mp4" --output-dir "data/golden_template"
```

**Kết quả:**
- `data/golden_template/golden_profile.json` - Profile chứa thống kê đặc trưng
- `data/golden_template/golden_skeleton.pkl` - Keypoints của video golden

### 2. Đánh giá Video Test

So sánh video test với golden template và chấm điểm:

```bash
python score_video.py evaluate "data/input_videos/video1.mp4"
```

Hoặc chỉ định thư mục golden template:

```bash
python score_video.py evaluate "path/to/test_video.mp4" --golden-dir "data/golden_template"
```

**Kết quả:**
- `data/output/<video_name>/evaluation_result.json` - Kết quả đánh giá chi tiết
- In ra console: Điểm số, số lỗi, kết quả đạt/trượt

## Ví dụ

### Bước 1: Tạo Golden Template

```bash
python score_video.py create_golden "data/golden_template/golden_video.mp4"
```

Output:
```
📹 Đang xử lý video golden: data/golden_template/golden_video.mp4
   FPS: 30.0, Kích thước: 1920x1080
   Đang phân tích từng frame...
   Đã xử lý 30 frames...
   ...
✅ Đã phân tích 450/500 frames hợp lệ
✅ Đã lưu golden profile: data/golden_template/golden_profile.json
✅ Đã lưu golden skeleton: data/golden_template/golden_skeleton.pkl
```

### Bước 2: Đánh giá Video Test

```bash
python score_video.py evaluate "data/input_videos/video1.mp4"
```

Output:
```
📹 Đang đánh giá video test: data/input_videos/video1.mp4
   FPS: 30.0, Kích thước: 1920x1080
✅ Đã load golden template
   Đang phân tích từng frame...
   Đã xử lý 30 frames, phát hiện 5 lỗi...
   ...
✅ Đã phân tích 480/500 frames hợp lệ
   Tổng số lỗi phát hiện: 23
✅ Đã lưu kết quả: data/output/video1/evaluation_result.json

============================================================
KẾT QUẢ ĐÁNH GIÁ
============================================================
Video: video1.mp4
Điểm ban đầu: 100.00
Tổng điểm trừ: 15.50
Điểm cuối: 84.50
Kết quả: ✅ ĐẠT

Tổng số lỗi: 23

Lỗi theo loại:
  - arm_angle: 8
  - leg_angle: 5
  - head_angle: 3
  - torso_stability: 7
============================================================
```

## Cấu trúc dữ liệu

### Golden Profile (`golden_profile.json`)

```json
{
  "video_path": "data/golden_template/golden_video.mp4",
  "metadata": {
    "fps": 30.0,
    "width": 1920,
    "height": 1080,
    "frame_count": 500,
    "duration": 16.67
  },
  "statistics": {
    "arm_angle": {
      "left": {
        "mean": 165.2,
        "std": 3.5,
        "min": 158.0,
        "max": 172.0,
        "count": 450
      },
      "right": { ... }
    },
    "leg_angle": { ... },
    ...
  },
  "total_frames": 500,
  "valid_frames": 450
}
```

### Evaluation Result (`evaluation_result.json`)

```json
{
  "video_path": "data/input_videos/video1.mp4",
  "metadata": { ... },
  "total_frames": 500,
  "valid_frames": 480,
  "initial_score": 100.0,
  "total_deduction": 15.5,
  "final_score": 84.5,
  "is_passed": true,
  "total_errors": 23,
  "errors_by_type": {
    "arm_angle": 8,
    "leg_angle": 5,
    "head_angle": 3,
    "torso_stability": 7
  }
}
```

## Lưu ý

1. **Video format**: Hỗ trợ `.mp4`, `.avi`, `.mov`, `.mkv`
2. **Độ phân giải**: Tối thiểu 720p (1280x720 hoặc 1080x720 cho video dọc)
3. **FPS**: Khuyến nghị >= 24fps
4. **Golden template**: Phải tạo golden template trước khi đánh giá video test
5. **Model**: YOLOv8-Pose sẽ tự động download lần đầu (có thể mất vài phút)

## Troubleshooting

### Lỗi: "Không tìm thấy người nào trong video"
- Kiểm tra video có người rõ ràng không
- Thử video khác hoặc điều chỉnh góc quay

### Lỗi: "Không tìm thấy golden profile"
- Chạy `create_golden` trước
- Kiểm tra file `data/golden_template/golden_profile.json` có tồn tại không

### Lỗi: Model download chậm
- Lần đầu chạy sẽ download YOLOv8 model (~6-22MB)
- Có thể tải thủ công và đặt vào `data/models/`

