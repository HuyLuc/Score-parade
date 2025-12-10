# Score Parade Backend

Backend API cho hệ thống chấm điều lệnh tự động.

## Tech Stack

- FastAPI
- PostgreSQL + SQLAlchemy
- Python 3.8+

## Setup

```bash
# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Chạy migrations (khi có database)
alembic upgrade head

# Chạy server
python -m app.main
# hoặc
uvicorn app.main:app --reload
```

## Cấu trúc

- `app/models/` - Database models
- `app/controllers/` - Business logic controllers
- `app/api/` - API routes
- `app/services/` - Core services (AI, scoring, audio)
- `app/database/` - Database setup và migrations

## Environment Variables

Tạo file `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost/score_parade
SECRET_KEY=your-secret-key
```

