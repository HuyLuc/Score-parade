# Cấu trúc thư mục (gọn gàng)

```
Score-parade/
├── backend/                # FastAPI backend (API, AI controllers, services)
│   ├── app/
│   │   ├── api/            # auth, candidates, camera, local, global, results
│   │   ├── controllers/    # business logic (local/global, AI, camera, etc.)
│   │   ├── services/       # pose, tracking, geometry, motion_filter, scoring
│   │   ├── models/         # DB models
│   │   ├── database/       # Base + migrations
│   │   └── config.py       # Backend config (SCORING_CONFIG, ERROR_THRESHOLDS, ...)
│   └── requirements.txt
├── frontend/               # React frontend
│   └── src/
│       ├── views/          # Register, Login, Observation, EndOfSection, Summary, ...
│       ├── components/     # CameraView, ...
│       └── services/       # API clients (auth, candidates, camera, local/global, results)
├── src/                    # Legacy CLI pipeline (giữ để tương thích)
│   ├── step1..7_*.py       # Các bước pipeline cũ
│   └── utils/              # Pose/tracking/geometry utils (phiên bản cũ)
├── data/                   # Dữ liệu (golden_template, input_videos, output, models, audio)
├── docs/                   # Tài liệu (file này, GOLDEN_TEMPLATE_MULTI_PERSON, ...)
├── main.py                 # CLI entry cũ
├── requirements.txt        # Dependencies cho CLI cũ
└── README.md
```

Ghi chú:
- Backend + frontend là luồng chính (API + web app).
- Thư mục `src/` giữ pipeline CLI cũ để tham chiếu/so sánh; code mới đã được port vào `backend/app/services` và controllers.
- Tài liệu chi tiết: `PROJECT_STRUCTURE.md`, `UPGRADE_PLAN.md`, `GOLDEN_TEMPLATE_USAGE.md`, `GOLDEN_TEMPLATE_MULTI_PERSON.md`.

