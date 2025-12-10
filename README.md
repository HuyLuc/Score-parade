# Score Parade - Hệ thống chấm điều lệnh tự động

Hệ thống AI để đánh giá và chấm điểm động tác điều lệnh quân đội.

## Cấu trúc dự án

Dự án được tổ chức theo mô hình MVC:

```
Score-parade/
├── backend/          # FastAPI backend
├── frontend/         # React frontend
├── src/             # Code CLI cũ (tương thích ngược)
└── data/            # Dữ liệu (videos, models, audio)
```

Xem chi tiết: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

## Quick Start

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

### CLI (Code cũ)

```bash
# Tạo golden template
python main.py --mode step1 --golden-video data/golden_template/video.mp4 --multi-person

# Chấm video
python main.py --mode full --input-video data/input_videos/video.mp4
```

## Tính năng

- ✅ Hỗ trợ nhiều người trong golden template
- ✅ Hỗ trợ nhiều góc quay
- ✅ Tự động chọn profile phù hợp
- ✅ Multi-person tracking
- ✅ Real-time scoring
- ✅ Web interface (đang phát triển)

## Tài liệu

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Cấu trúc dự án
- [UPGRADE_PLAN.md](UPGRADE_PLAN.md) - Kế hoạch nâng cấp
- [GOLDEN_TEMPLATE_USAGE.md](GOLDEN_TEMPLATE_USAGE.md) - Hướng dẫn golden template
- [QUICK_START.md](QUICK_START.md) - Hướng dẫn nhanh

## Requirements

- Python 3.8+
- Node.js 18+
- PostgreSQL (cho backend mới)
- CUDA (tùy chọn, cho GPU acceleration)
