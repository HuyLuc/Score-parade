"""
Web Interface cho Hệ Thống Đánh Giá Điều Lệnh Quân Đội
"""
import streamlit as st
import os
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import shutil
import time

# Page config
st.set_page_config(
    page_title="Đánh Giá Điều Lệnh Quân Đội",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    .score-value {
        font-size: 4rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin: 0.5rem 0;
    }
    
    .metric-title {
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #333;
    }
    
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        color: #155724;
        margin: 1rem 0;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 1rem;
        color: #856404;
        margin: 1rem 0;
    }
    
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        color: #721c24;
        margin: 1rem 0;
    }
    
    .recommendation {
        background: #f8f9fa;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)

def get_score_color(score):
    """Lấy màu dựa trên điểm số"""
    if score >= 8:
        return "#28a745"  # Green
    elif score >= 6:
        return "#ffc107"  # Yellow
    elif score >= 4:
        return "#fd7e14"  # Orange
    else:
        return "#dc3545"  # Red

def get_score_grade(score):
    """Lấy xếp loại dựa trên điểm số"""
    if score >= 9:
        return "Xuất Sắc 🏆"
    elif score >= 8:
        return "Giỏi ⭐"
    elif score >= 6.5:
        return "Khá 👍"
    elif score >= 5:
        return "Trung Bình 📊"
    else:
        return "Cần Cải Thiện 📈"

def generate_recommendations(scores, errors):
    """Tạo các khuyến nghị cải thiện"""
    recommendations = []
    
    # Lấy breakdown scores
    breakdown = scores.get('breakdown', {})
    
    # Lấy summary errors
    summary = errors.get('summary', {})
    
    # Kiểm tra kỹ thuật tay
    if breakdown.get('arm_technique', 10) < 6:
        arm_left = summary.get('arm_angle', {}).get('left', {}).get('mean', 0)
        arm_right = summary.get('arm_angle', {}).get('right', {}).get('mean', 0)
        if arm_left > 20:
            recommendations.append({
                'title': '🤚 Cải thiện tay trái',
                'detail': f'Góc tay trái lệch {arm_left:.1f}°. Hãy chú ý giữ tay thẳng và song song với thân người.',
                'priority': 'high'
            })
        if arm_right > 20:
            recommendations.append({
                'title': '🤚 Cải thiện tay phải',
                'detail': f'Góc tay phải lệch {arm_right:.1f}°. Hãy chú ý giữ tay thẳng và song song với thân người.',
                'priority': 'high'
            })
    
    # Kiểm tra kỹ thuật chân
    if breakdown.get('leg_technique', 10) < 6:
        leg_left = summary.get('leg_angle', {}).get('left', {}).get('mean', 0)
        leg_right = summary.get('leg_angle', {}).get('right', {}).get('mean', 0)
        if leg_left > 15:
            recommendations.append({
                'title': '🦵 Cải thiện chân trái',
                'detail': f'Góc chân trái lệch {leg_left:.1f}°. Hãy nâng cao chân hơn và giữ góc vuông với đùi.',
                'priority': 'high'
            })
        if leg_right > 15:
            recommendations.append({
                'title': '🦵 Cải thiện chân phải',
                'detail': f'Góc chân phải lệch {leg_right:.1f}°. Hãy nâng cao chân hơn và giữ góc vuông với đùi.',
                'priority': 'high'
            })
    
    # Kiểm tra nhịp bước
    if breakdown.get('step_rhythm', 10) < 8:
        recommendations.append({
            'title': '🎵 Cải thiện nhịp bước',
            'detail': 'Nhịp bước chưa đều. Hãy tập với nhạc hoặc đếm nhịp để duy trì tốc độ ổn định.',
            'priority': 'medium'
        })
    
    # Kiểm tra ổn định thân
    if breakdown.get('torso_stability', 10) < 7:
        head_error = summary.get('head_angle', {}).get('mean', 0)
        torso_error = summary.get('torso_angle', {}).get('mean', 0)
        if head_error > 10:
            recommendations.append({
                'title': '👤 Giữ đầu thẳng',
                'detail': f'Đầu bị nghiêng {head_error:.1f}°. Hãy nhìn thẳng phía trước và giữ cằm ngang.',
                'priority': 'medium'
            })
        if torso_error > 5:
            recommendations.append({
                'title': '🧍 Giữ thân thẳng',
                'detail': f'Thân người bị nghiêng {torso_error:.1f}°. Hãy duỗi thẳng lưng và siết bụng.',
                'priority': 'high'
            })
    
    # Nếu điểm tốt, khen ngợi
    if scores.get('total_score', 0) >= 8:
        recommendations.append({
            'title': '✨ Xuất sắc!',
            'detail': 'Kỹ thuật rất tốt! Hãy duy trì và tiếp tục rèn luyện để hoàn thiện hơn.',
            'priority': 'success'
        })
    
    return recommendations

def process_video(video_path):
    """Xử lý video và trả về kết quả"""
    try:
        # Chạy pipeline
        cmd = [
            sys.executable,
            "main.py",
            "--mode", "full",
            "--input-video", video_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=os.getcwd()
        )
        
        if result.returncode != 0:
            return None, f"Lỗi xử lý: {result.stderr}"
        
        # Đọc kết quả
        video_name = Path(video_path).stem
        output_path = Path("data/output") / video_name
        
        # Đọc điểm số
        score_file = output_path / "person_0_score.json"
        if not score_file.exists():
            return None, "Không tìm thấy kết quả điểm số"
        
        with open(score_file, 'r', encoding='utf-8') as f:
            scores = json.load(f)
        
        # Đọc lỗi
        error_file = output_path / "person_0_errors.json"
        if error_file.exists():
            with open(error_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        else:
            errors = {}
        
        # Lấy video kết quả
        annotated_video = output_path / "person_0_annotated.mp4"
        html_report = output_path / "person_0_report.html"
        
        return {
            'scores': scores,
            'errors': errors,
            'annotated_video': str(annotated_video) if annotated_video.exists() else None,
            'html_report': str(html_report) if html_report.exists() else None
        }, None
        
    except Exception as e:
        return None, f"Lỗi: {str(e)}"

def main():
    # Header
    st.markdown('<h1 class="main-header">🎖️ HỆ THỐNG ĐÁNH GIÁ ĐIỀU LỆNH QUÂN ĐỘI</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Cài đặt")
        
        # Golden template info
        st.subheader("📋 Mẫu chuẩn")
        golden_path = Path("data/golden_template/golden_profile.json")
        if golden_path.exists():
            with open(golden_path, 'r', encoding='utf-8') as f:
                golden = json.load(f)
                st.success(f"✅ Đã tải mẫu chuẩn ({golden.get('num_frames', 0)} frames)")
        else:
            st.warning("⚠️ Chưa có mẫu chuẩn")
            if st.button("Tạo mẫu chuẩn"):
                st.info("Vui lòng chạy: python main.py --mode golden --golden-video <video_path>")
        
        st.markdown("---")
        
        # About
        st.subheader("ℹ️ Về hệ thống")
        st.info("""
        **Hệ thống AI đánh giá điều lệnh** sử dụng:
        - YOLOv8-Pose để phát hiện khung xương
        - DTW để căn chỉnh thời gian
        - Phân tích góc hình học
        - Chấm điểm tự động theo 4 tiêu chí
        """)
        
        st.markdown("---")
        st.caption("Version 2.0 | © 2025")
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Upload Video")
        
        uploaded_file = st.file_uploader(
            "Chọn video điều lệnh của bạn",
            type=['mp4', 'avi', 'mov'],
            help="Video nên có 1 người thực hiện động tác điều lệnh"
        )
        
        if uploaded_file is not None:
            # Hiển thị video preview
            st.video(uploaded_file)
            
            # Thông tin video
            st.caption(f"📁 Tên file: {uploaded_file.name}")
            st.caption(f"📊 Kích thước: {uploaded_file.size / (1024*1024):.2f} MB")
            
            # Nút xử lý
            if st.button("🚀 Bắt đầu đánh giá", type="primary", use_container_width=True):
                # Tạo thư mục tạm
                with tempfile.TemporaryDirectory() as tmp_dir:
                    # Lưu video
                    video_path = Path(tmp_dir) / uploaded_file.name
                    with open(video_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("🔍 Đang phát hiện khung xương...")
                    progress_bar.progress(20)
                    time.sleep(0.5)
                    
                    status_text.text("🎯 Đang tracking người...")
                    progress_bar.progress(40)
                    time.sleep(0.5)
                    
                    status_text.text("⏱️ Đang căn chỉnh thời gian...")
                    progress_bar.progress(60)
                    
                    # Xử lý video
                    result, error = process_video(str(video_path))
                    
                    progress_bar.progress(80)
                    status_text.text("📊 Đang tính điểm...")
                    time.sleep(0.5)
                    
                    progress_bar.progress(100)
                    
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        status_text.text("✅ Hoàn thành!")
                        st.session_state['result'] = result
                        time.sleep(0.5)
                        status_text.empty()
                        progress_bar.empty()
    
    with col2:
        st.header("📊 Kết quả đánh giá")
        
        if 'result' in st.session_state:
            result = st.session_state['result']
            scores = result['scores']
            errors = result['errors']
            
            # Điểm tổng
            total_score = scores.get('total_score', 0)
            score_color = get_score_color(total_score)
            grade = get_score_grade(total_score)
            
            st.markdown(f"""
            <div class="score-card">
                <h2>ĐIỂM TỔNG</h2>
                <div class="score-value" style="color: white;">{total_score:.2f}/10</div>
                <h3>{grade}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Chi tiết điểm
            st.subheader("📋 Chi tiết điểm số")
            
            # Lấy breakdown từ scores
            breakdown = scores.get('breakdown', {})
            
            metrics_col1, metrics_col2 = st.columns(2)
            
            with metrics_col1:
                arm_score = breakdown.get('arm_technique', 0)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">🤚 Kỹ thuật tay</div>
                    <div class="metric-value" style="color: {get_score_color(arm_score)};">{arm_score:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
                rhythm_score = breakdown.get('step_rhythm', 0)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">🎵 Nhịp bước</div>
                    <div class="metric-value" style="color: {get_score_color(rhythm_score)};">{rhythm_score:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with metrics_col2:
                leg_score = breakdown.get('leg_technique', 0)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">🦵 Kỹ thuật chân</div>
                    <div class="metric-value" style="color: {get_score_color(leg_score)};">{leg_score:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
                stability_score = breakdown.get('torso_stability', 0)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">🧍 Ổn định thân</div>
                    <div class="metric-value" style="color: {get_score_color(stability_score)};">{stability_score:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Khuyến nghị
            st.subheader("💡 Nhận xét & Khuyến nghị cải thiện")
            recommendations = generate_recommendations(scores, errors)
            
            for rec in recommendations:
                priority = rec['priority']
                if priority == 'high':
                    icon = "🔴"
                    box_class = "error-box"
                elif priority == 'medium':
                    icon = "🟡"
                    box_class = "warning-box"
                else:
                    icon = "🟢"
                    box_class = "success-box"
                
                st.markdown(f"""
                <div class="{box_class}">
                    <strong>{icon} {rec['title']}</strong><br/>
                    {rec['detail']}
                </div>
                """, unsafe_allow_html=True)
            
            # Video kết quả
            if result['annotated_video'] and Path(result['annotated_video']).exists():
                st.subheader("🎬 Video phân tích")
                try:
                    # Đọc file video và hiển thị
                    video_path = Path(result['annotated_video'])
                    if video_path.exists():
                        with open(video_path, 'rb') as video_file:
                            video_bytes = video_file.read()
                        st.video(video_bytes, format='video/mp4')
                    else:
                        st.error(f"Không tìm thấy video: {video_path}")
                except Exception as e:
                    st.error(f"Lỗi khi tải video: {e}")
            
            # Download report
            if result['html_report'] and Path(result['html_report']).exists():
                with open(result['html_report'], 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                st.download_button(
                    label="📥 Tải báo cáo HTML",
                    data=html_content,
                    file_name="bao_cao_danh_gia.html",
                    mime="text/html",
                    use_container_width=True
                )
        
        else:
            st.info("👈 Vui lòng upload video để bắt đầu đánh giá")
            
            # Hiển thị hướng dẫn
            st.markdown("""
            ### 📖 Hướng dẫn sử dụng
            
            1. **Upload video** của bạn ở bên trái
            2. **Nhấn nút "Bắt đầu đánh giá"** để hệ thống phân tích
            3. **Xem kết quả** điểm số và nhận xét cải thiện
            4. **Tải báo cáo** để lưu lại kết quả
            
            ### ✅ Lưu ý
            - Video nên quay rõ ràng, đủ sáng
            - Chỉ có 1 người trong khung hình
            - Thời lượng video nên từ 5-30 giây
            - Quay toàn thân, không bị che khuất
            """)

if __name__ == "__main__":
    main()
