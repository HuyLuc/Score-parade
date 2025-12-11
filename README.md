# Score Parade - Hệ thống chấm điều lệnh tự động

Hệ thống AI để đánh giá và chấm điểm động tác điều lệnh quân đội từ video.

## ✨ Tính năng

- ✅ **Phát hiện pose tự động**: Sử dụng YOLOv8-Pose để phát hiện keypoints
- ✅ **Tạo Golden Template**: Phân tích video mẫu để tạo profile chuẩn
- ✅ **Đánh giá tự động**: So sánh video test với golden template
- ✅ **Phát hiện lỗi**: Tự động phát hiện lỗi tư thế (góc tay, chân, đầu, ổn định thân)
- ✅ **Tính điểm**: Tính điểm tự động dựa trên số lỗi và mức độ nghiêm trọng
- ✅ **Xuất kết quả**: Lưu kết quả chi tiết dưới dạng JSON

## 📁 Cấu trúc dự án

```
Score-parade/
├── backend/                    # Backend services và AI
│   └── app/
│       ├── controllers/        # AI controller (phát hiện lỗi)
│       │   └── ai_controller.py
│       ├── services/           # Core services
│       │   ├── pose_service.py          # Pose estimation service
│       │   ├── pose_estimation.py       # YOLOv8 pose model
│       │   ├── video_utils.py           # Xử lý video
│       │   ├── geometry.py              # Tính toán góc, khoảng cách
│       │   └── scoring_service.py       # Logic chấm điểm
│       └── config.py           # Cấu hình
├── data/                       # Dữ liệu
│   ├── golden_template/        # Video mẫu và profile
│   │   ├── golden_video.mp4
│   │   ├── golden_profile.json
│   │   └── golden_skeleton.pkl
│   ├── input_videos/           # Video cần chấm
│   ├── output/                 # Kết quả chấm điểm
│   └── models/                 # YOLOv8 models (tự động download)
├── score_video.py              # Script chính (tạo golden + đánh giá)
├── run_scoring.py              # Script đơn giản để chạy
├── backend/requirements.txt    # Dependencies
└── README.md                   # File này
```

## 🚀 Cài đặt

### Yêu cầu

- Python 3.8+
- CUDA (tùy chọn, cho GPU acceleration)

### Cài đặt dependencies

```bash
pip install -r backend/requirements.txt
```

**Lưu ý**: YOLOv8-Pose model sẽ tự động download lần đầu chạy (có thể mất vài phút, ~6-22MB).

## 📖 Sử dụng

### Bước 1: Tạo Golden Template (Video mẫu)

Phân tích video mẫu để tạo golden template:

```bash
python run_scoring.py create_golden "data/golden_template/golden_video.mp4"
```

**Kết quả:**
- `data/golden_template/golden_profile.json` - Profile chứa thống kê đặc trưng (mean, std, min, max)
- `data/golden_template/golden_skeleton.pkl` - Keypoints của video golden

### Bước 2: Đánh giá Video Test

So sánh video test với golden template và chấm điểm:

```bash
python run_scoring.py evaluate "data/input_videos/video1.mp4"
```

**Kết quả:**
- `data/output/<video_name>/evaluation_result.json` - Kết quả đánh giá chi tiết
- In ra console: Điểm số, số lỗi, kết quả đạt/trượt

## 📝 Ví dụ

```bash
# Tạo golden template
python run_scoring.py create_golden "data/golden_template/golden_video.mp4"

# Đánh giá video test
python run_scoring.py evaluate "data/input_videos/video1.mp4"
```

### Output mẫu

**Khi tạo Golden Template:**
```
============================================================
TAO GOLDEN TEMPLATE
============================================================
📹 Đang xử lý video golden: data/golden_template/golden_video.mp4
   FPS: 30.0, Kích thước: 1280x720
✅ Đã phân tích 47/47 frames hợp lệ
✅ Đã lưu golden profile: data/golden_template/golden_profile.json
✅ Đã lưu golden skeleton: data/golden_template/golden_skeleton.pkl
```

**Khi đánh giá Video Test:**
```
============================================================
DANH GIA VIDEO TEST
============================================================
📹 Đang đánh giá video test: data/input_videos/video1.mp4
✅ Đã load golden template
✅ Đã phân tích 53/53 frames hợp lệ
   Tổng số lỗi phát hiện: 109

============================================================
KẾT QUẢ ĐÁNH GIÁ
============================================================
Video: video1.mp4
Điểm ban đầu: 100.00
Tổng điểm trừ: 363.49
Điểm cuối: 0.00
Kết quả: ❌ TRƯỢT

Tổng số lỗi: 109
Lỗi theo loại:
  - arm_angle: 6
  - head_angle: 53
  - leg_angle: 1
============================================================
```

## 🔧 Cấu hình

Các tham số có thể điều chỉnh trong `backend/app/config.py`:

- **SCORING_CONFIG**: Điểm ban đầu, ngưỡng đạt, trọng số lỗi
- **ERROR_THRESHOLDS**: Ngưỡng sai lệch mặc định cho từng loại lỗi
- **POSE_CONFIG**: Cấu hình model pose estimation (YOLOv8)

## 📊 Các loại lỗi được phát hiện

1. **arm_angle**: Góc tay (trái/phải) - so sánh với golden template
2. **leg_angle**: Góc chân (trái/phải) - so sánh với golden template
3. **arm_height**: Độ cao tay (trái/phải)
4. **leg_height**: Độ cao chân (trái/phải)
5. **head_angle**: Góc đầu (cúi/ngửa)
6. **torso_stability**: Ổn định thân (variance vị trí hông)

## ⚠️ Lưu ý

1. **Phải tạo golden template trước** khi đánh giá video test
2. **Video format**: Hỗ trợ `.mp4`, `.avi`, `.mov`, `.mkv`
3. **Độ phân giải**: Tối thiểu 720p (1280x720)
4. **FPS**: Khuyến nghị >= 24fps
5. **Model**: YOLOv8-Pose sẽ tự động download lần đầu (có thể mất vài phút)
6. **GPU**: Nếu có CUDA, model sẽ tự động sử dụng GPU để tăng tốc

## 🐛 Troubleshooting

### Lỗi: "Không tìm thấy người nào trong video"
- Kiểm tra video có người rõ ràng không
- Thử video khác hoặc điều chỉnh góc quay
- Kiểm tra độ sáng và độ tương phản của video

### Lỗi: "Không tìm thấy golden profile"
- Chạy `create_golden` trước
- Kiểm tra file `data/golden_template/golden_profile.json` có tồn tại không

### Lỗi: Model download chậm
- Lần đầu chạy sẽ download YOLOv8 model (~6-22MB)
- Có thể tải thủ công và đặt vào `data/models/`

### Lỗi encoding trên Windows
- Script đã tự động fix encoding
- Nếu vẫn lỗi, chạy trong PowerShell hoặc CMD với UTF-8

## 📚 Tài liệu

- [QUICK_START.md](QUICK_START.md) - Hướng dẫn nhanh
- [HUONG_DAN_SU_DUNG.md](HUONG_DAN_SU_DUNG.md) - Hướng dẫn chi tiết
- [docs/DEMO_GLOBAL_MODE.md](docs/DEMO_GLOBAL_MODE.md) - Demo script cho Global Mode API

## 🧪 Demo Global Mode API

Để test workflow của Global Mode API (testing/practising mode):

```bash
# 1. Start backend server
cd backend
python -m uvicorn app.main:app --reload

# 2. Run demo script (trong terminal khác)
python demo_global_mode.py
```

Demo script sẽ:
- ✅ Khởi tạo session (testing/practising mode)
- ✅ Load và xử lý video từng frame
- ✅ Hiển thị real-time: motion events, errors, score
- ✅ Stop tự động khi score < 50 (testing mode)
- ✅ Hiển thị summary cuối cùng
- ✅ Cleanup session

Chi tiết: [docs/DEMO_GLOBAL_MODE.md](docs/DEMO_GLOBAL_MODE.md)

## 🔬 Cách hoạt động

1. **Pose Detection**: Sử dụng YOLOv8-Pose để phát hiện 17 keypoints (COCO format)
2. **Feature Extraction**: Tính toán các đặc trưng từ keypoints:
   - Góc tay, chân, đầu
   - Độ cao tay, chân
   - Ổn định thân (variance)
3. **Golden Template**: Lưu thống kê (mean, std) của các đặc trưng từ video mẫu
4. **Comparison**: So sánh video test với golden template, phát hiện lỗi khi vượt ngưỡng
5. **Scoring**: Tính điểm dựa trên số lỗi và mức độ nghiêm trọng

## 📄 License

Dự án này được phát triển cho mục đích giáo dục và nghiên cứu.
