# Hướng dẫn chuyển đổi từ YOLOv8 sang MMPose/AlphaPose

## Tổng quan

Dự án đã được cập nhật để hỗ trợ **MMPose (RTMPose)** và **AlphaPose** thay thế cho YOLOv8. 

### So sánh các models

| Model | Độ chính xác | Tốc độ | Dễ setup | Khuyến nghị |
|-------|--------------|--------|----------|-------------|
| **MMPose (RTMPose)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ **Khuyến nghị** |
| **AlphaPose** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⚠️ Phức tạp |
| **YOLOv8** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ Legacy |

## 1. Cài đặt MMPose (Khuyến nghị)

### Cách 1: Sử dụng OpenMMLab MIM (Khuyến nghị)

```bash
# Cài đặt MIM
pip install openmim

# Cài đặt MMPose và dependencies
mim install mmengine
mim install mmcv
mim install mmpose
```

### Cách 2: Cài đặt trực tiếp

```bash
pip install mmengine mmcv mmpose
```

**Lưu ý:** `mmcv` cần version phù hợp với PyTorch version của bạn.

## 2. Cấu hình

### Cập nhật file `.env` hoặc environment variables:

```bash
# Chọn model type
POSE_MODEL_TYPE=mmpose

# Chọn MMPose model (tùy chọn, có thể để mặc định)
MMPOSE_MODEL=rtmpose-m_8xb256-420e_coco-256x192
```

### Các model MMPose có sẵn:

- **RTMPose-S** (Small, nhanh): `rtmpose-s_8xb256-420e_coco-256x192`
- **RTMPose-M** (Medium, cân bằng): `rtmpose-m_8xb256-420e_coco-256x192` ⭐ **Mặc định**
- **RTMPose-L** (Large, chính xác): `rtmpose-l_8xb256-420e_coco-256x192`
- **RTMPose-X** (XLarge, rất chính xác): `rtmpose-x_8xb256-420e_coco-256x192`

### Cập nhật `backend/app/config.py`:

Model type mặc định đã được đổi từ `"yolov8"` sang `"mmpose"`. Bạn có thể override bằng environment variable:

```python
POSE_CONFIG = {
    "model_type": os.getenv("POSE_MODEL_TYPE", "mmpose"),  # mmpose, alphapose, yolov8
    "mmpose_model": os.getenv("MMPOSE_MODEL", "rtmpose-m_8xb256-420e_coco-256x192"),
    # ...
}
```

## 3. Cài đặt AlphaPose (Tùy chọn)

AlphaPose phức tạp hơn để setup, chỉ nên dùng nếu cần độ chính xác đặc biệt cao.

### Bước 1: Clone AlphaPose

```bash
git clone https://github.com/MVIG-SJTU/AlphaPose.git
cd AlphaPose
```

### Bước 2: Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### Bước 3: Download models

```bash
# Download detector (YOLOv5)
python scripts/demo_inference.py --detector yolov5s

# Download pose models
python scripts/download_models.py
```

### Bước 4: Cấu hình

```bash
# Trong .env
POSE_MODEL_TYPE=alphapose
ALPHAPOSE_PATH=/path/to/AlphaPose
ALPHAPOSE_DETECTOR=yolov5s
ALPHAPOSE_MODEL=fastpose_duc
```

## 4. Kiểm tra cài đặt

### Test MMPose:

```python
from backend.app.services.pose_estimation import PoseEstimator
import cv2
import numpy as np

# Khởi tạo estimator
estimator = PoseEstimator(model_type="mmpose")

# Test với một frame
frame = cv2.imread("test_image.jpg")
keypoints = estimator.predict(frame)

print(f"Phát hiện {len(keypoints)} người")
```

### Test AlphaPose:

```python
estimator = PoseEstimator(model_type="alphapose")
keypoints = estimator.predict(frame)
```

## 5. Keypoint Format

Tất cả models đều trả về keypoints theo **COCO format** với **17 keypoints**:

```python
# Format: [17, 3] với (x, y, confidence)
keypoints = [
    [x_nose, y_nose, conf_nose],
    [x_left_eye, y_left_eye, conf_left_eye],
    # ... 17 keypoints
]
```

Keypoint indices (giống YOLOv8):
- 0: nose
- 1-2: left_eye, right_eye
- 3-4: left_ear, right_ear
- 5-6: left_shoulder, right_shoulder
- 7-8: left_elbow, right_elbow
- 9-10: left_wrist, right_wrist
- 11-12: left_hip, right_hip
- 13-14: left_knee, right_knee
- 15-16: left_ankle, right_ankle

## 6. Migration từ YOLOv8

### Thay đổi code:

**Trước (YOLOv8):**
```python
estimator = PoseEstimator(model_type="yolov8")
```

**Sau (MMPose):**
```python
estimator = PoseEstimator(model_type="mmpose")
# Hoặc
estimator = PoseEstimator()  # Sử dụng config mặc định
```

### Không cần thay đổi:

- ✅ Keypoint format (vẫn là 17 keypoints COCO)
- ✅ API của `PoseService` và `PoseEstimator`
- ✅ Các services khác (tracking, scoring, etc.)

## 7. Troubleshooting

### Lỗi: "Cần cài đặt mmpose"

```bash
pip install openmim
mim install mmengine mmcv mmpose
```

### Lỗi: "mmcv version không tương thích"

```bash
# Kiểm tra PyTorch version
python -c "import torch; print(torch.__version__)"

# Cài đặt mmcv phù hợp
pip install mmcv==2.0.0  # Thay version phù hợp
```

### Lỗi: "CUDA out of memory"

Giảm model size hoặc batch size:
```python
POSE_CONFIG = {
    "mmpose_model": "rtmpose-s_8xb256-420e_coco-256x192",  # Small model
    "batch_size": 1,
}
```

### Model không download tự động

MMPose sẽ tự động download model lần đầu tiên. Nếu gặp vấn đề:

```bash
# Download thủ công
python -c "from mmpose.apis import MMPoseInferencer; MMPoseInferencer('rtmpose-m_8xb256-420e_coco-256x192')"
```

## 8. Performance Tips

1. **Sử dụng RTMPose-M** cho cân bằng tốc độ/chính xác
2. **Sử dụng RTMPose-S** nếu cần tốc độ cao
3. **Sử dụng RTMPose-L/X** nếu cần độ chính xác tối đa
4. **Batch processing** có thể cải thiện throughput
5. **GPU** sẽ tăng tốc đáng kể

## 9. So sánh Performance

| Model | mAP (COCO) | FPS (GPU) | FPS (CPU) | Model Size |
|-------|------------|-----------|-----------|------------|
| RTMPose-S | ~70 | ~150 | ~15 | ~15MB |
| RTMPose-M | ~75 | ~120 | ~12 | ~30MB |
| RTMPose-L | ~78 | ~90 | ~8 | ~60MB |
| RTMPose-X | ~80 | ~60 | ~5 | ~120MB |
| YOLOv8n-Pose | ~65 | ~200 | ~20 | ~6MB |

## 10. Kết luận

✅ **Khuyến nghị:** Sử dụng **MMPose (RTMPose-M)** vì:
- Độ chính xác cao hơn YOLOv8 đáng kể
- Dễ cài đặt và sử dụng
- Tương thích hoàn toàn với code hiện tại
- Hỗ trợ nhiều models khác nhau

⚠️ **AlphaPose:** Chỉ dùng nếu cần độ chính xác đặc biệt cao và sẵn sàng setup phức tạp.

❌ **YOLOv8:** Vẫn được hỗ trợ nhưng không khuyến nghị cho mục đích pose estimation chính xác.

