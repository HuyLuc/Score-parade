# Nâng cấp Golden Template - Hỗ trợ nhiều người và góc quay

## Yêu cầu

Golden template có thể:
- Chứa 2-3 người trong cùng video
- Hỗ trợ nhiều góc quay (nhiều video hoặc một video với nhiều cảnh)
- Tạo profile riêng cho từng người và/hoặc góc quay
- Tự động chọn profile phù hợp nhất khi so sánh

## Cấu trúc dữ liệu mới

### Database Models

**File: `backend/app/models/golden_template.py`**
```python
class GoldenTemplate(Base):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    criteria_type: str  # di_deu/di_nghiem

class GoldenPerson(Base):
    id: int
    template_id: int (FK)
    person_index: int  # 0, 1, 2...
    camera_angle: str  # front, side, back, etc.
    video_path: str
    skeleton_path: str
    profile_path: str
    is_primary: bool  # Profile chính để dùng mặc định

class GoldenProfile(Base):
    id: int
    golden_person_id: int (FK)
    statistics: JSON  # Tương tự profile hiện tại
    created_at: datetime
```

### File Structure

```
data/golden_template/
├── template_1/
│   ├── video.mp4 (hoặc video_front.mp4, video_side.mp4)
│   ├── metadata.json
│   ├── person_0/
│   │   ├── skeleton.pkl
│   │   └── profile.json
│   ├── person_1/
│   │   ├── skeleton.pkl
│   │   └── profile.json
│   └── person_2/
│       ├── skeleton.pkl
│       └── profile.json
├── template_2/ (góc quay khác)
│   └── ...
└── combined_profiles/ (profile tổng hợp)
    ├── average_profile.json
    └── best_profile.json
```

## Cập nhật Step 1: Tạo Golden Template

**File: `src/step1_golden_template_multi.py`** (mới)

```python
def create_golden_template_multi(
    video_path: Path,
    template_name: str = "default",
    camera_angle: str = "front",
    output_dir: Path = None
) -> dict:
    """
    Tạo golden template với nhiều người
    
    Args:
        video_path: Đường dẫn video
        template_name: Tên template
        camera_angle: Góc quay (front, side, back, etc.)
        output_dir: Thư mục output
    """
    # 1. Trích xuất skeleton cho TẤT CẢ người
    # 2. Tracking để phân biệt từng người
    # 3. Lưu skeleton riêng cho từng người
    # 4. Tạo profile cho từng người
    # 5. Tạo profile tổng hợp (optional)
```

**Thay đổi chính:**
- Không chỉ lấy người đầu tiên
- Tracking tất cả người trong video
- Lưu skeleton và profile riêng cho mỗi người
- Metadata: camera_angle, person_index

## Cập nhật Step 2: Trích xuất đặc điểm

**File: `src/step2_feature_extraction_multi.py`** (mới)

```python
def extract_features_multi_person(
    template_dir: Path,
    create_combined: bool = True
) -> dict:
    """
    Trích xuất features cho tất cả người trong template
    
    Args:
        template_dir: Thư mục template
        create_combined: Có tạo profile tổng hợp không
    """
    # 1. Load skeleton cho từng người
    # 2. Tính profile cho từng người
    # 3. Tạo profile tổng hợp (trung bình) nếu cần
    # 4. Lưu vào database
```

## Cập nhật Step 5: So sánh với profile phù hợp

**File: `src/step5_geometric_matching.py`** (cập nhật)

```python
def compare_with_golden_auto_select(
    person_keypoints: np.ndarray,
    golden_template_id: int,
    camera_angle: Optional[str] = None
) -> Dict:
    """
    So sánh và tự động chọn profile phù hợp nhất
    
    Args:
        person_keypoints: Keypoints của người cần đánh giá
        golden_template_id: ID của golden template
        camera_angle: Góc quay (nếu biết trước)
    """
    # 1. Load tất cả profiles từ template
    # 2. Nếu có camera_angle, ưu tiên profiles cùng góc
    # 3. So sánh với từng profile
    # 4. Chọn profile có similarity cao nhất
    # 5. So sánh với profile đã chọn
```

## Cập nhật Config

**File: `src/config.py`** (thêm)

```python
GOLDEN_TEMPLATE_CONFIG = {
    "support_multi_person": True,
    "max_people_per_template": 3,
    "supported_camera_angles": ["front", "side", "back", "diagonal"],
    "auto_select_profile": True,  # Tự động chọn profile phù hợp
    "create_combined_profile": True,  # Tạo profile tổng hợp
}
```

## API mới

**File: `backend/app/api/golden_template.py`**

```python
# Tạo template mới
POST /api/golden-template
{
    "name": "Template 1",
    "video_path": "...",
    "camera_angle": "front"
}

# Thêm người vào template
POST /api/golden-template/{id}/add-person
{
    "video_path": "...",
    "person_index": 1,
    "camera_angle": "side"
}

# Lấy tất cả profiles
GET /api/golden-template/{id}/profiles

# Chọn profile để dùng
POST /api/golden-template/{id}/select-profile
{
    "profile_id": 1
}

# Tạo profile tổng hợp
POST /api/golden-template/{id}/create-combined-profile
```

## Workflow mới

### Tạo Golden Template với nhiều người:

1. **Quay video** với 2-3 người (hoặc nhiều góc quay)
2. **Chạy Step 1:**
   ```bash
   python src/step1_golden_template_multi.py \
       --video data/golden_template/video_multi.mp4 \
       --template-name "template_1" \
       --camera-angle "front"
   ```
3. **Hệ thống tự động:**
   - Detect tất cả người
   - Tracking từng người
   - Lưu skeleton cho mỗi người
4. **Chạy Step 2:**
   ```bash
   python src/step2_feature_extraction_multi.py \
       --template-name "template_1" \
       --create-combined
   ```
5. **Kết quả:**
   - Profile cho từng người
   - Profile tổng hợp (trung bình)

### So sánh tự động:

1. **Khi chấm thí sinh:**
   - Hệ thống tự động so sánh với tất cả profiles
   - Chọn profile có similarity cao nhất
   - Hoặc chọn theo camera angle nếu biết

2. **Hoặc chọn thủ công:**
   - User chọn profile cụ thể trong ConfigurationView
   - Hoặc chọn "Auto" để tự động

## Lợi ích

1. **Linh hoạt hơn:** Có thể dùng nhiều người mẫu
2. **Chính xác hơn:** Chọn profile phù hợp với góc quay
3. **Đa dạng:** Hỗ trợ nhiều góc quay khác nhau
4. **Tự động:** Không cần chọn thủ công

## Migration từ code cũ

- Code cũ vẫn hoạt động (chỉ lấy người đầu tiên)
- Code mới là optional, có thể dùng song song
- Có thể convert template cũ sang format mới
