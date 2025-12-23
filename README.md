# 🎵 Score Parade – Chấm Điều Lệnh Tự Động

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-pytest-orange.svg)](https://docs.pytest.org/)

**Score Parade** là hệ thống chấm điểm điều lệnh tự động sử dụng AI, phân tích video chiến sĩ/sĩ quan thực hành đi điều lệnh và cung cấp phản hồi theo thời gian thực (Local Mode – Làm chậm) và bài tổng hợp (Global Mode). Hệ thống sử dụng **MMPose (RTMPose)** cho ước tính tư thế với độ chính xác cao, ByteTrack cho theo dõi nhiều người, beat detection để kiểm tra nhịp, và cơ chế nhóm lỗi theo chuỗi để tránh trừ điểm quá mức.

## ✨ Tính năng chính (theo trạng thái hiện tại)

- 🎯 **Phân tích tư thế thời gian thực (Local Mode – Làm chậm)**  
  - Kiểm tra tay, chân, vai, đầu, cổ, lưng theo từng frame với 1 camera.  
  - Chế độ **Testing**: trừ điểm dần, dừng khi điểm dưới ngưỡng.  
  - Chế độ **Practising**: không trừ điểm, chỉ hiển thị lỗi (có đọc lỗi bằng TTS).

- 🌍 **Chấm “Tổng hợp” (Global Mode)**  
  - Giám sát thời gian thực qua webcam hoặc upload video.  
  - Chấm tư thế + nhịp (beat detection) + multi-person tracking (ByteTrack).  
  - Nhóm lỗi liên tiếp thành chuỗi để tránh trừ điểm quá nhiều.

- 👤 **Quản lý tài khoản & thí sinh**  
  - Đăng ký / đăng nhập / đổi mật khẩu (Auth + JWT).  
  - Quản lý danh sách thí sinh, import từ Excel, chọn thí sinh cho từng session (Local & Global).

- ⚙️ **Cấu hình chấm điểm & Barem**  
  - Điều chỉnh trọng số từng loại lỗi, ngưỡng phát hiện, độ khắt khe (easy/medium/hard), tiêu chí đi đều/đi nghiêm, app_mode (dev/release).  
  - Xem và chỉnh Barem trực tiếp trên frontend.

- 🎼 **Beat detection & skeleton video**  
  - Upload/chọn file audio khi khởi tạo Global Mode để kiểm tra nhịp so với bước chân.  
  - Sau khi upload video, backend tạo video skeleton overlay (kèm bản H.264/AAC thân thiện trình duyệt).

- 🗄️ **Hạ tầng backend**  
  - FastAPI + PostgreSQL, connection pooling, khởi tạo DB qua `docker/init-db.sql`.  
  - Lưu `sessions`, `persons`, `errors`, `golden_templates`, `configs` với index tối ưu.

- 🖥️ **Frontend React + TypeScript**  
  - Dashboard, Candidates, Settings, Barem, Real-time Monitoring (Global), Local Mode, Upload Video, Results, Sessions, Comparison.

## 📊 Chỉ Số Hiệu Suất

| Chỉ Số | Giá Trị | Mô Tả |
|--------|--------|-------|
| **Độ Chính Xác** | 94.2% | Độ chính xác phát hiện tư thế trung bình |
| **Tốc Độ Xử Lý** | 30 FPS | Khả năng phân tích video thời gian thực |
| **Độ Trễ** | <50ms | Thời gian xử lý mỗi khung hình |
| **Sử Dụng Bộ Nhớ** | ~800MB | Mức tiêu thụ RAM trung bình |
| **Định Dạng Hỗ Trợ** | MP4, AVI, MOV, MKV | Định dạng video đầu vào |
| **Độ Phân Giải Tối Đa** | 1920x1080 | Độ phân giải xử lý tối ưu |

## 📁 Cấu trúc dự án

```
Score-parade/
├── backend/                           # Backend API (FastAPI)
│   ├── app/
│   │   ├── api/                      # API routes
│   │   │   ├── auth.py               # Auth endpoints
│   │   │   ├── candidates.py         # Quản lý thí sinh
│   │   │   ├── barem.py              # Barem & cấu hình chấm điểm
│   │   │   ├── global_mode.py        # Global mode endpoints
│   │   │   └── local_mode.py         # Local mode (Làm chậm) endpoints
│   │   ├── controllers/              # Business logic controllers
│   │   │   ├── ai_controller.py      # Phát hiện lỗi tư thế, sequence scoring
│   │   │   ├── global_controller.py  # Base Global Mode controller
│   │   │   ├── global_testing_controller.py
│   │   │   ├── global_practising_controller.py
│   │   │   ├── local_testing_controller.py
│   │   │   └── local_practising_controller.py
│   │   ├── services/                 # Core services
│   │   │   ├── pose_service.py       # MMPose pose detection
│   │   │   ├── scoring_service.py    # Scoring logic
│   │   │   ├── bytetrack_service.py  # Multi-person tracking
│   │   │   ├── tracker_service.py    # SORT-style tracker
│   │   │   ├── beat_detection.py     # Phát hiện beat nhạc
│   │   │   ├── sequence_comparison.py# Nhóm lỗi theo chuỗi
│   │   │   ├── video_utils.py        # Load/validate video
│   │   │   └── skeleton_visualization.py # Tạo skeleton video
│   │   ├── utils/                    # Utilities (video validator, cache, progress...)
│   │   ├── config.py                 # Configuration
│   │   └── main.py                   # FastAPI app entry
│   ├── requirements.txt              # Python dependencies
│   └── tests/                        # Backend tests
├── frontend/                          # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── pages/                    # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── VideoUpload.tsx
│   │   │   ├── RealTimeMonitoring.tsx   # Global Mode (tổng hợp, realtime)
│   │   │   ├── LocalMode.tsx           # Local Mode (Làm chậm, realtime)
│   │   │   ├── Results.tsx
│   │   │   ├── Sessions.tsx
│   │   │   ├── Candidates.tsx
│   │   │   ├── Barem.tsx
│   │   │   ├── Settings.tsx
│   │   │   ├── Login.tsx / Register.tsx
│   │   │   └── Comparison.tsx
│   │   ├── components/               # Layout, charts, skeleton drawer...
│   │   ├── services/                 # API services
│   │   └── store/                    # State management
│   ├── package.json
│   └── vite.config.ts
├── docker/                            # Docker configuration
│   └── init-db.sql                   # Database initialization
├── data/                              # Data directory
│   ├── golden_template/              # Golden template files
│   ├── input_videos/                 # Input videos
│   ├── output/                       # Output videos
│   └── models/                       # Model files
├── Dockerfile                         # Docker image definition
├── docker-compose.yml                 # Docker Compose config
├── env.example                        # Environment variables template
├── .dockerignore                      # Docker ignore patterns
├── .gitignore
└── README.md
```

## 🚀 Cài Đặt

### Yêu Cầu

**Cho Development:**
- Python 3.11 trở lên
- Node.js 16+ và npm
- PostgreSQL 15+ (hoặc Docker)
- FFmpeg (để xử lý video)

**Cho Production:**
- Docker và Docker Compose
- Hoặc cài đặt thủ công như development

### Cách 1: Cài Đặt Với Docker (Khuyến Nghị)

**Bước 1: Clone Repository**

```bash
git clone https://github.com/HuyLuc/Score-parade.git
cd Score-parade
```

**Bước 2: Cấu Hình Environment**

```bash
# Copy file mẫu environment
cp env.example .env

# Chỉnh sửa .env nếu cần (mặc định đã đủ để chạy)
# POSTGRES_USER=scoreuser
# POSTGRES_PASSWORD=scorepass123
# POSTGRES_DB=score_parade
```

**Bước 3: Build và Chạy với Docker Compose**

```bash
# Build và khởi động tất cả services (database + app)
docker-compose up -d --build

# Xem logs
docker-compose logs -f app

# Hoặc xem logs của database
docker-compose logs -f db
```

**Bước 4: Truy Cập Ứng Dụng**

- **Frontend + API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

**Bước 5: Database Management (Tùy chọn - Development)**

```bash
# Khởi động Adminer (Database UI)
docker-compose --profile dev up -d adminer

# Truy cập Adminer tại: http://localhost:8080
# Server: db
# Username: scoreuser
# Password: scorepass123
# Database: score_parade
```

**Các Lệnh Docker Hữu Ích:**

```bash
# Dừng tất cả services
docker-compose down

# Dừng và xóa volumes (xóa database)
docker-compose down -v

# Rebuild lại image
docker-compose build --no-cache

# Xem trạng thái services
docker-compose ps

# Restart một service cụ thể
docker-compose restart app
```

### Cách 2: Cài Đặt Thủ Công (Development)

**Bước 1: Clone Repository**

```bash
git clone https://github.com/HuyLuc/Score-parade.git
cd Score-parade
```

### Bước 2: Tạo Môi Trường Ảo

```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Hoặc nếu gặp lỗi execution policy:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# .\venv\Scripts\Activate.ps1

# Trên Windows (CMD):
# venv\Scripts\activate.bat

# Trên macOS/Linux:
# source venv/bin/activate
```

### Bước 3: Cài Đặt Phụ Thuộc Backend

```bash
# Cài đặt phụ thuộc Python cho backend
cd backend
pip install -r requirements.txt

# Quay lại thư mục gốc
cd ..
```

### Bước 3.1: Cài Đặt MMPose (QUAN TRỌNG)

**Cách 1: Tự động (Khuyến nghị)**
```bash
# Chạy script tự động cài đặt MMPose
python install_mmpose.py
```

**Cách 2: Thủ công**
```bash
# Cài đặt OpenMMLab MIM
pip install -U openmim

# Cài đặt MMPose stack
mim install mmengine
mim install "mmcv>=2.0.0"
mim install "mmpose>=1.0.0"

# Xác minh cài đặt
python -c "from mmpose.apis import MMPoseInferencer; print('✅ MMPose OK')"
```

**Lưu ý:** MMPose là thư viện chính để phát hiện pose với độ chính xác cao. Xem thêm chi tiết tại [POSE_MODEL_MIGRATION.md](POSE_MODEL_MIGRATION.md).

### Bước 4: Cài Đặt Phụ Thuộc Frontend

```bash
# Cài đặt Node.js dependencies (yêu cầu Node.js 16+)
cd frontend
npm install

# Quay lại thư mục gốc
cd ..
```

### Bước 5: Cài Đặt FFmpeg

**Windows:**
```bash
# Sử dụng Chocolatey
choco install ffmpeg

# Hoặc tải từ https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### Bước 6: Cấu Hình Database

**Cài đặt PostgreSQL:**

**Windows:**
```bash
# Sử dụng Chocolatey
choco install postgresql15

# Hoặc tải từ https://www.postgresql.org/download/windows/
```

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-contrib-15
sudo systemctl start postgresql
```

**Tạo Database:**

```bash
# Kết nối PostgreSQL
psql -U postgres

# Tạo database và user
CREATE DATABASE score_parade;
CREATE USER scoreuser WITH PASSWORD 'scorepass123';
GRANT ALL PRIVILEGES ON DATABASE score_parade TO scoreuser;
\q

# Chạy script khởi tạo schema
psql -U scoreuser -d score_parade -f docker/init-db.sql
```

### Bước 7: Cấu Hình Môi Trường

```bash
# Sao chép mẫu biến môi trường
cp env.example .env

# Chỉnh sửa file .env với cài đặt của bạn
# Đặc biệt là DATABASE_URL:
# DATABASE_URL=postgresql://scoreuser:scorepass123@localhost:5432/score_parade
nano .env
```

### Bước 8: Xác Minh Cài Đặt

```bash
# Kiểm tra backend dependencies
python -c "import cv2; import numpy; import mmpose; print('✅ Backend dependencies OK')"

# Kiểm tra frontend
cd frontend
npm list --depth=0
cd ..
```

## 💻 Sử dụng

### 🚀 Chạy ứng dụng

#### Cách 1: Chạy full stack (Backend + Frontend)

**Bước 1: Khởi động Backend API**

Mở Terminal 1:
```bash
# Từ thư mục gốc của project
cd F:\Score-parade\Score-parade

# Chạy backend
python -c "import sys; sys.path.insert(0, '.'); from backend.app.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"
```

Hoặc sử dụng uvicorn trực tiếp:
```bash
# Cài đặt uvicorn nếu chưa có
pip install uvicorn

# Chạy từ thư mục gốc
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend sẽ chạy tại: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

**Bước 2: Khởi động Frontend**

Mở Terminal 2 (PowerShell hoặc Command Prompt):
```bash
# Vào thư mục frontend (từ thư mục gốc project)
cd F:\Score-parade\Score-parade\frontend

# Cài đặt dependencies (chỉ lần đầu tiên)
npm install

# Chạy development server

```

Frontend sẽ chạy tại: `http://localhost:3000`

**Lưu ý:**
- ✅ Đảm bảo backend đã chạy trước khi mở frontend
- ✅ Kiểm tra file `frontend/.env` có `VITE_API_URL=http://localhost:8000`
- ✅ Nếu port 3000 đã được sử dụng, Vite sẽ tự động đề xuất port khác

**Kiểm tra kết nối:**
- Mở trình duyệt và truy cập `http://localhost:3000`
- Dashboard sẽ hiển thị trạng thái kết nối backend
- Nếu thấy "Backend API: Hoạt động bình thường" là thành công!

**Troubleshooting:**
- Nếu backend không chạy được, đảm bảo bạn đang ở thư mục gốc và đã cài đặt tất cả dependencies
- Nếu frontend không kết nối được backend, kiểm tra file `frontend/.env` có `VITE_API_URL=http://localhost:8000`
- Nếu port 8000 hoặc 3000 đã được sử dụng, dừng process cũ hoặc đổi port

#### Cách 2: Chạy CLI Scoring (không cần frontend)

Sử dụng script CLI `run_scoring.py` để tạo golden template và chấm điểm video:

```bash
# Tạo golden template từ video mẫu
python run_scoring.py create_golden "data/golden_template/golden_video.mp4" --output-dir data/golden_template

# Đánh giá video test so với golden template
python run_scoring.py evaluate "data/input_videos/video1.mp4" --golden-dir data/golden_template --output-dir data/output
```

### 🌐 API backend hiện tại

#### Khởi Động Máy Chủ Backend

**Cách 1: Sử dụng uvicorn (Khuyến nghị)**
```bash
# Đảm bảo bạn đang ở thư mục GỐC của project
cd F:\Score-parade\Score-parade

# Cài đặt uvicorn nếu chưa có
pip install uvicorn

# Chạy backend từ thư mục gốc
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Cách 2: Sử dụng Python trực tiếp**
```bash
# Từ thư mục gốc project
cd F:\Score-parade\Score-parade
python -c "import sys; sys.path.insert(0, '.'); from backend.app.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000, reload=True)"
```

**Lưu ý:**
- ⚠️ **QUAN TRỌNG:** Luôn chạy từ **thư mục gốc** của project, không phải từ thư mục `backend/`
- ✅ Sử dụng `python -m uvicorn` để đảm bảo Python tìm đúng module paths
- ✅ Flag `--reload` cho phép tự động reload khi code thay đổi (chỉ dùng trong development)

#### Điểm cuối cơ bản

**1. Kiểm tra sức khỏe**
```bash
curl http://localhost:8000/health
```

**2. Bắt đầu session (Global Mode)**
```bash
curl -X POST http://localhost:8000/api/global/{session_id}/start \
  -F "mode=testing" \
  -F "audio_file=@path/to/audio.wav"
```

**3. Xử lý frame (Global Mode)**
```bash
curl -X POST http://localhost:8000/api/global/{session_id}/process-frame \
  -F "frame_data=@frame.jpg" \
  -F "timestamp=123.45" \
  -F "frame_number=1"
```

**4. Lấy điểm số (Global Mode)**
```bash
curl http://localhost:8000/api/global/{session_id}/score
```

**5. Lấy danh sách lỗi (Global Mode)**
```bash
curl http://localhost:8000/api/global/{session_id}/errors
```

**6. Reset session (Global Mode)**
```bash
curl -X POST http://localhost:8000/api/global/{session_id}/reset
```

**7. Xóa session (Global Mode)**
```bash
curl -X DELETE http://localhost:8000/api/global/{session_id}
```

**8. Local Mode – Làm chậm**

- `POST /api/local/{session_id}/start` (form: `mode`, `candidate_id?`)  
- `POST /api/local/{session_id}/process-frame` (frame_data, timestamp, frame_number)  
- `GET /api/local/{session_id}/score`  
- `GET /api/local/{session_id}/errors`  
- `POST /api/local/{session_id}/reset`  
- `DELETE /api/local/{session_id}`

> Chi tiết xem trong `backend/app/api/global_mode.py` và `backend/app/api/local_mode.py`.

### 🎨 Frontend web interface

#### Khởi Động Frontend

```bash
# Vào thư mục frontend (từ thư mục gốc project)
cd F:\Score-parade\Score-parade\frontend

# Cài đặt dependencies (chỉ lần đầu tiên)
npm install

# Chạy development server
npm run dev
```

Frontend sẽ chạy tại: `http://localhost:3000`

**Lưu ý:**
- ✅ Đảm bảo backend đã chạy trước khi mở frontend
- ✅ Kiểm tra file `frontend/.env` có `VITE_API_URL=http://localhost:8000`
- ✅ Nếu port 3000 đã được sử dụng, Vite sẽ tự động đề xuất port khác

#### Các trang chính

1. **Dashboard** (`/`) – Trang chủ với thống kê tổng quan.  
2. **Upload Video** (`/upload`) – Upload video, backend xử lý và chấm điểm + tạo skeleton video.  
3. **Real-time Monitoring (Global Mode)** (`/monitoring`) – Giám sát thời gian thực qua webcam, chấm tổng hợp (tư thế + nhịp), hỗ trợ multi-person.  
4. **Local Mode – Làm chậm** (`/local-mode`) – Giám sát thời gian thực cho bài Làm chậm, chỉ kiểm tra tư thế, có nút phát câu lệnh “Nghiêm. Đi đều bước”.  
5. **Results** (`/results/:sessionId?`) – Xem chi tiết kết quả chấm điểm cho một session.  
6. **Sessions** (`/sessions`) – Quản lý và xem lịch sử các phiên chấm.  
7. **Comparison** (`/comparison`) – So sánh nhiều sessions với nhau.  
8. **Settings** (`/settings`) – Cấu hình chấm điểm, error grouping, difficulty, app_mode, v.v.  
9. **Barem** (`/barem`) – Xem và chỉnh Barem.  
10. **Candidates** (`/candidates`) – Quản lý danh sách thí sinh (CRUD + import Excel).  
11. **Login/Register** (`/login`, `/register`) – Đăng nhập, đăng ký tài khoản.

#### Build Production

```bash
# Build frontend cho production
cd frontend
npm run build

# Output sẽ ở trong thư mục dist/
# Deploy thư mục dist/ lên hosting service
```

### 👥 Tính Năng Multi-Person Tracking

Hệ thống hỗ trợ tự động phát hiện và theo dõi nhiều người trong video:

**Cấu Hình:**

1. Vào trang **Settings** (`/settings`)
2. Bật **"Bật chế độ nhiều người"**
3. Cấu hình các tham số:
   - **Tracking Method**: ByteTrack (khuyến nghị) hoặc SORT
   - **Max Persons**: Số người tối đa (mặc định: 5)
   - **Max Disappeared**: Số frame tối đa một người có thể biến mất trước khi bỏ theo dõi
   - **IoU Threshold**: Ngưỡng IoU cho matching

**Cách Hoạt Động:**

- Hệ thống tự động phát hiện và gán ID cho mỗi người
- Mỗi người được chấm điểm riêng biệt
- Kết quả hiển thị theo từng người với ID tương ứng
- Lọc các track không ổn định (ghost detections)

**Xem Kết Quả:**

- Trang **Results** cho phép chuyển đổi giữa các người bằng cách chọn ID
- Trang **Real-time Monitoring** hiển thị số người đang được theo dõi
- Mỗi người có điểm số và danh sách lỗi riêng

### 🔗 Error Grouping - Nhóm Lỗi Liên Tiếp

Hệ thống tự động nhóm các lỗi liên tiếp cùng loại thành một lỗi duy nhất:

**Cấu Hình:**

- Vào **Settings** → **Scoring Configuration**
- Cấu hình **Error Grouping**:
  - **Min Sequence Length**: Độ dài tối thiểu để nhóm (mặc định: 2 frames)
  - Các lỗi liên tiếp cùng loại sẽ được gộp thành một sequence

**Ví Dụ:**

```
Frame 34: arm_angle - Tay trái quá thấp
Frame 35: arm_angle - Tay trái quá thấp
Frame 36: arm_angle - Tay trái quá thấp
```

→ Được nhóm thành: **"Arm Angle (left) from frame 34-36 (3 frames)"** - Trừ điểm 1 lần thay vì 3 lần

#### Điểm Cuối API

**1. Kiểm Tra Sức Khỏe**
```bash
curl http://localhost:8000/health
```

**2. Phân Tích Video**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "video=@path/to/video.mp4" \
  -F "reference=@path/to/reference.mp4" \
  -F "config={\"enable_beat_detection\": true}"
```

**3. Lấy Kết Quả**
```bash
curl http://localhost:8000/api/v1/results/{job_id}
```

**4. Xử Lý Hàng Loạt**
```bash
curl -X POST http://localhost:8000/api/v1/batch \
  -H "Content-Type: application/json" \
  -d '{
    "videos": ["video1.mp4", "video2.mp4"],
    "reference": "reference.mp4"
  }'
```

> Lưu ý: Phần “Python API” với các lớp `PoseEstimator`, `ScoreCalculator`, `VideoProcessor` trong README cũ không còn áp dụng cho repo hiện tại (kiến trúc đã được tổ chức lại thành `backend/app/...` và `run_scoring.py`).  
> Nếu cần dùng programmatic API, hãy import trực tiếp từ `backend.app.services` và `backend.app.controllers`.

## 🧪 Kiểm tra

### Chạy kiểm tra

#### Chạy tất cả kiểm tra backend
```bash
# Chạy bộ kiểm tra đầy đủ
pytest

# Chạy với báo cáo độ phủ
pytest --cov=src --cov-report=html

# Chạy với đầu ra chi tiết
pytest -v
```

#### Chạy một số nhóm kiểm tra tiêu biểu

```bash
# Chỉ kiểm tra đơn vị
pytest tests/test_pose_estimator.py tests/test_score_calculator.py

# Kiểm tra dịch vụ
pytest tests/test_temporal_smoothing.py tests/test_adaptive_threshold.py \
       tests/test_keypoint_normalization.py tests/test_sequence_comparison.py \
       tests/test_beat_detection.py

# Kiểm tra tích hợp
pytest tests/test_integration.py

# Kiểm tra hiệu suất
pytest tests/test_performance.py -m slow
```

#### Chạy Với Markers

```bash
# Chỉ chạy kiểm tra nhanh
pytest -m "not slow"

# Chỉ chạy kiểm tra tích hợp
pytest -m integration

# Chạy kiểm tra khớp mẫu
pytest -k "test_temporal or test_adaptive"
```

#### Tạo Báo Cáo

```bash
# Báo cáo độ phủ HTML
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Báo cáo XML cho CI/CD
pytest --cov=src --cov-report=xml --junitxml=test-results.xml

# Báo cáo terminal với các dòng thiếu
pytest --cov=src --cov-report=term-missing
```

### Cấu hình kiểm tra (tùy chọn)

Tạo `pytest.ini` cho cấu hình tùy chỉnh:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
addopts = 
    --strict-markers
    --disable-warnings
    -ra
```

## ⚙️ Cấu hình

### 🗄️ Database schema

Hệ thống sử dụng PostgreSQL để lưu trữ dữ liệu. Schema được khởi tạo bởi file `docker/init-db.sql` với các bảng chính:

- `users` – người dùng hệ thống (đăng ký/đăng nhập).  
- `candidates` – thí sinh.  
- `sessions` – phiên chấm điểm (Local/Global, mode testing/practising, video_path, skeleton_video_url, candidate_id, user_id...).  
- `persons` – từng người (track ID) trong một session, điểm, số lỗi, first/last frame.  
- `errors` – chi tiết lỗi (type, severity, deduction, frame, is_sequence, sequence_length, start_frame, end_frame...).  
- `golden_templates` – thông tin golden template (video, skeleton, profile, camera_angle...).  
- `configs` – cấu hình hệ thống (scoring_config, multi_person_config, error_thresholds...).

**Khởi tạo database thủ công:**

```bash
psql -U scoreuser -d score_parade -f docker/init-db.sql
```

### Biến môi trường chính

Các biến môi trường thực tế được khai báo trong `env.example`. Ví dụ:

```bash
# Database Configuration
POSTGRES_USER=scoreuser
POSTGRES_PASSWORD=scorepass123
POSTGRES_DB=score_parade
DATABASE_URL=postgresql://scoreuser:scorepass123@localhost:5432/score_parade

# Ứng dụng
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=INFO
```

**Lưu ý:** Copy `env.example` thành `.env` và điều chỉnh các giá trị phù hợp với môi trường của bạn.

## 🚨 Các loại lỗi & exception

Score Parade định nghĩa nhiều loại exception để xử lý lỗi mạnh mẽ, nằm chủ yếu trong `backend/app/utils/exceptions.py` (ValidationException, NotFoundException, DatabaseException, AIException, ...), và được dùng trong API (FastAPI) để trả về HTTP status + message phù hợp. Ngoài ra, các service (video, pose, DTW, beat detection) cũng log chi tiết để hỗ trợ debug.

### 1. **VideoProcessingError**
```python
class VideoProcessingError(Exception):
    """Raised when video cannot be processed"""
    pass
```
**Nguyên Nhân:**
- File video bị hỏng
- Định dạng video không được hỗ trợ
- Thiếu codec video

### 2. **PoseEstimationError**
```python
class PoseEstimationError(Exception):
    """Raised when pose estimation fails"""
    pass
```
**Nguyên Nhân:**
- Không phát hiện được người trong khung hình
- Nhiều người trong khung hình
- Điều kiện ánh sáng kém

### 3. **ConfigurationError**
```python
class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass
```
**Nguyên Nhân:**
- Định dạng cấu hình không hợp lệ
- Thiếu tham số bắt buộc
- Giá trị ngoài phạm vi

### 4. **SequenceAlignmentError**
```python
class SequenceAlignmentError(Exception):
    """Raised when sequence alignment fails"""
    pass
```
**Nguyên Nhân:**
- Các chuỗi quá khác biệt
- Không đủ khung hình
- Định dạng chuỗi không hợp lệ

### 5. **BeatDetectionError**
```python
class BeatDetectionError(Exception):
    """Raised when beat detection fails"""
    pass
```
**Nguyên Nhân:**
- Không có track âm thanh trong video
- Tempo không đều
- Chất lượng âm thanh quá thấp

### 6. **ValidationError**
```python
class ValidationError(Exception):
    """Raised when input validation fails"""
    pass
```
**Nguyên Nhân:**
- Đường dẫn file không hợp lệ
- Loại tham số không đúng
- Thiếu đầu vào bắt buộc

## 🔧 Quy Trình Kỹ Thuật

### Quy Trình Xử Lý

```
Video Đầu Vào → Trích Xuất Khung Hình → Phát Hiện Tư Thế → Chuẩn Hóa Điểm Mốc
                                                          ↓
Điểm Cuối Cùng ← Tổng Hợp Điểm ← Làm Mịn Thời Gian ← Căn Chỉnh Chuỗi
                                                          ↓
                                   ← Phát Hiện Nhịp ← Ngưỡng Thích Ứng
```

### Các Bước Chi Tiết

1. **Đầu Vào Video & Tiền Xử Lý**
   - Tải file video và trích xuất khung hình
   - Thay đổi kích thước về độ phân giải tối ưu
   - Áp dụng hiệu chỉnh màu nếu cần

2. **Ước Tính Tư Thế**
   - Phát hiện 33 điểm mốc cơ thể mỗi khung hình
   - Tính điểm độ tin cậy
   - Lọc các phát hiện có độ tin cậy thấp

3. **Chuẩn Hóa Điểm Mốc**
   - Chuẩn hóa tọa độ về phạm vi [-1, 1]
   - Áp dụng tính bất biến tỷ lệ và dịch chuyển
   - Xử lý các điểm mốc bị thiếu

4. **Căn Chỉnh Chuỗi (DTW)**
   - Căn chỉnh chuỗi người dùng với tham chiếu
   - Tính đường dẫn biến dạng tối ưu
   - Tính khoảng cách căn chỉnh

5. **Làm Mịn Thời Gian**
   - Áp dụng bộ lọc Gaussian cho quỹ đạo
   - Giảm nhiễu và rung
   - Bảo toàn các chuyển động quan trọng

6. **Ngưỡng Thích Ứng**
   - Điều chỉnh ngưỡng chấm điểm động
   - Thích ứng với độ khó biểu diễn
   - Chuẩn hóa trên các điệu nhảy khác nhau

7. **Phát Hiện Nhịp** (Tùy chọn)
   - Trích xuất âm thanh từ video
   - Phát hiện khởi phát nhịp
   - Tính đồng bộ chuyển động-nhịp

8. **Tính Điểm**
   - Tính độ chính xác vị trí
   - Đánh giá độ chính xác thời gian
   - Đánh giá độ mượt mà chuyển động
   - Tính căn chỉnh nhịp (nếu được bật)
   - Tổng hợp điểm cuối cùng có trọng số

## 🛠️ Khắc Phục Sự Cố

### Các Vấn Đề Thường Gặp & Giải Pháp

#### 1. **Lỗi "ModuleNotFoundError: No module named 'backend'" khi chạy backend**

**Vấn Đề:** Chạy backend từ thư mục sai hoặc Python không tìm thấy module

**Giải Pháp:**
```bash
# Đảm bảo bạn đang ở thư mục GỐC của project
cd F:\Score-parade\Score-parade

# Chạy backend từ thư mục gốc
python -c "import sys; sys.path.insert(0, '.'); from backend.app.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"

# Hoặc sử dụng uvicorn
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

#### 2. **Lỗi "Cannot find module" trong Frontend**

**Vấn Đề:** Dependencies chưa được cài đặt

**Giải Pháp:**
```bash
cd frontend
npm install
npm run dev
```

#### 3. **Lỗi "ERR_CONNECTION_REFUSED" trong Frontend**

**Vấn Đề:** Backend chưa chạy hoặc chạy sai port

**Giải Pháp:**
- Kiểm tra backend đang chạy tại `http://localhost:8000`
- Kiểm tra file `frontend/.env` có `VITE_API_URL=http://localhost:8000`
- Đảm bảo CORS đã được cấu hình trong backend

#### 4. **Lỗi Kết Nối Database**

**Vấn Đề:** Không thể kết nối đến PostgreSQL

**Giải Pháp:**
```bash
# Kiểm tra PostgreSQL đang chạy
# Windows:
# Services → PostgreSQL

# Linux/macOS:
sudo systemctl status postgresql
# hoặc
brew services list | grep postgresql

# Kiểm tra kết nối
psql -U scoreuser -d score_parade -h localhost

# Nếu dùng Docker, kiểm tra container
docker-compose ps db
docker-compose logs db
```

#### 5. **Lỗi Docker Build**

**Vấn Đề:** Docker build thất bại hoặc image quá lớn

**Giải Pháp:**
```bash
# Xóa cache và rebuild
docker-compose build --no-cache

# Kiểm tra disk space
docker system df

# Dọn dẹp unused images
docker system prune -a

# Kiểm tra logs chi tiết
docker-compose build --progress=plain
```

#### 6. **Lỗi "No module named 'mediapipe'"**

**Lưu ý:** Hệ thống hiện tại sử dụng YOLOv8-Pose, không phải MediaPipe

**Nếu gặp lỗi với YOLOv8:**
```bash
# Cài đặt ultralytics
pip install ultralytics

# Tải model nếu chưa có
# Model sẽ tự động tải khi chạy lần đầu
```

#### 7. **Lỗi "Video file cannot be opened"**

**Vấn Đề:** FFmpeg chưa được cài đặt hoặc định dạng video không được hỗ trợ

**Giải Pháp:**
```bash
# Cài đặt FFmpeg (xem phần Cài Đặt)

# Chuyển đổi video sang định dạng được hỗ trợ
ffmpeg -i input.avi -c:v libx264 -c:a aac output.mp4

# Kiểm tra tính toàn vẹn video
ffmpeg -v error -i video.mp4 -f null -
```

#### 8. **FPS Thấp / Xử Lý Chậm**

**Vấn Đề:** Xử lý quá chậm cho phân tích thời gian thực

**Giải Pháp:**
```yaml
# Giảm độ phức tạp mô hình trong config
pose_estimation:
  model_complexity: 0  # Sử dụng mô hình nhẹ

# Giảm độ phân giải video
video_processing:
  max_resolution: [640, 480]

# Bật tăng tốc GPU
performance:
  enable_gpu: true
```

```bash
# Kiểm tra khả năng GPU
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

#### 9. **Cảnh Báo "No person detected"**

**Vấn Đề:** Ước tính tư thế không phát hiện được người

**Giải Pháp:**
```yaml
# Giảm độ tin cậy phát hiện
pose_estimation:
  min_detection_confidence: 0.3  # Giảm ngưỡng

# Đảm bảo ánh sáng tốt và góc camera
# Đảm bảo người hoàn toàn hiển thị trong khung hình
# Tránh nền lộn xộn
```

#### 10. **Sử Dụng Bộ Nhớ Cao**

**Vấn Đề:** Ứng dụng tiêu thụ quá nhiều RAM

**Giải Pháp:**
```yaml
# Bật giới hạn cache khung hình
performance:
  max_cached_frames: 100
  enable_memory_optimization: true

# Xử lý theo lô nhỏ hơn
batch_processing:
  batch_size: 10
```

```bash
# Theo dõi sử dụng bộ nhớ
python -m memory_profiler src/main.py --video input.mp4
```

#### 11. **Điểm Không Nhất Quán**

**Vấn Đề:** Điểm thay đổi đáng kể giữa các lần chạy

**Giải Pháp:**
```yaml
# Tăng làm mịn thời gian
temporal_smoothing:
  window_size: 10
  method: "gaussian"
  sigma: 2.0

# Bật ngưỡng thích ứng
adaptive_threshold:
  enabled: true
  learning_rate: 0.005

# Sử dụng trọng số chấm điểm ổn định hơn
scoring:
  weights:
    position: 0.50
    timing: 0.30
    smoothness: 0.20
```

### Chế Độ Debug

Bật debug toàn diện:

```bash
# Đặt biến môi trường
export APP_DEBUG=true
export LOG_LEVEL=DEBUG

# Chạy với cờ debug
python -m src.main --video input.mp4 --reference ref.mp4 --debug --verbose

# Tạo báo cáo debug
python -m src.main --video input.mp4 --reference ref.mp4 --debug-output debug_report.json
```

### Nhận Trợ Giúp

Nếu vấn đề vẫn còn:

1. **Kiểm Tra Log:** Xem lại `logs/score_parade.log` để biết thông báo lỗi chi tiết
2. **GitHub Issues:** Tìm kiếm hoặc tạo issue tại [github.com/HuyLuc/Score-parade/issues](https://github.com/HuyLuc/Score-parade/issues)
3. **Tài Liệu:** Đọc tài liệu chi tiết trong thư mục `docs/`
4. **Cộng Đồng:** Tham gia thảo luận trong repository

## 🗺️ Lộ Trình

### Phiên Bản 2.0 (Hiện Tại) ✅
- [x] Theo dõi và so sánh nhiều người (ByteTrack)
- [x] Phân tích webcam thời gian thực
- [x] Database PostgreSQL với schema đầy đủ
- [x] Docker deployment với Docker Compose
- [x] Error grouping cho lỗi liên tiếp
- [x] Frontend React với TypeScript
- [x] API RESTful với FastAPI
- [x] YOLOv8-Pose integration

### Phiên Bản 2.1 (Q1 2026)
- [ ] Ứng dụng di động (iOS/Android)
- [ ] API xử lý dựa trên đám mây
- [ ] Bảng điều khiển trực quan hóa nâng cao
- [ ] Real-time collaboration features

### Phiên Bản 2.2 (Q2 2026)
- [ ] Ước tính tư thế 3D
- [ ] Tích hợp VR/AR
- [ ] Huấn luyện phong cách khiêu vũ tùy chỉnh
- [ ] Tính năng xã hội và bảng xếp hạng
- [ ] Gợi ý huấn luyện bằng AI

### Phiên Bản 3.0 (Q3 2026)
- [ ] Ước tính tư thế dựa trên Transformer
- [ ] Phân tích đa phương thức (tư thế + âm thanh + cảm xúc)
- [ ] AI tạo sinh cho biên đạo
- [ ] Ứng dụng desktop đa nền tảng
- [ ] Tính năng và phân tích doanh nghiệp

### Cân Nhắc Tương Lai
- Tùy chỉnh mô hình học máy
- Tích hợp với các trò chơi khiêu vũ phổ biến
- Tích hợp nền tảng giáo dục
- Hỗ trợ cuộc thi và giải đấu
- Quốc tế hóa (i18n)

## 🤝 Đóng Góp

Chúng tôi hoan nghênh mọi đóng góp! Vui lòng xem [CONTRIBUTING.md](docs/CONTRIBUTING.md) để biết chi tiết.

### Bắt Đầu Nhanh Cho Người Đóng Góp

1. Fork repository
2. Tạo nhánh tính năng: `git checkout -b feature/amazing-feature`
3. Thực hiện thay đổi và thêm kiểm tra
4. Chạy bộ kiểm tra: `pytest`
5. Commit thay đổi: `git commit -m 'Add amazing feature'`
6. Push lên nhánh: `git push origin feature/amazing-feature`
7. Mở Pull Request

### Hướng Dẫn Phát Triển

- Tuân theo hướng dẫn phong cách PEP 8
- Thêm docstring cho tất cả hàm/lớp
- Viết kiểm tra đơn vị cho tính năng mới
- Cập nhật tài liệu khi cần
- Sử dụng type hints khi phù hợp

## 📄 Giấy Phép

Dự án này được cấp phép theo Giấy phép MIT - xem file [LICENSE](LICENSE) để biết chi tiết.

## 👏 Lời Cảm Ơn

- **YOLOv8** của Ultralytics cho ước tính tư thế chính xác cao
- **ByteTrack** cho multi-object tracking
- **OpenCV** cho xử lý video
- **NumPy/SciPy** cho tính toán số
- **FastAPI** cho framework API hiện đại
- **React + TypeScript** cho frontend framework
- **PostgreSQL** cho database management
- **Docker** cho containerization
- **pytest** cho framework kiểm tra

## 📞 Liên Hệ

**HuyLuc** - [@HuyLuc](https://github.com/HuyLuc)

Liên Kết Dự Án: [https://github.com/HuyLuc/Score-parade](https://github.com/HuyLuc/Score-parade)

---

<p align="center">Được tạo với ❤️ bởi Đội Ngũ Score Parade</p>
<p align="center">⭐ Hãy đánh dấu sao cho chúng tôi trên GitHub nếu bạn thấy dự án này hữu ích!</p>
