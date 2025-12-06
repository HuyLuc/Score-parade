📌 BƯỚC 1 — TẠO VIDEO MẪU CHUẨN (GOLDEN TEMPLATE)

Làm gì:

Quay video người thực hiện điều lệnh chuẩn nhất → trích xuất skeleton và các góc chuyển động.

Công nghệ:

Pose estimation: RTMPose hoặc YOLOv8-Pose.

Mục đích:

Tạo “bộ chuẩn tuyệt đối” gồm góc tay, chân, độ cao chi, hướng thân, nhịp bước → dùng làm mẫu so sánh cho các video khác.

📌 BƯỚC 2 — TRÍCH XUẤT ĐẶC ĐIỂM HÌNH HỌC (FEATURE EXTRACTION)

Làm gì:

Tính toán góc khớp, độ cao tay/chân, sải chân, nhịp bước từ skeleton mẫu.

Công nghệ:

NumPy, SciPy, Savitzky–Golay filter để làm mượt và tính toán vector.

Mục đích:

Xây dựng Profile Điều Lệnh Chuẩn chứa các giá trị chuẩn hóa (ví dụ: góc tay 60°, sải chân X cm, nhịp 106 bước/phút).

📌 BƯỚC 3 — XỬ LÝ VIDEO MỚI (TÂN BINH / NHÓM)

Làm gì:

Xử lý video đầu vào, trích skeleton, làm mượt dữ liệu và tách các pha chuyển động.

Công nghệ:

OpenCV, RTMPose / YOLO-Pose

Keyframe detection, OC-SORT (nếu nhiều người).

Mục đích:

Chuẩn hóa video mới để đảm bảo dữ liệu so sánh tương thích với mẫu chuẩn.

📌 BƯỚC 4 — CĂN CHỈNH THỜI GIAN (TEMPORAL ALIGNMENT)

Làm gì:

Khớp nhịp và pha chuyển động giữa video mẫu và video mới.

Công nghệ:

Dynamic Time Warping (DTW)

Mục đích:

Xử lý trường hợp tân binh đi nhanh/chậm khác mẫu → bảo đảm so sánh công bằng và chính xác.

📌 BƯỚC 5 — SO SÁNH HÌNH HỌC (GEOMETRIC MATCHING)

Làm gì:

Đo sai lệch góc, độ cao tay/chân, hướng vector xương, độ ổn định thân người.

Công nghệ:

Góc khớp, Cosine similarity, phân tích vector.

Mục đích:

Tạo các chỉ số lỗi chính xác ở từng thời điểm: lệch tay, lệch góc chân, gập gối, cúi đầu, sai nhịp…

📌 BƯỚC 6 — TÍNH ĐIỂM

Làm gì:

Quy đổi sai lệch thành điểm số, áp dụng trọng số cho từng yếu tố (kỹ thuật – nhịp – ổn định).

Công nghệ:

Công thức tính điểm theo sai số góc, sai nhịp DTW, độ ổn định của cột sống…

Mục đích:

Cho ra điểm tổng kết công bằng, minh bạch và có thể giải thích.

📌 BƯỚC 7 — XUẤT LỖI CHO HUẤN LUYỆN VIÊN

Làm gì:

Tạo báo cáo lỗi: tay thấp bao nhiêu độ, chân không thẳng, nhịp sai bao nhiêu %, đầu cúi bao nhiêu độ…

Công nghệ:

Overlay lên video bằng OpenCV hoặc render HTML/video.

Mục đích:

Hỗ trợ huấn luyện viên xem trực quan lỗi sai để chỉnh quân nhanh và chính xác.