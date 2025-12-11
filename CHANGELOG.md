# Changelog - Các cải tiến và sửa lỗi

## ✅ Đã sửa lỗi

### 1. Lỗi `confidence_threshold` trong `pose_estimation.py`
- **Vấn đề**: Code dùng `confidence_threshold` nhưng config có `conf_threshold`
- **Giải pháp**: Sửa tất cả references để dùng `conf_threshold` với `.get()` để có fallback

### 2. Lỗi `torso_stability` với single frame
- **Vấn đề**: `calculate_torso_stability` được gọi với single frame nhưng cần sequence
- **Giải pháp**: 
  - Sửa hàm để nhận cả single frame và sequence
  - Bỏ qua `torso_stability` trong `_check_back_posture` (single frame)
  - Tính `torso_stability` sau khi có đủ frames trong `create_golden_template`

### 3. Lỗi encoding trên Windows
- **Vấn đề**: Unicode characters không hiển thị đúng trong PowerShell
- **Giải pháp**: Thêm fix encoding trong `score_video.py` và `run_scoring.py`

### 4. Error handling trong `load_golden_template`
- **Vấn đề**: Không có error handling khi load golden template
- **Giải pháp**: 
  - Thêm try-except cho JSON và pickle loading
  - Thêm fallback cho `keypoints` nếu không có `valid_skeletons`
  - Thêm warning messages khi không load được

## 🔧 Cải tiến

### 1. README.md
- Cập nhật đầy đủ thông tin về dự án
- Thêm hướng dẫn sử dụng chi tiết
- Thêm troubleshooting section
- Thêm mô tả cách hoạt động

### 2. Error handling
- Thêm validation và error handling tốt hơn
- Thêm warning messages thay vì crash
- Fallback values khi không có golden template

### 3. Code quality
- Kiểm tra và sửa tất cả lỗi linter
- Đảm bảo imports đúng
- Validation input tốt hơn

## 📝 Files đã thay đổi

1. `backend/app/services/pose_estimation.py` - Sửa `confidence_threshold` → `conf_threshold`
2. `backend/app/services/geometry.py` - Sửa `calculate_torso_stability` để nhận cả single frame và sequence
3. `backend/app/controllers/ai_controller.py` - Bỏ qua `torso_stability` trong single frame check, thêm error handling
4. `score_video.py` - Sửa logic tính `torso_stability`, thêm encoding fix, thêm validation
5. `README.md` - Cập nhật đầy đủ với thông tin mới

## ✅ Kiểm tra

- ✅ Tất cả imports đúng
- ✅ Không có lỗi linter
- ✅ Error handling đầy đủ
- ✅ README.md cập nhật
- ✅ Code hoạt động đúng với test cases

