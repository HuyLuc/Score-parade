# Kế hoạch nâng cấp hệ thống chấm điều lệnh tự động

## Tổng quan

Nâng cấp hệ thống từ batch processing CLI thành ứng dụng web hoàn chỉnh theo tài liệu yêu cầu.

**Tech Stack:**
- Backend: FastAPI + PostgreSQL + SQLAlchemy
- Frontend: React + TypeScript
- Real-time: WebSocket cho camera streaming
- Audio: Web Audio API

## Phân tích yêu cầu từ tài liệu

### Models (8 lớp)
1. Person → Soldier, Officer
2. PartOfBody → Nose, Neck, Shoulder, Arm, Elbow, Fist, Hand, Back, Knee, Foot
3. Score
4. Criterion
5. Candidate
6. ScoringSession
7. Error
8. Audio/Video

### Views (9 màn hình)
1. RegisterView
2. LoginView
3. ListOfCandidatesView
4. CreateCandidateView
5. ConfigurationView
6. BaremView
7. ObservationView
8. EndOfSectionView
9. SummaryView

### Controllers (17 lớp)
1. RegisterController
2. LoginController
3. DBController
4. CandidateController
5. ConfigurationController
6. BaremController
7. DifficultController
8. CameraController
9. SnapshotController
10. VideoController
11. AudioService
12. LocalController → LocalTestingController, LocalPractisingController
13. GlobalController → GlobalTestingController, GlobalPractisingController
14. AIController
15. ScoringService
16. EndOfSectionController
17. SummaryController
18. LogController → DevController, ReleaseController

## Luồng chấm thí sinh (chi tiết theo tài liệu)

### ObservationView - Luồng chấm (dòng 104-128):

1. **Khởi tạo:**
   - Hiển thị popup: tiêu chí (đi đều/đi nghiêm), chế độ (kiểm tra/luyện tập), thông tin thí sinh
   - CameraController kết nối 2 camera
   - Hiển thị hình ảnh từ 2 camera

2. **Chọn thí sinh:**
   - User chọn từ danh sách (nếu cần)
   - CandidateController hiển thị giao diện chọn
   - OK → phát nhạc / Cancel → ListOfCandidatesView

3. **Phát nhạc:**
   - Phát "Nghiêm. Đi đều bước" trước
   - Phát nhạc theo: đi đều/đi nghiêm, làm chậm/tổng hợp, kiểm tra/luyện tập

4. **Làm chậm (Local Mode):**
   - LocalTestingController hoặc LocalPractisingController
   - SnapshotController lấy frame theo chu kỳ
   - AIController phát hiện lỗi (tay, chân, vai, mũi, cổ, lưng - chỉ tư thế)
   - **Testing mode:** Điểm ban đầu 100, trừ dần, hiển thị lỗi
   - **Practising mode:** Chỉ hiển thị lỗi (stack notifications)
   - SnapshotController lưu ảnh lỗi
   - Nếu điểm < 50 → EndOfSectionView

5. **Tổng hợp (Global Mode):**
   - Tự động chuyển sang GlobalTestingController hoặc GlobalPractisingController
   - Phát nhạc
   - VideoController lấy video frames theo chu kỳ
   - AIController kiểm tra:
     - (i) Nhịp nhạc
     - (ii) Khoảng cách (bước chân, vung tay)
     - (iii) Tốc độ
   - **Testing mode:** Dùng lại điểm làm chậm, trừ dần, hiển thị lỗi
   - **Practising mode:** Chỉ hiển thị lỗi
   - VideoController lưu video lỗi
   - Nếu điểm < 50 → EndOfSectionView

6. **Kết thúc:**
   - Chuyển EndOfSectionView
   - Hiển thị lỗi theo tabs: làm chậm, nhịp, khoảng cách, tốc độ
   - Xem ảnh (làm chậm) hoặc video (tổng hợp) lỗi

## Cấu trúc dự án mới

```
Score-parade/
├── backend/
│   ├── app/
│   │   ├── models/              # 8 model files
│   │   │   ├── person.py
│   │   │   ├── part_of_body.py
│   │   │   ├── score.py
│   │   │   ├── criterion.py
│   │   │   ├── candidate.py
│   │   │   ├── session.py
│   │   │   └── media.py
│   │   ├── controllers/         # 17+ controller files
│   │   │   ├── auth_controller.py
│   │   │   ├── candidate_controller.py
│   │   │   ├── camera_controller.py
│   │   │   ├── local_controller.py
│   │   │   ├── global_controller.py
│   │   │   └── ...
│   │   ├── api/                 # API routes
│   │   │   ├── auth.py
│   │   │   ├── candidates.py
│   │   │   ├── camera.py
│   │   │   └── scoring.py
│   │   ├── services/            # Core services
│   │   │   ├── pose_service.py
│   │   │   ├── scoring_service.py
│   │   │   └── audio_service.py
│   │   ├── database/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── migrations/
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/               # 9 view files
│   │   │   ├── RegisterView.tsx
│   │   │   ├── LoginView.tsx
│   │   │   ├── ListOfCandidatesView.tsx
│   │   │   └── ...
│   │   ├── components/
│   │   ├── services/
│   │   └── App.tsx
│   └── package.json
├── src/                         # Code cũ (giữ lại)
└── data/audio/                  # Audio files
```

## Thứ tự triển khai (12 Phases)

### Phase 1: Database Foundation
**Files:**
- `backend/app/models/person.py` - Person, Soldier, Officer
- `backend/app/models/part_of_body.py` - PartOfBody và 10 lớp con
- `backend/app/models/score.py` - Score model
- `backend/app/models/criterion.py` - Criterion model
- `backend/app/models/candidate.py` - Candidate model
- `backend/app/models/session.py` - ScoringSession, Error
- `backend/app/models/media.py` - Audio, Video
- `backend/app/database/base.py` - SQLAlchemy setup
- `backend/app/database/session.py` - Session management
- `alembic.ini` + migrations

### Phase 2: Authentication
**Files:**
- `backend/app/controllers/register_controller.py`
- `backend/app/controllers/login_controller.py`
- `backend/app/controllers/db_controller.py`
- `backend/app/api/auth.py`
- `frontend/src/views/RegisterView.tsx`
- `frontend/src/views/LoginView.tsx`

**Luồng (dòng 54-70):**
- Register: Validate → Check duplicate → Create → Success message
- Login: Validate → Authenticate → Generate token → Redirect

### Phase 3: Candidate Management
**Files:**
- `backend/app/controllers/candidate_controller.py`
- `backend/app/api/candidates.py`
- `frontend/src/views/ListOfCandidatesView.tsx`
- `frontend/src/views/CreateCandidateView.tsx`

**Luồng (dòng 72-85):**
- Import Excel → Validate → Insert → Select first
- Create manual → Validate → Insert → Select new
- Edit/Delete candidates

### Phase 4: Configuration & Barem
**Files:**
- `backend/app/controllers/configuration_controller.py`
- `backend/app/controllers/barem_controller.py`
- `backend/app/controllers/difficult_controller.py`
- `backend/app/api/configuration.py`
- `backend/app/api/barem.py`
- `frontend/src/views/ConfigurationView.tsx`
- `frontend/src/views/BaremView.tsx`

**Luồng (dòng 87-102):**
- Barem: Load criteria → Adjust weights → Validate → Update
- Config: Set mode/criteria/strictness/operation → Create controllers

### Phase 5: Camera & Media
**Files:**
- `backend/app/controllers/camera_controller.py`
- `backend/app/controllers/snapshot_controller.py`
- `backend/app/controllers/video_controller.py`
- `backend/app/services/audio_service.py`
- `backend/app/api/camera.py`
- `frontend/src/components/CameraView.tsx`

**Luồng (dòng 107-108):**
- Connect 2 cameras → Stream → Auto reconnect

### Phase 6: AI & Scoring Services
**Files:**
- `backend/app/services/pose_service.py` (tích hợp src/utils/)
- `backend/app/services/geometry_service.py` (tích hợp src/utils/)
- `backend/app/services/scoring_service.py` (tích hợp src/step4-6)
- `backend/app/services/golden_template_service.py` (tích hợp src/step1-2)
- `backend/app/controllers/ai_controller.py`
- `backend/app/controllers/scoring_service.py`

### Phase 7: Local Mode (Làm chậm)
**Files:**
- `backend/app/controllers/local_controller.py` (base)
- `backend/app/controllers/local_testing_controller.py`
- `backend/app/controllers/local_practising_controller.py`
- `backend/app/api/scoring.py` (local endpoints)

**Luồng (dòng 114-119):**
- Testing: Score 100 → Detect errors → Deduct → Stop if < 50
- Practising: Detect errors → Stack notifications only

### Phase 8: Global Mode (Tổng hợp)
**Files:**
- `backend/app/controllers/global_controller.py` (base)
- `backend/app/controllers/global_testing_controller.py`
- `backend/app/controllers/global_practising_controller.py`
- `backend/app/api/scoring.py` (global endpoints)

**Luồng (dòng 122-127):**
- Check: (i) Nhịp nhạc, (ii) Khoảng cách, (iii) Tốc độ
- Testing: Reuse score → Deduct → Stop if < 50
- Practising: Show errors only

### Phase 9: Observation View
**Files:**
- `frontend/src/views/ObservationView.tsx`
- Integration với camera, audio, scoring APIs

**Luồng (dòng 104-128):**
- Popup → 2 cameras → Select candidate → Play audio → Local mode → Global mode → EndOfSectionView

### Phase 10: Results & Summary
**Files:**
- `backend/app/controllers/end_of_section_controller.py`
- `backend/app/controllers/summary_controller.py`
- `backend/app/api/results.py`
- `frontend/src/views/EndOfSectionView.tsx`
- `frontend/src/views/SummaryView.tsx`

**Luồng (dòng 130-144):**
- EndOfSection: Tabs (làm chậm, nhịp, khoảng cách, tốc độ) → View image/video → Next/Finish
- Summary: Table (STT, thí sinh, thời điểm, điểm) → Delete → Resume/Finish

### Phase 11: Audio Files Setup
**Files:**
- `data/audio/command/nghiem_di_deu_buoc.mp3`
- `data/audio/di_deu/local/testing_short.mp3`
- `data/audio/di_deu/local/practising_long.mp3`
- `data/audio/di_deu/global/total.mp3`
- `data/audio/di_nghiem/...` (tương tự)

## Phase 11.5: Nâng cấp Golden Template - Hỗ trợ nhiều người và góc quay

### Yêu cầu mới:
- Golden template có thể chứa 2-3 người
- Hỗ trợ nhiều góc quay (nhiều video hoặc một video với nhiều cảnh)
- Tạo profile cho từng người và/hoặc góc quay
- Khi so sánh, tự động chọn profile phù hợp nhất

### Cấu trúc dữ liệu mới:

**File: `backend/app/models/golden_template.py`**
```python
class GoldenTemplate(Base):
    id, name, description, created_at

class GoldenPerson(Base):
    id, template_id (FK), person_index, camera_angle, 
    skeleton_path, profile_path

class GoldenProfile(Base):
    id, golden_person_id (FK), statistics (JSON)
```

### Cập nhật Step 1:

**File: `src/step1_golden_template_multi.py`** (mới)
- Detect tất cả người trong video
- Tracking để phân biệt từng người
- Lưu skeleton cho từng người
- Hỗ trợ metadata: camera_angle, person_index

### Cập nhật Step 2:

**File: `src/step2_feature_extraction_multi.py`** (mới)
- Trích xuất profile cho từng người
- Lưu profile riêng biệt
- Tạo profile tổng hợp (trung bình) nếu cần

### Cập nhật Step 5 (So sánh):

**File: `src/step5_geometric_matching.py`** (cập nhật)
- Tự động chọn golden profile phù hợp nhất:
  - So sánh với tất cả profiles
  - Chọn profile có similarity cao nhất
  - Hoặc chọn profile theo camera angle tương tự

### Cấu trúc thư mục mới:

```
data/golden_template/
├── template_1/
│   ├── video.mp4
│   ├── person_0/
│   │   ├── skeleton.pkl
│   │   └── profile.json
│   ├── person_1/
│   │   ├── skeleton.pkl
│   │   └── profile.json
│   └── metadata.json
├── template_2/ (góc quay khác)
│   └── ...
└── template_combined/ (profile tổng hợp)
    └── profile.json
```

### API mới:

**File: `backend/app/api/golden_template.py`**
- `POST /api/golden-template` - Tạo template mới
- `POST /api/golden-template/{id}/add-person` - Thêm người vào template
- `GET /api/golden-template/{id}/profiles` - Lấy tất cả profiles
- `POST /api/golden-template/{id}/select-profile` - Chọn profile để dùng

### Phase 12: Testing & Deployment
- Unit tests
- Integration tests
- E2E tests
- Docker setup
- Deployment scripts

## Lưu ý quan trọng

1. **Giữ nguyên code cũ** trong `src/` để tái sử dụng
2. **Tích hợp từng phần** - test kỹ trước khi chuyển phase
3. **WebSocket** cho real-time camera streaming
4. **Audio timing** phải chính xác
5. **Database migrations** version control
6. **JWT authentication** cho security
7. **Error handling** và logging đầy đủ

## Các điểm quan trọng từ tài liệu

- **Điểm ban đầu:** 100 (chỉ testing mode)
- **Điểm trượt:** < 50 (tự động dừng)
- **Làm chậm:** Chỉ xét tư thế (tay, chân, vai, mũi, cổ, lưng)
- **Tổng hợp:** Xét nhịp, khoảng cách, tốc độ
- **Nhạc:** "Nghiêm. Đi đều bước" trước mỗi bài
- **Lỗi làm chậm:** Lưu ảnh
- **Lỗi tổng hợp:** Lưu video
- **Practising mode:** Chỉ hiển thị lỗi, không trừ điểm
