# Hướng dẫn Restart Backend

## Vấn đề
Endpoint `/api/global/{session_id}/upload-video` không được tìm thấy (404) vì backend server đang chạy với code cũ.

## Giải pháp

### Cách 1: Restart Backend Server (Khuyến nghị)

1. **Tìm và dừng process backend đang chạy:**
   ```powershell
   # Tìm process đang chạy trên port 8000
   netstat -ano | findstr :8000
   
   # Kill process (thay PID bằng process ID từ lệnh trên)
   taskkill /PID <PID> /F
   ```

2. **Khởi động lại backend:**
   ```powershell
   cd F:\Score-parade\Score-parade
   python -m backend.app.main
   ```

   Hoặc nếu bạn đang dùng uvicorn trực tiếp:
   ```powershell
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Cách 2: Sử dụng --reload flag (Tự động reload)

Nếu bạn chạy backend với flag `--reload`, nó sẽ tự động reload khi code thay đổi:

```powershell
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Kiểm tra endpoint đã được load

Sau khi restart, kiểm tra endpoint có sẵn không:

```powershell
# Mở browser và vào:
http://localhost:8000/docs

# Hoặc test bằng curl:
curl http://localhost:8000/openapi.json | findstr upload-video
```

Bạn sẽ thấy endpoint `/api/global/{session_id}/upload-video` trong danh sách endpoints.

