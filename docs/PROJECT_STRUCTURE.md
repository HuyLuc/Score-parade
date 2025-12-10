# Cấu trúc dự án mới

## Tổng quan

Dự án đã được cấu trúc lại theo mô hình MVC với backend (FastAPI) và frontend (React).

## Cấu trúc thư mục

```
Score-parade/
├── backend/                    # Backend application
│   ├── app/
│   │   ├── models/             # Database models (8 files)
│   │   │   ├── __init__.py
│   │   │   ├── person.py       # Person, Soldier, Officer
│   │   │   ├── part_of_body.py # PartOfBody và 10 lớp con
│   │   │   ├── score.py        # Score model
│   │   │   ├── criterion.py    # Criterion model
│   │   │   ├── candidate.py    # Candidate model
│   │   │   ├── session.py      # ScoringSession, Error
│   │   │   └── media.py        # Audio, Video
│   │   ├── controllers/        # Controllers (17+ files)
│   │   │   ├── __init__.py
│   │   │   ├── auth_controller.py
│   │   │   ├── candidate_controller.py
│   │   │   ├── camera_controller.py
│   │   │   ├── local_controller.py
│   │   │   ├── global_controller.py
│   │   │   └── ...
│   │   ├── api/                # API routes
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── candidates.py
│   │   │   ├── camera.py
│   │   │   └── scoring.py
│   │   ├── services/           # Core services
│   │   │   ├── __init__.py
│   │   │   ├── pose_service.py      # Wrapper cho PoseEstimator
│   │   │   ├── scoring_service.py    # Logic chấm điểm
│   │   │   ├── audio_service.py      # Xử lý audio
│   │   │   ├── pose_estimation.py    # Pose estimation (từ src/utils)
│   │   │   ├── tracking.py            # Multi-person tracking
│   │   │   ├── video_utils.py         # Video utilities
│   │   │   ├── geometry.py            # Geometry calculations
│   │   │   ├── smoothing.py           # Smoothing algorithms
│   │   │   └── motion_filter.py        # Motion filtering
│   │   ├── database/          # Database setup
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # SQLAlchemy base
│   │   │   ├── session.py      # Session management
│   │   │   └── migrations/     # Alembic migrations
│   │   ├── config.py           # Configuration
│   │   └── main.py             # FastAPI app
│   └── requirements.txt        # Backend dependencies
│
├── frontend/                   # Frontend application
│   ├── src/
│   │   ├── views/              # 9 view files
│   │   │   ├── __init__.ts
│   │   │   ├── RegisterView.tsx
│   │   │   ├── LoginView.tsx
│   │   │   ├── ListOfCandidatesView.tsx
│   │   │   ├── CreateCandidateView.tsx
│   │   │   ├── ConfigurationView.tsx
│   │   │   ├── BaremView.tsx
│   │   │   ├── ObservationView.tsx
│   │   │   ├── EndOfSectionView.tsx
│   │   │   └── SummaryView.tsx
│   │   ├── components/         # Reusable components
│   │   │   └── __init__.ts
│   │   ├── services/          # Frontend services
│   │   │   └── __init__.ts
│   │   └── App.tsx
│   └── package.json
│
├── src/                        # Code cũ (giữ lại để tương thích)
│   ├── step1_golden_template.py
│   ├── step2_feature_extraction.py
│   ├── step3_process_video.py
│   ├── step4_temporal_alignment.py
│   ├── step5_geometric_matching.py
│   ├── step6_scoring.py
│   ├── step7_visualization.py
│   ├── config.py               # Config cũ (giữ lại)
│   ├── manage_golden_template.py
│   └── utils/                   # Utils cũ (đã copy sang backend/app/services)
│
├── data/                       # Data files
│   ├── golden_template/        # Golden templates
│   ├── input_videos/           # Input videos
│   ├── output/                 # Output results
│   ├── models/                 # ML models
│   └── audio/                  # Audio files
│       ├── command/            # Command audio
│       ├── di_deu/
│       │   ├── local/
│       │   └── global/
│       └── di_nghiem/
│           ├── local/
│           └── global/
│
├── main.py                     # CLI entry point (cũ)
├── requirements.txt            # Dependencies cũ
├── README.md
├── UPGRADE_PLAN.md
└── PROJECT_STRUCTURE.md         # File này
```

## Migration từ code cũ

### Imports

**Cũ:**
```python
import src.config as config
from src.utils.pose_estimation import PoseEstimator
```

**Mới:**
```python
import backend.app.config as config
from backend.app.services.pose_estimation import PoseEstimator
```

### Services

Tất cả utils từ `src/utils/` đã được copy sang `backend/app/services/`:
- `pose_estimation.py` → `backend/app/services/pose_estimation.py`
- `tracking.py` → `backend/app/services/tracking.py`
- `video_utils.py` → `backend/app/services/video_utils.py`
- `geometry.py` → `backend/app/services/geometry.py`
- `smoothing.py` → `backend/app/services/smoothing.py`
- `motion_filter.py` → `backend/app/services/motion_filter.py`

### Config

Config mới ở `backend/app/config.py` với các cấu hình bổ sung:
- `DATABASE_CONFIG`
- `API_CONFIG`
- `CAMERA_CONFIG`

## Chạy ứng dụng

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### CLI (code cũ - vẫn hoạt động)

```bash
python main.py --mode step1 --golden-video video.mp4
```

## Lưu ý

1. **Tương thích ngược:** Code cũ trong `src/` vẫn hoạt động, nhưng nên migrate dần sang backend
2. **Imports:** Cần cập nhật imports khi migrate code từ `src/` sang `backend/app/`
3. **Config:** Dùng `backend/app/config.py` cho code mới, `src/config.py` cho code cũ
4. **Services:** Tất cả AI/ML services đã có sẵn trong `backend/app/services/`

