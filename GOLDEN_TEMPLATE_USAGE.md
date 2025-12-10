# Hướng dẫn sử dụng Golden Template (Nhiều người & Góc quay)

## Tổng quan

Hệ thống đã được nâng cấp để hỗ trợ:
- ✅ Nhiều người trong một video golden template
- ✅ Nhiều góc quay (front, side, back, diagonal)
- ✅ Tự động chọn profile phù hợp khi so sánh
- ✅ Tạo profile tổng hợp (trung bình)

## Cách sử dụng

### 1. Tạo Golden Template với một người (chế độ cũ)

```bash
# Chế độ mặc định: chỉ lấy người đầu tiên
python main.py --mode step1 --golden-video data/golden_template/video.mp4

# Hoặc chỉ định rõ ràng
python main.py --mode step1 --golden-video video.mp4 --single-person
```

### 2. Tạo Golden Template với nhiều người

```bash
# Tự động detect và track tất cả người trong video
python main.py --mode step1 \
    --golden-video data/golden_template/video_multi.mp4 \
    --template-name "template_1" \
    --camera-angle "front" \
    --multi-person
```

**Kết quả:**
```
data/golden_template/template_1/
├── metadata.json
├── person_0/
│   ├── skeleton.pkl
│   ├── profile.json (sau step2)
│   └── visualization.mp4
├── person_1/
│   ├── skeleton.pkl
│   ├── profile.json
│   └── visualization.mp4
└── person_2/
    ├── skeleton.pkl
    ├── profile.json
    └── visualization.mp4
```

### 3. Tạo Golden Template với nhiều góc quay

```bash
# Góc quay 1: Front
python main.py --mode step1 \
    --golden-video data/golden_template/video_front.mp4 \
    --template-name "template_front" \
    --camera-angle "front" \
    --multi-person

# Góc quay 2: Side
python main.py --mode step1 \
    --golden-video data/golden_template/video_side.mp4 \
    --template-name "template_side" \
    --camera-angle "side" \
    --multi-person
```

### 4. Trích xuất Profile (Step 2)

#### Cho template nhiều người:

```bash
# Chỉ định template cụ thể
python main.py --mode step2 --template-name "template_1"

# Hoặc tự động tìm template mới nhất
python main.py --mode step2 --template-name "template_1"
```

**Kết quả:**
- Profile cho từng người: `person_X/profile.json`
- Profile tổng hợp: `template_1/combined_profile.json`
- Summary: `template_1/profiles_summary.json`

#### Cho template một người (chế độ cũ):

```bash
python main.py --mode step2
```

### 5. Quản lý Templates

```bash
# Liệt kê tất cả templates
python src/manage_golden_template.py list

# Xem thông tin template
python src/manage_golden_template.py info --template template_1

# Xóa template
python src/manage_golden_template.py delete --template template_1
```

### 6. So sánh tự động (Step 5)

Khi chấm thí sinh, hệ thống sẽ tự động:
1. So sánh với tất cả profiles trong template
2. Chọn profile có similarity cao nhất
3. Hoặc ưu tiên profile cùng góc quay nếu biết

```bash
# Hệ thống tự động chọn profile phù hợp
python main.py --mode step5 --video-name video1 --person-id 0
```

## Cấu trúc dữ liệu

### Metadata.json

```json
{
  "template_name": "template_1",
  "camera_angle": "front",
  "metadata": {
    "fps": 30,
    "width": 1920,
    "height": 1080
  },
  "people": {
    "0": {
      "skeleton_path": "person_0/skeleton.pkl",
      "vis_path": "person_0/visualization.mp4",
      "num_frames": 300
    },
    "1": {
      "skeleton_path": "person_1/skeleton.pkl",
      "vis_path": "person_1/visualization.mp4",
      "num_frames": 300
    }
  }
}
```

### Profile.json (cho mỗi người)

```json
{
  "metadata": {...},
  "statistics": {
    "arm_angle": {
      "left": {"mean": 45.2, "std": 2.1},
      "right": {"mean": 45.8, "std": 2.3}
    },
    "leg_angle": {...},
    ...
  }
}
```

## Ví dụ workflow hoàn chỉnh

### Scenario 1: Video với 2-3 người, góc quay front

```bash
# Bước 1: Tạo template
python main.py --mode step1 \
    --golden-video data/golden_template/multi_person_front.mp4 \
    --template-name "multi_front" \
    --camera-angle "front" \
    --multi-person

# Bước 2: Trích xuất profile
python main.py --mode step2 --template-name "multi_front"

# Kết quả: 2-3 profiles riêng + 1 profile tổng hợp
```

### Scenario 2: Nhiều góc quay

```bash
# Template 1: Front
python main.py --mode step1 \
    --golden-video video_front.mp4 \
    --template-name "angle_front" \
    --camera-angle "front" \
    --multi-person

# Template 2: Side
python main.py --mode step1 \
    --golden-video video_side.mp4 \
    --template-name "angle_side" \
    --camera-angle "side" \
    --multi-person

# Trích xuất profile cho cả hai
python main.py --mode step2 --template-name "angle_front"
python main.py --mode step2 --template-name "angle_side"
```

### Scenario 3: Chấm thí sinh (tự động chọn profile)

```bash
# Hệ thống tự động:
# 1. So sánh với tất cả profiles
# 2. Chọn profile phù hợp nhất
# 3. Hoặc chọn theo camera angle nếu biết

python main.py --mode full --input-video data/input_videos/test.mp4
```

## Lưu ý

1. **Tương thích ngược:** Code cũ vẫn hoạt động (chỉ lấy người đầu tiên)
2. **Tự động chọn:** Nếu không chỉ định `--multi-person`, mặc định dùng chế độ cũ
3. **Profile tổng hợp:** Được tạo tự động khi có nhiều người (có thể tắt bằng `--no-combined`)
4. **Camera angle:** Chỉ là metadata, không ảnh hưởng đến xử lý, nhưng giúp chọn profile phù hợp

## Troubleshooting

### Lỗi: "Không tìm thấy template"

```bash
# Kiểm tra templates có sẵn
python src/manage_golden_template.py list

# Tạo template mới
python main.py --mode step1 --golden-video video.mp4 --template-name "new_template" --multi-person
```

### Lỗi: "Không track được người"

- Kiểm tra video có đủ người không
- Thử giảm `min_motion_variance` trong `config.py`
- Kiểm tra chất lượng video (độ phân giải, FPS)

### Lỗi: "Không tìm thấy profile"

```bash
# Tạo profile cho template
python main.py --mode step2 --template-name "template_name"
```

