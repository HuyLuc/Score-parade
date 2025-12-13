# Score Parade Frontend

Frontend application cho hệ thống chấm điểm điều lệnh tự động, được xây dựng với React, TypeScript, Material-UI và Tailwind CSS.

## 🚀 Tính Năng

- 📊 **Dashboard** - Tổng quan thống kê và biểu đồ
- 📤 **Upload Video** - Upload và xử lý video với drag & drop
- 🎥 **Real-time Monitoring** - Giám sát thời gian thực qua webcam
- 📈 **Kết Quả** - Xem chi tiết kết quả chấm điểm với biểu đồ và bảng lỗi
- 📋 **Quản Lý Sessions** - Quản lý và xem lịch sử sessions
- 🔄 **So Sánh** - So sánh nhiều sessions với nhau
- 📄 **Export** - Xuất báo cáo PDF và Excel

## 🛠️ Công Nghệ

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Material-UI (MUI)** - Component library
- **Tailwind CSS** - Utility-first CSS
- **React Router** - Routing
- **Zustand** - State management
- **Axios** - HTTP client
- **Recharts** - Charts và visualizations
- **React Player** - Video playback
- **React Webcam** - Webcam integration

## 📦 Cài Đặt

```bash
# Cài đặt dependencies
npm install

# Hoặc sử dụng yarn
yarn install
```

## 🏃 Chạy Ứng Dụng

```bash
# Development mode
npm run dev

# Build cho production
npm run build

# Preview production build
npm run preview
```

Ứng dụng sẽ chạy tại `http://localhost:3000`

## ⚙️ Cấu Hình

Tạo file `.env` trong thư mục `frontend/`:

```env
VITE_API_URL=http://localhost:8000
```

## 📁 Cấu Trúc Dự Án

```
frontend/
├── src/
│   ├── components/      # Reusable components
│   │   ├── Dashboard/   # Dashboard components
│   │   ├── Layout/       # Layout components
│   │   ├── Results/      # Results components
│   │   └── Comparison/  # Comparison components
│   ├── pages/           # Page components
│   │   ├── Dashboard.tsx
│   │   ├── VideoUpload.tsx
│   │   ├── RealTimeMonitoring.tsx
│   │   ├── Results.tsx
│   │   ├── Sessions.tsx
│   │   └── Comparison.tsx
│   ├── services/        # API services
│   │   └── api.ts
│   ├── store/           # State management
│   │   └── useSessionStore.ts
│   ├── utils/           # Utility functions
│   │   └── export.ts
│   ├── App.tsx          # Main app component
│   ├── main.tsx         # Entry point
│   └── theme.ts         # MUI theme configuration
├── public/              # Static assets
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## 🔌 Kết Nối Backend

Frontend kết nối với backend API tại `http://localhost:8000` (mặc định).

Đảm bảo backend đang chạy trước khi start frontend:

```bash
# Terminal 1: Start backend
cd backend
python -m backend.app.main

# Terminal 2: Start frontend
cd frontend
npm run dev
```

## 📝 Scripts

- `npm run dev` - Chạy development server
- `npm run build` - Build cho production
- `npm run preview` - Preview production build
- `npm run lint` - Chạy ESLint

## 🎨 Styling

Ứng dụng sử dụng:
- **Material-UI** cho components và theme
- **Tailwind CSS** cho utility classes
- Custom theme được định nghĩa trong `src/theme.ts`

## 📱 Responsive Design

Ứng dụng được thiết kế responsive và hoạt động tốt trên:
- Desktop (1920px+)
- Laptop (1024px - 1920px)
- Tablet (768px - 1024px)
- Mobile (320px - 768px)

## 🔐 State Management

Sử dụng **Zustand** để quản lý state:
- Session data được lưu trong localStorage
- Persistent storage cho sessions
- Lightweight và dễ sử dụng

## 📊 Charts & Visualizations

Sử dụng **Recharts** cho:
- Line charts (điểm số theo thời gian)
- Bar charts (phân bố lỗi)
- Comparison charts (so sánh sessions)

## 🚀 Production Build

```bash
# Build
npm run build

# Output sẽ ở trong thư mục dist/
```

Deploy `dist/` folder lên hosting service như:
- Vercel
- Netlify
- AWS S3 + CloudFront
- Nginx

## 🐛 Troubleshooting

### Lỗi kết nối API
- Kiểm tra backend đang chạy
- Kiểm tra `VITE_API_URL` trong `.env`
- Kiểm tra CORS settings trong backend

### Lỗi build
- Xóa `node_modules` và `package-lock.json`
- Chạy `npm install` lại
- Kiểm tra Node.js version (>= 16)

## 📄 License

MIT

