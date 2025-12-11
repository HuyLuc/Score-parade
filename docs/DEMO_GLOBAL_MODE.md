# Demo Global Mode API Workflow

Script demo Python để test luồng hoạt động chính của Global Mode API (không cần frontend).

## Mục đích

Script `demo_global_mode.py` giúp:
- Test workflow đầy đủ của Global Mode API
- Hiển thị real-time progress khi xử lý video
- Kiểm tra khả năng detect motion, rhythm errors, posture errors
- Debug và troubleshoot API issues
- Demo cách tích hợp API vào ứng dụng client

## Prerequisites

### 1. Backend đang chạy

Backend API phải đang chạy tại `http://localhost:8000`:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Kiểm tra backend hoạt động:
```bash
curl http://localhost:8000/health
# Kết quả: {"status":"healthy","service":"score-parade-api"}
```

### 2. Dependencies

Script yêu cầu các thư viện sau (đã có trong `backend/requirements.txt`):

```bash
pip install requests opencv-python numpy
```

### 3. Video file

Cần có video file để test. Mặc định script sử dụng:
```
data/input_videos/video1.mp4
```

Nếu dùng video khác, cập nhật biến `VIDEO_PATH` trong script.

### 4. Audio file (Optional)

Nếu test beat detection, cần file audio:
```
data/audio/di_deu/global/total.mp3
```

Cập nhật biến `AUDIO_PATH` trong script.

## Cách chạy

### Chạy đơn giản (mặc định)

```bash
python demo_global_mode.py
```

### Customize config

Mở file `demo_global_mode.py` và chỉnh sửa các biến ở đầu file:

```python
# Session configuration
SESSION_ID = "demo-test-session"  # Unique session ID
MODE = "testing"                  # "testing" or "practising"

# File paths
VIDEO_PATH = "data/input_videos/video1.mp4"
AUDIO_PATH = None  # hoặc "data/audio/..."

# Processing options
MAX_FRAMES = 300      # Giới hạn số frames, None = full video
FRAME_SKIP = 1        # Process every Nth frame (1 = all)
SLEEP_BETWEEN_FRAMES = 0.05  # Delay between frames (seconds)

# API endpoint
API_BASE = "http://localhost:8000"
```

## Output mẫu

### Testing mode - Success case

```
############################################################
#  DEMO: Global Mode API Workflow
############################################################

============================================================
🚀 Bước 1: Khởi tạo session
============================================================
Session ID: demo-test-session
Mode: testing
✅ Session 'demo-test-session' đã được khởi tạo
   Mode: testing
   Audio set: True

============================================================
🎬 Bước 2: Xử lý video
============================================================
📹 Video: data/input_videos/video1.mp4
   FPS: 30.0
   Total frames: 900
   Duration: 30.0s
   Processing: 300 frames (limit)

⏱️  Frame   10 |   0.33s | Score: 🟢 100.0
⏱️  Frame   20 |   0.67s | Score: 🟢 100.0
⏱️  Frame   30 |   1.00s | Score: 🟢  98.5 | ⚠️  1 error(s)
   🔴 RHYTHM: Động tác step không theo nhịp (lệch 0.18s) (trừ 1.5 điểm)
⏱️  Frame   40 |   1.33s | Score: 🟢  98.5
⏱️  Frame   50 |   1.67s | Score: 🟢  96.8 | ⚠️  1 error(s)
   🟠 POSTURE: Tay trái quá thấp (trừ 1.7 điểm)
⏱️  Frame   60 |   2.00s | Score: 🟢  96.8
...
⏱️  Frame  300 |  10.00s | Score: 🟢  85.2

⏸️  Đạt giới hạn 300 frames

✅ Đã xử lý 300 frames

============================================================
📊 Bước 3: Tổng kết
============================================================
🎯 Điểm cuối: 🟡  85.2/100
📝 Tổng lỗi: 12
   - Rhythm errors: 8
   - Posture errors: 4

============================================================
🧹 Bước 4: Cleanup
============================================================
✅ Session 'demo-test-session' đã được xóa

✅ Demo hoàn tất!
```

### Testing mode - Early stop case

```
...
⏱️  Frame  150 |   5.00s | Score: 🟠  52.3
⏱️  Frame  160 |   5.33s | Score: 🟠  50.8
⏱️  Frame  170 |   5.67s | Score: 🔴  48.5 | ⚠️  2 error(s)
   🔴 RHYTHM: Động tác step không theo nhịp (lệch 0.25s) (trừ 2.0 điểm)
   🟠 POSTURE: Đầu cúi quá thấp (trừ 1.8 điểm)

🛑 Testing stopped: điểm số (48.5) dưới ngưỡng (50.0)

✅ Đã xử lý 170 frames

============================================================
📊 Bước 3: Tổng kết
============================================================
🎯 Điểm cuối: 🔴  48.5/100
📝 Tổng lỗi: 35
   - Rhythm errors: 22
   - Posture errors: 13

⚠️  Chế độ testing đã dừng do điểm số < 50

============================================================
🧹 Bước 4: Cleanup
============================================================
✅ Session 'demo-test-session' đã được xóa

✅ Demo hoàn tất!
```

## Test cases

### 1. Test với video đầy đủ

```python
MAX_FRAMES = None  # Process all frames
MODE = "practising"  # Không dừng khi score thấp
```

### 2. Test với video ngắn (quick test)

```python
MAX_FRAMES = 100  # Chỉ 100 frames (~3s)
MODE = "testing"
```

### 3. Test fast processing (skip frames)

```python
FRAME_SKIP = 2  # Process every 2nd frame
SLEEP_BETWEEN_FRAMES = 0.01  # Faster processing
```

### 4. Test với audio beat detection

```python
AUDIO_PATH = "data/audio/di_deu/global/total.mp3"
MODE = "testing"
```

### 5. Test practising mode (không dừng)

```python
MODE = "practising"  # Tiếp tục dù score < 50
MAX_FRAMES = None  # Process hết video
```

## Troubleshooting

### Lỗi: Connection refused

```
❌ Lỗi: Không thể kết nối đến backend API
   Kiểm tra backend có đang chạy tại http://localhost:8000
```

**Giải pháp:**
1. Start backend: `cd backend && python -m uvicorn app.main:app --reload`
2. Kiểm tra port: `curl http://localhost:8000/health`
3. Nếu backend dùng port khác, cập nhật `API_BASE` trong script

### Lỗi: Video not found

```
❌ Lỗi: Không tìm thấy video tại data/input_videos/video1.mp4
   Vui lòng cập nhật VIDEO_PATH trong script
```

**Giải pháp:**
1. Kiểm tra video tồn tại: `ls -la data/input_videos/`
2. Cập nhật `VIDEO_PATH` trong script
3. Sử dụng absolute path nếu cần

### Lỗi: Session already exists

```
❌ Lỗi HTTP: 400 Client Error
   Response: {"detail":"Session demo-test-session đã tồn tại..."}
```

**Giải pháp:**
1. Chờ một chút rồi chạy lại (cleanup hoàn tất)
2. Hoặc đổi `SESSION_ID` thành tên khác
3. Hoặc xóa session thủ công:
   ```bash
   curl -X DELETE http://localhost:8000/api/global/demo-test-session
   ```

### Lỗi: Frame encoding failed

```
❌ Lỗi khi xử lý frame 150: Failed to encode frame as JPEG
```

**Giải pháp:**
1. Kiểm tra video không corrupt: `ffmpeg -v error -i video.mp4 -f null -`
2. Convert sang format khác: `ffmpeg -i input.mp4 -c:v libx264 output.mp4`
3. Giảm resolution nếu quá lớn

### Chậm khi process

**Giải pháp:**
1. Tăng `FRAME_SKIP` để skip frames: `FRAME_SKIP = 2` hoặc `3`
2. Giảm `MAX_FRAMES` để test nhanh: `MAX_FRAMES = 100`
3. Tăng `SLEEP_BETWEEN_FRAMES` nếu API bị quá tải

### Backend trả về lỗi 500

**Giải pháp:**
1. Xem logs của backend để biết lỗi chi tiết
2. Kiểm tra model pose estimation đã được tải
3. Kiểm tra audio file (nếu dùng) hợp lệ

## Advanced Usage

### Lưu frames có lỗi

Thêm code vào hàm `process_frame`:

```python
# Sau khi nhận result
if new_errors:
    cv2.imwrite(f"error_frame_{frame_count}.jpg", frame)
```

### Export errors to JSON

Thêm vào cuối hàm `main()`:

```python
import json
with open("demo_errors.json", "w") as f:
    json.dump(all_errors, f, indent=2)
```

### Visualize progress bar

Cài đặt `tqdm`:
```bash
pip install tqdm
```

Sử dụng:
```python
from tqdm import tqdm
for frame_count in tqdm(range(total_frames)):
    # process frame
```

## API Endpoints được sử dụng

Script demo sử dụng các endpoints sau:

1. **Start session**
   - `POST /api/global/{session_id}/start`
   - Body: `mode`, `audio_path` (optional)

2. **Process frame**
   - `POST /api/global/{session_id}/process-frame`
   - Multipart: `frame_data`, `timestamp`, `frame_number`

3. **Get score**
   - `GET /api/global/{session_id}/score`

4. **Get errors**
   - `GET /api/global/{session_id}/errors`

5. **Delete session**
   - `DELETE /api/global/{session_id}`

## Tích hợp vào ứng dụng

Script này là mẫu để tích hợp vào ứng dụng thực tế:

1. **Web frontend**: Dùng JavaScript/TypeScript fetch API
2. **Mobile app**: Dùng HTTP client (axios, fetch)
3. **Desktop app**: Dùng requests hoặc HTTP client tương ứng

Key points:
- Encode frame thành JPEG trước khi gửi
- Gửi qua multipart/form-data
- Handle stopped flag trong testing mode
- Poll score và errors để update UI
- Cleanup session khi done

## Notes

- Script chỉ demo workflow, không có UI visualization
- Trong production, nên xử lý concurrent sessions
- Nên implement retry logic cho network errors
- Có thể mở rộng để test multiple videos parallel
- Score và errors là cumulative trong session
