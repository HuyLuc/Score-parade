# Hướng Dẫn Sử Dụng Skeleton Visualization & TTS Realtime

## ✅ Đã Triển Khai

### 1. **Skeleton Visualization (Hiển thị khớp xương)**
- ✅ Backend trả về keypoints trong response của `process_frame`
- ✅ Frontend vẽ skeleton overlay lên webcam feed
- ✅ Hỗ trợ multi-person (vẽ skeleton cho nhiều người)
- ✅ Hiển thị person ID label
- ✅ Toggle bật/tắt skeleton visualization

### 2. **Text-to-Speech (TTS) - Đọc lỗi bằng giọng nói**
- ✅ Tự động đọc lỗi khi phát hiện lỗi mới
- ✅ Queue management để tránh đọc trùng lặp
- ✅ Cooldown 2 giây giữa các lỗi cùng loại
- ✅ Hỗ trợ tiếng Việt
- ✅ Toggle bật/tắt TTS

## 🎯 Cách Sử Dụng

### Bước 1: Khởi động Backend và Frontend

```powershell
# Terminal 1: Backend
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Bước 2: Truy cập Real-time Monitoring

1. Mở trình duyệt: `http://localhost:5173`
2. Điều hướng đến **"Real-time Monitoring"** từ menu
3. Cho phép quyền truy cập camera khi được hỏi

### Bước 3: Cấu hình Session

1. **Session ID**: Tự động tạo hoặc nhập thủ công
2. **Chế Độ**: 
   - `Testing`: Trừ điểm, dừng khi điểm < ngưỡng
   - `Practising`: Chỉ hiển thị lỗi, không trừ điểm
3. **Hiển thị khớp xương**: Toggle để bật/tắt skeleton overlay
4. **Đọc lỗi bằng giọng nói**: Toggle để bật/tắt TTS

### Bước 4: Bắt đầu Session

1. Click **"Bắt Đầu"**
2. Đứng trước camera
3. Hệ thống sẽ:
   - Phát hiện người và vẽ skeleton (nếu bật)
   - Chấm điểm realtime
   - Đọc lỗi bằng giọng nói khi phát hiện lỗi mới (nếu bật TTS)

## 🔧 Cấu Hình Nâng Cao

### TTS Settings (trong code)

File: `frontend/src/utils/ttsManager.ts`

```typescript
// Cooldown giữa các lỗi cùng loại (ms)
private readonly COOLDOWN_MS = 2000

// Kích thước queue tối đa
private readonly MAX_QUEUE_SIZE = 5
```

### Skeleton Colors

File: `frontend/src/utils/skeletonDrawer.ts`

```typescript
const COLORS = {
  head: '#FF6B6B',      // Đỏ
  torso: '#4ECDC4',     // Xanh lá
  leftArm: '#45B7D1',   // Xanh dương
  rightArm: '#96CEB4',  // Xanh nhạt
  leftLeg: '#FFEAA7',   // Vàng
  rightLeg: '#DDA15E',  // Cam
  joint: '#FFFFFF',     // Trắng
}
```

## ⚠️ Lưu Ý Quan Trọng

### 1. **Web Speech API**
- **Chrome/Edge**: Hỗ trợ tốt, có giọng tiếng Việt
- **Firefox**: Hỗ trợ nhưng có thể không có giọng tiếng Việt
- **Safari**: Hỗ trợ hạn chế

### 2. **Camera Resolution**
- Webcam mặc định: 1280x720
- Nếu camera của bạn có resolution khác, skeleton sẽ tự động scale

### 3. **Performance**
- Skeleton rendering: ~10 FPS (mỗi 100ms)
- TTS: Chỉ đọc khi có lỗi mới (cooldown 2s)

### 4. **Multi-Person**
- Hệ thống hỗ trợ nhiều người
- Chọn person ID để xem điểm/lỗi của từng người
- Skeleton sẽ vẽ cho tất cả người được phát hiện

## 🐛 Troubleshooting

### Skeleton không hiển thị
1. Kiểm tra toggle "Hiển thị khớp xương" đã bật chưa
2. Kiểm tra console có lỗi không
3. Đảm bảo backend trả về keypoints trong response

### TTS không đọc
1. Kiểm tra toggle "Đọc lỗi bằng giọng nói" đã bật chưa
2. Kiểm tra trình duyệt có hỗ trợ Web Speech API không
3. Kiểm tra console có lỗi không
4. Thử cho phép microphone permission (một số trình duyệt yêu cầu)

### Skeleton bị lệch vị trí
- Keypoints được scale tự động dựa trên video resolution
- Nếu vẫn lệch, kiểm tra video constraints trong `RealTimeMonitoring.tsx`

## 📝 API Response Format

Backend trả về keypoints trong format:

```json
{
  "success": true,
  "persons": [
    {
      "person_id": 0,
      "score": 95.5,
      "errors": [...],
      "keypoints": [
        [x1, y1, confidence1],  // nose
        [x2, y2, confidence2],  // left_eye
        ...
        // 17 keypoints total
      ]
    }
  ]
}
```

## 🎉 Tính Năng Mới

1. **Skeleton Overlay**: Xem khớp xương trực tiếp trên camera
2. **TTS Realtime**: Nghe lỗi được đọc tự động
3. **Multi-Person Support**: Hỗ trợ nhiều người cùng lúc
4. **Toggle Controls**: Dễ dàng bật/tắt các tính năng

---

**Lưu ý**: Tính năng này yêu cầu:
- Camera hoạt động
- Trình duyệt hỗ trợ Web Speech API (cho TTS)
- Backend đang chạy và có thể xử lý pose estimation

