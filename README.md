# Hệ thống đánh giá điều lệnh quân đội

Hệ thống sử dụng Computer Vision để phân tích và chấm điểm động tác điều lệnh của từng cá nhân trong nhóm (6-20 người).

## Tổng quan

Hệ thống thực hiện 7 bước chính:

1. **Tạo video mẫu chuẩn (Golden Template)**: Trích xuất skeleton từ video điều lệnh hoàn hảo
2. **Trích xuất đặc điểm hình học**: Tính toán góc, độ cao, nhịp bước từ skeleton mẫu
3. **Xử lý video mới**: Trích skeleton và tracking nhiều người
4. **Căn chỉnh thời gian**: Khớp nhịp bằng Dynamic Time Warping (DTW)
5. **So sánh hình học**: Đo sai lệch giữa động tác thực tế và mẫu chuẩn
6. **Tính điểm**: Quy đổi sai lệch thành điểm số (0-10)
7. **Xuất lỗi và báo cáo**: Tạo video annotated và báo cáo chi tiết

## Cài đặt

### Yêu cầu

- Python 3.8+
- CUDA (khuyến nghị cho GPU) hoặc CPU

### Cài đặt dependencies

```bash
# Tạo virtual environment (khuyến nghị)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows

# Cài đặt packages
pip install -r requirements.txt
```

### Cài đặt models

Hệ thống sẽ tự động download models khi chạy lần đầu:
- RTMPose hoặc YOLOv8-Pose cho pose estimation
- Models sẽ được lưu vào `data/models/`

## Sử dụng

### Cách 1: Chạy toàn bộ pipeline

```bash
# Chạy với video mẫu chuẩn và video cần đánh giá
python main.py --mode full --golden-video data/golden_template/golden_video.mp4 --input-video data/input_videos/video1.mp4

# Nếu đã có golden template, chỉ cần video đầu vào
python main.py --mode full --input-video data/input_videos/video1.mp4
```

### Cách 2: Chạy từng bước riêng lẻ

#### Bước 1: Tạo golden template

```bash
# Đặt video mẫu chuẩn vào data/golden_template/golden_video.mp4
# hoặc chỉ định đường dẫn
python main.py --mode step1 --golden-video path/to/golden_video.mp4
```

**Công việc thủ công:**
1. Quay/chuẩn bị video mẫu chuẩn (1 người hoặc nhóm nhỏ)
   - Độ phân giải tối thiểu: 720p
   - Frame rate: 30fps trở lên
   - Điều kiện ánh sáng tốt, góc quay rõ ràng
   - Video dài ít nhất 1 chu kỳ điều lệnh hoàn chỉnh (10-30 giây)
2. Lưu video vào `data/golden_template/golden_video.mp4`

#### Bước 2: Trích xuất đặc điểm

```bash
python main.py --mode step2
```

**Công việc thủ công:**
1. Xác định các điểm khớp quan trọng (đã được định nghĩa trong config)
2. Xác định các góc và khoảng cách cần đo (đã được tính tự động)

#### Bước 3: Xử lý video mới

```bash
# Đặt video vào data/input_videos/
python main.py --mode step3 --input-video data/input_videos/video1.mp4
```

**Công việc thủ công:**
1. Chuẩn bị video đầu vào:
   - Đặt video vào `data/input_videos/`
   - Đảm bảo format tương thích (MP4, AVI)
   - Ghi chú số lượng người trong video
2. Kiểm tra chất lượng video (độ phân giải, ánh sáng)

#### Bước 4-7: Xử lý từng người

```bash
# Bước 4: Căn chỉnh thời gian
python main.py --mode step4 --video-name video1 --person-id 0

# Bước 5: So sánh hình học
python main.py --mode step5 --video-name video1 --person-id 0

# Bước 6: Tính điểm
python main.py --mode step6 --video-name video1 --person-id 0

# Bước 7: Xuất lỗi và báo cáo
python main.py --mode step7 --input-video data/input_videos/video1.mp4 --video-name video1 --person-id 0
```

## Cấu trúc dự án

```
Score-parade/
├── data/
│   ├── golden_template/          # Video và skeleton mẫu chuẩn
│   │   ├── golden_video.mp4
│   │   ├── golden_skeleton.pkl
│   │   ├── golden_profile.json
│   │   └── golden_skeleton_vis.mp4
│   ├── input_videos/             # Video đầu vào cần đánh giá
│   ├── output/                   # Video và báo cáo kết quả
│   │   └── {video_name}/
│   │       ├── person_{id}_skeleton.pkl
│   │       ├── person_{id}_aligned.pkl
│   │       ├── person_{id}_errors.json
│   │       ├── person_{id}_score.json
│   │       ├── person_{id}_annotated.mp4
│   │       ├── person_{id}_report.html
│   │       └── person_{id}_report.json
│   └── models/                   # Model weights
├── src/
│   ├── step1_golden_template.py
│   ├── step2_feature_extraction.py
│   ├── step3_process_video.py
│   ├── step4_temporal_alignment.py
│   ├── step5_geometric_matching.py
│   ├── step6_scoring.py
│   ├── step7_visualization.py
│   ├── utils/
│   │   ├── pose_estimation.py
│   │   ├── tracking.py
│   │   ├── geometry.py
│   │   ├── smoothing.py
│   │   └── video_utils.py
│   └── config.py
├── notebooks/                    # Jupyter notebooks để thử nghiệm
├── requirements.txt
├── main.py
└── README.md
```

## Cấu hình

Chỉnh sửa `src/config.py` để thay đổi:

- **Ngưỡng sai lệch**: Góc tay, góc chân, độ cao, etc.
- **Trọng số tính điểm**: Kỹ thuật tay (30%), chân (30%), nhịp bước (20%), ổn định (20%)
- **Công thức tính điểm**: Linear hoặc Exponential
- **Màu sắc visualization**: Màu đỏ/vàng/xanh cho các mức lỗi

## Output

Sau khi chạy xong, mỗi người sẽ có:

1. **Video annotated** (`person_{id}_annotated.mp4`): Video với skeleton và annotations lỗi
2. **Báo cáo HTML** (`person_{id}_report.html`): Báo cáo chi tiết với bảng điểm và lỗi
3. **Báo cáo JSON** (`person_{id}_report.json`): Dữ liệu raw để xử lý tiếp

## Lưu ý

- **Bước 1-2 chỉ làm 1 lần** để tạo golden template
- **Bước 3-7** sẽ chạy cho mỗi video đầu vào mới
- Test với video ngắn trước, sau đó scale lên video dài
- Đảm bảo video có chất lượng tốt (độ phân giải, ánh sáng) để kết quả chính xác

## Troubleshooting

### Lỗi import mmpose
```bash
pip install mmpose mmcv mmengine
# Hoặc nếu dùng GPU
pip install mmpose mmcv-full mmengine
```

### Lỗi không detect được người
- Kiểm tra chất lượng video (độ phân giải, ánh sáng)
- Điều chỉnh `confidence_threshold` trong `config.py`
- Thử model khác (RTMPose hoặc YOLOv8-Pose)

### Lỗi tracking không ổn định
- Điều chỉnh `max_age`, `min_hits`, `iou_threshold` trong `config.py`
- Đảm bảo video có góc quay ổn định

## Tham khảo

- RTMPose: https://github.com/open-mmlab/mmpose
- OC-SORT: https://github.com/noahcao/OC_SORT
- DTW: https://github.com/DynamicTimeWarping/dtw-python

## License

[Thêm license nếu cần]

