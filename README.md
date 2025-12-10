# Score Parade - Hệ thống chấm điều lệnh tự động

Hệ thống AI để đánh giá và chấm điểm động tác điều lệnh quân đội.

## Cấu trúc dự án

- `backend/`: FastAPI backend (API, local/global controllers, AI, camera, DB)
- `frontend/`: React frontend (Observation, EndOfSection, Summary, Auth)
- `data/`: Dữ liệu (golden_template, input_videos, output, models, audio)
- `docs/`: Tài liệu (project structure, upgrade plan, golden template usage)

## Quick Start

### Backend (chạy trực tiếp)

```bash
cd backend
pip install -r requirements.txt
# (tuỳ chọn) Tạo .env: DATABASE_URL=postgresql://user:password@localhost/score_parade, SECRET_KEY=...
# (tuỳ chọn) alembic upgrade head  # nếu cần migrations
cd ..  # quay về thư mục gốc dự án
python -m backend.app.main  # chạy API (mặc định http://localhost:8000)
# mở docs: http://localhost:8000/docs
```

### Frontend (chạy trực tiếp)

```bash
cd frontend
npm install
# nếu backend không ở http://localhost:8000, đặt REACT_APP_API_URL
npm start
```

### Quy trình test nhanh
- Đăng ký → Đăng nhập
- Import/Tạo thí sinh
- Cấu hình (mode testing/practising, tiêu chí đi đều/đi nghiêm, độ khắt khe)
- Barem: chỉnh trọng số nếu cần
- Observation: kết nối camera, phát lệnh + nhạc, chạy Local → Global
- EndOfSection: xem lỗi (ảnh/video), điểm
- Summary: bảng kết quả, xoá session (nếu muốn)

## Tính năng

- ✅ Hỗ trợ nhiều người trong golden template
- ✅ Hỗ trợ nhiều góc quay
- ✅ Tự động chọn profile phù hợp
- ✅ Multi-person tracking
- ✅ Real-time scoring
- ✅ Web interface (đang phát triển)

## Tài liệu

- [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) - Cấu trúc dự án
- [docs/UPGRADE_PLAN.md](docs/UPGRADE_PLAN.md) - Kế hoạch nâng cấp
- [docs/GOLDEN_TEMPLATE_USAGE.md](docs/GOLDEN_TEMPLATE_USAGE.md) - Hướng dẫn golden template
- [docs/QUICK_START.md](docs/QUICK_START.md) - Hướng dẫn nhanh

## Requirements

- Python 3.8+
- Node.js 18+
- PostgreSQL (cho backend mới) hoặc SQLite cho môi trường demo
- CUDA (tùy chọn, cho GPU acceleration)

## Chạy bằng Docker

Yêu cầu: Docker + Docker Compose.

```bash
# build & run
docker-compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

Mặc định dùng PostgreSQL trong compose với URL `postgresql://postgres:postgres@db:5432/score_parade`.

Nếu muốn thay API URL cho frontend khi build, chỉnh trong `docker-compose.yml`:
```yaml
frontend:
  build:
    args:
      REACT_APP_API_URL: http://backend:8000
```

Lưu ý: Backend auto tạo bảng khi khởi động (startup init_db). Nếu dùng Postgres thật, hãy tạo DB/USER phù hợp và đặt `DATABASE_URL`.
