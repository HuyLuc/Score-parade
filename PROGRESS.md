# Tiến độ triển khai

## ✅ Phase 1: Database Foundation (HOÀN THÀNH)

### Models đã tạo:
- ✅ `person.py` - Person, Soldier, Officer với Rank, Gender enums
- ✅ `part_of_body.py` - PartOfBody và 10 lớp con (Nose, Neck, Shoulder, Arm, Elbow, Fist, Hand, Back, Knee, Foot)
- ✅ `score.py` - Score với list_of_modified_times
- ✅ `criterion.py` - Criterion với action và weight
- ✅ `candidate.py` - Candidate với CandidateStatus enum
- ✅ `session.py` - ScoringSession, Error với các enums (SessionMode, SessionType, CriteriaType)
- ✅ `media.py` - Audio, Video, Log với các enums

### Database setup:
- ✅ `base.py` - SQLAlchemy base và engine
- ✅ `session.py` - Session management với get_db()
- ✅ `migrations/` - Alembic setup (env.py, script.py.mako)

## ✅ Phase 2: Authentication (HOÀN THÀNH - Backend)

### Controllers:
- ✅ `db_controller.py` - Database operations (create_person, authenticate_user, candidate CRUD)
- ✅ `register_controller.py` - Register với validation
- ✅ `login_controller.py` - Login với JWT token

### API:
- ✅ `auth.py` - API routes:
  - POST `/api/auth/register` - Đăng ký
  - POST `/api/auth/login` - Đăng nhập
  - GET `/api/auth/me` - Lấy thông tin user hiện tại

### Utilities:
- ✅ `utils/auth.py` - Password hashing, JWT tokens

### Main app:
- ✅ Đã đăng ký auth router trong `main.py`

## 🔄 Phase 2: Authentication (ĐANG LÀM - Frontend)

### Views cần tạo:
- ⏳ `RegisterView.tsx` - Màn hình đăng ký
- ⏳ `LoginView.tsx` - Màn hình đăng nhập

## ✅ Phase 3: Candidate Management (HOÀN THÀNH)

### Backend:
- ✅ `candidate_controller.py` - Controller với validation, import Excel, CRUD
- ✅ `api/candidates.py` - API routes:
  - GET `/api/candidates/` - Lấy tất cả
  - GET `/api/candidates/{id}` - Lấy theo ID
  - POST `/api/candidates/` - Tạo mới
  - PUT `/api/candidates/{id}` - Cập nhật
  - DELETE `/api/candidates/{id}` - Xóa
  - POST `/api/candidates/import` - Import Excel
  - POST `/api/candidates/{id}/select` - Chọn candidate

### Frontend:
- ✅ `ListOfCandidatesView.tsx` - Danh sách thí sinh với:
  - Hiển thị danh sách
  - Chọn thí sinh (radio)
  - Import Excel
  - Tạo mới
  - Sửa/Xóa
  - Next button (disabled nếu chưa chọn)
- ✅ `CreateCandidateView.tsx` - Form tạo thí sinh mới
- ✅ `services/candidateService.ts` - API service
- ✅ `services/api.ts` - Axios client với interceptors

### Dependencies:
- ✅ Thêm `pandas` và `openpyxl` vào requirements.txt

## ✅ Phase 4: Configuration & Barem (HOÀN THÀNH)

### Backend:
- ✅ `configuration_controller.py` - Controller cho cấu hình:
  - Đổi mật khẩu
  - Get/Update configuration (mode, criteria, difficulty, operation_mode)
- ✅ `barem_controller.py` - Controller cho barem điểm:
  - Lấy tất cả criteria
  - Lấy criteria theo loại (posture, rhythm, distance, speed)
  - Cập nhật trọng số (đơn lẻ hoặc nhiều)
- ✅ `difficult_controller.py` - Controller cho mức độ khắt khe:
  - Điều chỉnh trọng số theo difficulty (easy/normal/hard)
  - Tính điểm trừ đã điều chỉnh
- ✅ `api/configuration.py` - API routes:
  - POST `/api/configuration/change-password` - Đổi mật khẩu
  - GET `/api/configuration/` - Lấy cấu hình
  - PUT `/api/configuration/` - Cập nhật cấu hình
- ✅ `api/barem.py` - API routes:
  - GET `/api/barem/` - Lấy tất cả criteria
  - GET `/api/barem/by-type/{type}` - Lấy theo loại
  - PUT `/api/barem/weight/{id}` - Cập nhật trọng số
  - PUT `/api/barem/weights` - Cập nhật nhiều trọng số

### Frontend:
- ✅ `ConfigurationView.tsx` - Màn hình cấu hình:
  - Đổi mật khẩu (form riêng)
  - Chọn chế độ (testing/practising)
  - Chọn tiêu chí (di_deu/di_nghiem)
  - Chọn mức độ khắt khe (easy/normal/hard)
  - Chọn chế độ hoạt động (dev/release)
- ✅ `BaremView.tsx` - Màn hình barem:
  - Hiển thị criteria theo nhóm (posture, rhythm, distance, speed)
  - Lọc theo loại
  - Chỉnh sửa trọng số
  - Lưu thay đổi (nhiều cùng lúc)
  - Reset về giá trị ban đầu
- ✅ `services/configurationService.ts` - API service
- ✅ `services/baremService.ts` - API service

## ✅ Phase 5: Camera Integration (HOÀN THÀNH)

### Backend:
- ✅ `camera_controller.py` - Controller cho camera:
  - Kết nối/ngắt kết nối camera
  - Lấy frame từ camera
  - Quản lý nhiều cameras (tối đa 2)
  - Lấy thông tin camera (resolution, FPS)
- ✅ `snapshot_controller.py` - Controller cho snapshot:
  - Chụp snapshot theo interval
  - Lưu snapshot vào file
  - Tổ chức theo session
- ✅ `video_controller.py` - Controller cho video recording:
  - Bắt đầu/dừng ghi video
  - Ghi video theo chunks (thời lượng cố định)
  - Lưu video vào file
- ✅ `api/camera.py` - API routes:
  - POST `/api/camera/connect` - Kết nối camera
  - POST `/api/camera/disconnect/{id}` - Ngắt kết nối
  - GET `/api/camera/info` - Lấy thông tin cameras
  - GET `/api/camera/{id}/frame` - Lấy frame (streaming)
  - POST `/api/camera/{id}/snapshot` - Chụp snapshot
  - POST `/api/camera/{id}/video/start` - Bắt đầu ghi video
  - POST `/api/camera/{id}/video/stop` - Dừng ghi video

### Frontend:
- ✅ `CameraView.tsx` - Component hiển thị camera:
  - Auto connect/disconnect
  - Streaming frames (10 FPS)
  - Hiển thị thông tin camera
  - Controls (connect/disconnect)
  - Error handling
- ✅ `services/cameraService.ts` - API service cho camera

## ✅ Phase 6: Local Mode (Làm chậm) (HOÀN THÀNH)

### Backend:
- ✅ `local_controller.py` - Base controller cho Local Mode:
  - `LocalTestingController` - Testing mode (trừ điểm)
  - `LocalPractisingController` - Practising mode (chỉ hiển thị lỗi)
  - Xử lý frame, phát hiện lỗi, cập nhật điểm
  - Lưu snapshot khi có lỗi
- ✅ `ai_controller.py` - AI Controller phát hiện lỗi:
  - Phát hiện lỗi tư thế (tay, chân, vai, mũi, cổ, lưng)
  - So sánh với golden template
  - Tính severity và deduction
- ✅ `api/local.py` - API routes:
  - POST `/api/local/process-frame` - Xử lý một frame
  - GET `/api/local/{session_id}/notifications` - Lấy lỗi (Practising)
  - GET `/api/local/{session_id}/score` - Lấy điểm hiện tại

### Frontend:
- ✅ `ObservationView.tsx` - Màn hình chấm thí sinh:
  - Popup hiển thị thông tin (tiêu chí, chế độ, thí sinh)
  - Hiển thị 2 cameras
  - Kết nối cameras
  - Phát nhạc (lệnh + nhạc mode)
  - Local Mode:
    - Testing: Hiển thị điểm, trừ điểm, dừng nếu < 50
    - Practising: Stack notifications lỗi
  - Xử lý frame theo chu kỳ (1 giây)
- ✅ `services/localService.ts` - API service
- ✅ `services/audioService.ts` - Audio service

### Config:
- ✅ Thêm `KEYPOINT_INDICES` vào config.py

## ✅ Phase 7: Global Mode (Tổng hợp) (HOÀN THÀNH)

### Backend:
- ✅ `global_controller.py` - Base controller cho Global Mode:
  - `GlobalTestingController` - Testing mode (trừ điểm, dùng lại điểm Local)
  - `GlobalPractisingController` - Practising mode (chỉ hiển thị lỗi)
  - Xử lý frame, phát hiện lỗi tổng hợp, cập nhật điểm
  - Lưu video khi có lỗi
- ✅ Tích hợp AI cho Global Mode:
  - Kiểm tra nhịp nhạc (rhythm) - so sánh với golden template
  - Kiểm tra khoảng cách (distance) - bước chân, vung tay
  - Kiểm tra tốc độ (speed) - động tác quá nhanh/chậm
- ✅ `api/global.py` - API routes:
  - POST `/api/global/process-frame` - Xử lý một frame (với timestamp)
  - GET `/api/global/{session_id}/notifications` - Lấy lỗi (Practising)
  - GET `/api/global/{session_id}/score` - Lấy điểm hiện tại

### Frontend:
- ✅ Cập nhật `ObservationView.tsx`:
  - Tự động chuyển từ Local Mode sang Global Mode
  - Phát nhạc Global Mode sau khi Local Mode kết thúc
  - Bắt đầu ghi video khi vào Global Mode
  - Hiển thị mode indicator (Làm chậm / Tổng hợp)
  - Xử lý frame với timestamp
  - Hiển thị lỗi với video (thay vì snapshot)
- ✅ `services/globalService.ts` - API service

## 📋 Phase 8: AI Integration (CHƯA BẮT ĐẦU)

### Cần tạo:
- `candidate_controller.py`
- `api/candidates.py`
- `ListOfCandidatesView.tsx`
- `CreateCandidateView.tsx`
- Excel import functionality

## 📋 Phase 4-10: (CHƯA BẮT ĐẦU)

Xem chi tiết trong `UPGRADE_PLAN.md`

## Cách chạy

### Backend:
```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

### Test API:
```bash
# Register
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "username": "testuser", "password": "password123"}'

# Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

## Notes

- Database URL cần được cấu hình trong `.env` hoặc `backend/app/config.py`
- JWT secret key cần được set trong environment variable `SECRET_KEY`
- Alembic migrations cần được chạy sau khi setup database:
  ```bash
  alembic revision --autogenerate -m "Initial migration"
  alembic upgrade head
  ```

