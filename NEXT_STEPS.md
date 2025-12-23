# 🚀 Các bước tiếp theo sau khi chuyển sang MMPose

## ✅ Đã hoàn thành
- [x] Cập nhật code để hỗ trợ MMPose và AlphaPose
- [x] Cập nhật config.py với model mặc định là MMPose
- [x] Tạo documentation (POSE_MODEL_MIGRATION.md)
- [x] Cập nhật env.example

## 📋 Checklist các bước tiếp theo

### Bước 1: Cài đặt MMPose dependencies

#### Nếu chạy local (không dùng Docker):

```bash
# Cài đặt MIM (OpenMMLab package manager)
pip install openmim

# Cài đặt MMPose và dependencies
mim install mmengine
mim install mmcv
mim install mmpose
```

**Hoặc cài trực tiếp:**
```bash
pip install mmengine mmcv mmpose
```

**Lưu ý:** `mmcv` cần version phù hợp với PyTorch. Nếu gặp lỗi, kiểm tra:
```bash
python -c "import torch; print(torch.__version__)"
# Sau đó cài mmcv phù hợp
```

#### Nếu chạy trong Docker:

Cần cập nhật `Dockerfile` để cài MMPose. Xem Bước 2.

---

### Bước 2: Cập nhật Dockerfile (Nếu dùng Docker)

Cập nhật `Dockerfile` để cài MMPose trong container:

```dockerfile
# Thêm vào phần install dependencies
RUN pip install --no-cache-dir openmim && \
    mim install mmengine mmcv mmpose
```

Hoặc cài trực tiếp:
```dockerfile
RUN pip install --no-cache-dir mmengine mmcv mmpose
```

**Sau đó rebuild:**
```bash
docker-compose build app
docker-compose up -d
```

---

### Bước 3: Cấu hình Environment

#### Tạo/Update file `.env`:

```bash
# Copy từ env.example nếu chưa có
cp env.example .env
```

#### Thêm vào `.env`:

```bash
# Pose Estimation Model Configuration
POSE_MODEL_TYPE=mmpose
MMPOSE_MODEL=rtmpose-m_8xb256-420e_coco-256x192
```

**Các model options:**
- `rtmpose-s_8xb256-420e_coco-256x192` - Small (nhanh)
- `rtmpose-m_8xb256-420e_coco-256x192` - Medium (cân bằng) ⭐ **Khuyến nghị**
- `rtmpose-l_8xb256-420e_coco-256x192` - Large (chính xác)
- `rtmpose-x_8xb256-420e_coco-256x192` - XLarge (rất chính xác)

---

### Bước 4: Test cài đặt

#### Test import MMPose:

```bash
python -c "from mmpose.apis import MMPoseInferencer; print('✅ MMPose installed successfully')"
```

#### Test PoseEstimator:

```python
# Tạo file test_pose.py
from backend.app.services.pose_estimation import PoseEstimator
import cv2
import numpy as np

# Khởi tạo estimator
print("Đang khởi tạo MMPose...")
estimator = PoseEstimator(model_type="mmpose")
print("✅ MMPose khởi tạo thành công!")

# Test với một frame (nếu có ảnh test)
# frame = cv2.imread("test_image.jpg")
# keypoints = estimator.predict(frame)
# print(f"Phát hiện {len(keypoints)} người")
```

Chạy:
```bash
python test_pose.py
```

---

### Bước 5: Rebuild và Start Services

#### Nếu dùng Docker:

```bash
# Rebuild với dependencies mới
docker-compose build app

# Start services
docker-compose up -d

# Kiểm tra logs
docker-compose logs app -f
```

#### Nếu chạy local:

```bash
# Chỉ cần start lại (nếu đã cài dependencies)
# Hoặc chạy trực tiếp
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### Bước 6: Verify hoạt động

#### 1. Kiểm tra API health:

```bash
curl http://localhost:8000/api/health
```

#### 2. Kiểm tra logs khi khởi động:

Tìm dòng:
```
✅ Đã khởi tạo MMPose: rtmpose-m_8xb256-420e_coco-256x192 trên cuda/cpu
```

#### 3. Test với một video (nếu có):

Upload video qua API và kiểm tra xem pose estimation có hoạt động không.

---

### Bước 7: Tối ưu (Tùy chọn)

#### 1. Chọn model phù hợp:

- **Nếu cần tốc độ:** Dùng `rtmpose-s` (small)
- **Nếu cần cân bằng:** Dùng `rtmpose-m` (medium) ⭐
- **Nếu cần độ chính xác cao:** Dùng `rtmpose-l` hoặc `rtmpose-x`

#### 2. Tối ưu batch size:

Trong `backend/app/config.py`:
```python
POSE_CONFIG = {
    "batch_size": 4,  # Tăng nếu có GPU mạnh
    # ...
}
```

#### 3. Sử dụng GPU:

Đảm bảo CUDA đã được cài:
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

Nếu True, model sẽ tự động dùng GPU.

---

## ⚠️ Troubleshooting

### Lỗi: "Cần cài đặt mmpose"

```bash
pip install openmim
mim install mmengine mmcv mmpose
```

### Lỗi: "mmcv version không tương thích"

```bash
# Kiểm tra PyTorch version
python -c "import torch; print(torch.__version__)"

# Cài mmcv phù hợp (xem https://mmcv.readthedocs.io/)
pip install mmcv==2.0.0  # Thay version phù hợp
```

### Lỗi: "CUDA out of memory"

Giảm model size:
```bash
# Trong .env
MMPOSE_MODEL=rtmpose-s_8xb256-420e_coco-256x192  # Small model
```

Hoặc giảm batch size:
```python
POSE_CONFIG = {"batch_size": 1}
```

### Model không download tự động

MMPose sẽ tự động download model lần đầu. Nếu gặp vấn đề:

```bash
python -c "from mmpose.apis import MMPoseInferencer; MMPoseInferencer('rtmpose-m_8xb256-420e_coco-256x192')"
```

---

## 📊 So sánh Performance

Sau khi cài đặt, bạn có thể so sánh performance:

| Model | mAP | FPS (GPU) | FPS (CPU) | Model Size |
|-------|-----|-----------|-----------|------------|
| RTMPose-S | ~70 | ~150 | ~15 | ~15MB |
| RTMPose-M | ~75 | ~120 | ~12 | ~30MB |
| RTMPose-L | ~78 | ~90 | ~8 | ~60MB |
| RTMPose-X | ~80 | ~60 | ~5 | ~120MB |
| YOLOv8n-Pose | ~65 | ~200 | ~20 | ~6MB |

---

## 🎯 Kết luận

Sau khi hoàn thành các bước trên:

1. ✅ MMPose đã được cài đặt
2. ✅ Config đã được cập nhật
3. ✅ Services đã được restart
4. ✅ Model đã được load và sẵn sàng sử dụng

**Dự án của bạn giờ đã sử dụng MMPose thay vì YOLOv8!** 🎉

