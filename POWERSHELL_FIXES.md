# Sửa Lỗi PowerShell

## Các Lỗi Thường Gặp và Cách Sửa

### 1. Lỗi Execution Policy

**Lỗi:**
```
.ps1 cannot be loaded because running scripts is disabled on this system
```

**Cách sửa:**
```powershell
# Mở PowerShell as Administrator và chạy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Sau đó chạy lại:
.\venv\Scripts\Activate.ps1
```

### 2. Lỗi Đường Dẫn (Path)

**Lỗi:** Không tìm thấy file Activate.ps1

**Cách sửa:**
```powershell
# Sử dụng backslash (\) thay vì forward slash (/)
.\venv\Scripts\Activate.ps1

# Hoặc dùng đường dẫn đầy đủ:
& ".\venv\Scripts\Activate.ps1"
```

### 3. Lỗi Khi Chạy Python Scripts

**Lỗi:** `python` không được nhận dạng

**Cách sửa:**
```powershell
# Kiểm tra Python đã cài chưa:
python --version

# Nếu chưa có, cài đặt Python từ python.org
# Hoặc dùng đường dẫn đầy đủ:
C:\Users\PC\AppData\Local\Programs\Python\Python311\python.exe --version
```

### 4. Lỗi Khi Chạy Docker Commands

**Lỗi:** `docker-compose` không được nhận dạng

**Cách sửa:**
```powershell
# Kiểm tra Docker đã cài chưa:
docker --version
docker-compose --version

# Nếu chưa có, cài Docker Desktop từ docker.com
```

### 5. Lỗi Khi Chạy npm

**Lỗi:** `npm` không được nhận dạng

**Cách sửa:**
```powershell
# Kiểm tra Node.js đã cài chưa:
node --version
npm --version

# Nếu chưa có, cài Node.js từ nodejs.org
```

## Các Lệnh PowerShell Đúng

### Kích hoạt Virtual Environment:
```powershell
# Cách 1 (Khuyến nghị):
.\venv\Scripts\Activate.ps1

# Cách 2 (Nếu gặp lỗi):
& .\venv\Scripts\Activate.ps1

# Cách 3 (Dùng CMD thay vì PowerShell):
venv\Scripts\activate.bat
```

### Chạy Backend:
```powershell
# Từ thư mục gốc project:
cd F:\Score-parade\Score-parade
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Chạy Frontend:
```powershell
# Từ thư mục gốc project:
cd F:\Score-parade\Score-parade\frontend
npm install
npm run dev
```

### Chạy Docker:
```powershell
# Từ thư mục gốc project:
docker-compose up -d --build

# Xem logs:
docker-compose logs -f app

# Dừng:
docker-compose down
```

## Lưu Ý Quan Trọng

1. **Luôn chạy từ thư mục gốc project:**
   ```powershell
   cd F:\Score-parade\Score-parade
   ```

2. **Sử dụng backslash `\` cho đường dẫn Windows:**
   - ✅ Đúng: `.\venv\Scripts\Activate.ps1`
   - ❌ Sai: `.venv/Scripts/Activate.ps1`

3. **Nếu gặp lỗi permission, chạy PowerShell as Administrator**

4. **Kiểm tra execution policy:**
   ```powershell
   Get-ExecutionPolicy
   # Nếu là Restricted, cần set:
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

