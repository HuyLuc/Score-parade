# Hướng dẫn nhanh

## ✅ Đã cài đặt thành công

Các package chính đã được cài đặt:
- ✅ ultralytics (YOLOv8-Pose)
- ✅ dtw-python
- ✅ filterpy
- ✅ Các dependencies khác

## Bước tiếp theo

### 1. Kiểm tra cài đặt

```bash
python -c "from ultralytics import YOLO; print('YOLOv8-Pose OK')"
python -c "import dtw; print('DTW OK')"
```

### 2. Chuẩn bị video mẫu chuẩn (Golden Template)

**Công việc thủ công:**
1. Quay/chuẩn bị video mẫu chuẩn:
   - 1 người hoặc nhóm nhỏ thực hiện điều lệnh hoàn hảo
   - Độ phân giải: 720p trở lên (1280x720)
   - Frame rate: 30fps trở lên
   - Điều kiện: Ánh sáng tốt, góc quay rõ ràng
   - Độ dài: Ít nhất 1 chu kỳ điều lệnh hoàn chỉnh (10-30 giây)

2. Lưu video vào:
   ```
   data/golden_template/golden_video.mp4
   ```

### 3. Chạy Bước 1-2 (Tạo Golden Template)

```bash
# Bước 1: Trích xuất skeleton từ video mẫu
python main.py --mode step1 --golden-video data/golden_template/golden_video.mp4

# Bước 2: Trích xuất đặc điểm hình học
python main.py --mode step2
```

**Lưu ý:** Bước 1-2 chỉ cần chạy 1 lần để tạo golden template.

### 4. Xử lý video mới

1. Đặt video cần đánh giá vào:
   ```
   data/input_videos/video1.mp4
   ```

2. Chạy toàn bộ pipeline:
   ```bash
   python main.py --mode full --input-video data/input_videos/video1.mp4
   ```

   Hoặc chạy từng bước:
   ```bash
   # Bước 3: Xử lý video
   python main.py --mode step3 --input-video data/input_videos/video1.mp4
   
   # Bước 4-7: Xử lý từng người (thay video1 và 0 bằng tên video và ID người thực tế)
   python main.py --mode step4 --video-name video1 --person-id 0
   python main.py --mode step5 --video-name video1 --person-id 0
   python main.py --mode step6 --video-name video1 --person-id 0
   python main.py --mode step7 --input-video data/input_videos/video1.mp4 --video-name video1 --person-id 0
   ```

### 5. Xem kết quả

Sau khi chạy xong, kết quả sẽ ở:
```
data/output/{video_name}/
├── person_0_annotated.mp4    # Video với annotations
├── person_0_report.html       # Báo cáo HTML
├── person_0_report.json      # Báo cáo JSON
└── person_0_score.json       # Điểm số
```

## Lưu ý quan trọng

1. **Model mặc định:** Hệ thống đang dùng YOLOv8-Pose (đơn giản, ổn định)
2. **Nếu muốn dùng RTMPose:** Cần cài đặt thủ công:
   ```bash
   pip install mmpose mmcv-full mmengine
   ```
   Sau đó sửa `src/config.py`: `"model_type": "rtmpose"`

3. **Numpy version:** Có cảnh báo về numpy 2.x với faiss-cpu, nhưng không ảnh hưởng đến dự án này.

## Troubleshooting

### Lỗi "No module named 'src'"
```bash
# Đảm bảo đang ở thư mục gốc của dự án
cd F:\Score-parade\Score-parade
python main.py ...
```

### Lỗi import YOLO
```bash
pip install --upgrade ultralytics
```

### Video không detect được người
- Kiểm tra chất lượng video (độ phân giải, ánh sáng)
- Thử model lớn hơn: sửa `src/config.py` → `"yolov8_model": "yolov8s-pose.pt"` (s=small, m=medium)

