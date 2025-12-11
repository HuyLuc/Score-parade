# Hướng dẫn nhanh - Chấm điểm video điều lệnh

## Yêu cầu
- Python 3.8+
- Đã cài đặt dependencies: `pip install -r backend/requirements.txt`

## Luồng chính

### Bước 1: Tạo Golden Template (Video mẫu)

Phân tích video mẫu để tạo golden template:

```bash
python run_scoring.py create_golden "data/golden_template/golden_video.mp4"
```

**Kết quả:**
- `data/golden_template/golden_profile.json` - Profile chứa thống kê đặc trưng
- `data/golden_template/golden_skeleton.pkl` - Keypoints của video golden

### Bước 2: Đánh giá Video Test

So sánh video test với golden template và chấm điểm:

```bash
python run_scoring.py evaluate "data/input_videos/video1.mp4"
```

**Kết quả:**
- `data/output/<video_name>/evaluation_result.json` - Kết quả đánh giá chi tiết
- In ra console: Điểm số, số lỗi, kết quả đạt/trượt

## Ví dụ đầy đủ

```bash
# Bước 1: Tạo golden template
python run_scoring.py create_golden "data/golden_template/golden_video.mp4"

# Bước 2: Đánh giá video test
python run_scoring.py evaluate "data/input_videos/video1.mp4"
```

## Output mẫu

### Khi tạo Golden Template:
```
============================================================
TAO GOLDEN TEMPLATE
============================================================
📹 Đang xử lý video golden: data/golden_template/golden_video.mp4
   FPS: 30.0, Kích thước: 1920x1080
   Đang phân tích từng frame...
   Đã xử lý 30 frames...
   ...
✅ Đã phân tích 450/500 frames hợp lệ
✅ Đã lưu golden profile: data/golden_template/golden_profile.json
✅ Đã lưu golden skeleton: data/golden_template/golden_skeleton.pkl

✅ Hoàn tất!
```

### Khi đánh giá Video Test:
```
============================================================
DANH GIA VIDEO TEST
============================================================
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

✅ Hoàn tất!
```

## Lưu ý

1. **Phải tạo golden template trước** khi đánh giá video test
2. **Video format**: Hỗ trợ `.mp4`, `.avi`, `.mov`, `.mkv`
3. **Độ phân giải**: Tối thiểu 720p
4. **FPS**: Khuyến nghị >= 24fps
5. **Model**: YOLOv8-Pose sẽ tự động download lần đầu (có thể mất vài phút)

## Troubleshooting

### Lỗi: "Không tìm thấy người nào trong video"
- Kiểm tra video có người rõ ràng không
- Thử video khác hoặc điều chỉnh góc quay

### Lỗi: "Không tìm thấy golden profile"
- Chạy `create_golden` trước
- Kiểm tra file `data/golden_template/golden_profile.json` có tồn tại không

### Lỗi encoding trên Windows
- Script đã tự động fix encoding, nếu vẫn lỗi, chạy trong PowerShell hoặc CMD với UTF-8

