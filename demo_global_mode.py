#!/usr/bin/env python3
"""
Demo script for testing Global Mode API workflow
Tests the complete flow: session start -> process frames -> get summary -> cleanup
"""
import os
import sys
import time
import cv2
import requests
from typing import Optional, Dict, List
import base64

# ============================================================
# Configuration
# ============================================================

SESSION_ID = "demo-test-session"
MODE = "testing"  # "testing" or "practising"
VIDEO_PATH = "data/input_videos/video1.mp4"
AUDIO_PATH = None  # Optional: Set path to audio file if needed
MAX_FRAMES = 300  # Test với 300 frames (~10s), None = full video
API_BASE = "http://localhost:8000"
FRAME_SKIP = 1  # Process every Nth frame (1 = all frames)
SLEEP_BETWEEN_FRAMES = 0.05  # Sleep time between frames (seconds)

# ============================================================
# Helper Functions
# ============================================================

def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"{title}")
    print("=" * 60)

def print_separator():
    """Print separator line"""
    print("-" * 60)

def format_score(score: float) -> str:
    """Format score with color-like representation"""
    if score >= 90:
        return f"🟢 {score:5.1f}"
    elif score >= 70:
        return f"🟡 {score:5.1f}"
    elif score >= 50:
        return f"🟠 {score:5.1f}"
    else:
        return f"🔴 {score:5.1f}"

def start_session(session_id: str, mode: str, audio_path: Optional[str] = None) -> Dict:
    """
    Start a global mode session
    
    Args:
        session_id: Unique session identifier
        mode: Mode type ("testing" or "practising")
        audio_path: Optional path to audio file
        
    Returns:
        Response from API
    """
    url = f"{API_BASE}/api/global/{session_id}/start"
    
    data = {"mode": mode}
    files = {}
    
    if audio_path:
        data["audio_path"] = audio_path
    
    try:
        response = requests.post(url, data=data, files=files)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print("❌ Lỗi: Không thể kết nối đến backend API")
        print(f"   Kiểm tra backend có đang chạy tại {API_BASE}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ Lỗi HTTP: {e}")
        print(f"   Response: {response.text}")
        sys.exit(1)

def process_frame(session_id: str, frame, timestamp: float, frame_number: int) -> Dict:
    """
    Process a video frame
    
    Args:
        session_id: Session identifier
        frame: Video frame (numpy array)
        timestamp: Frame timestamp in seconds
        frame_number: Frame number
        
    Returns:
        Response from API
    """
    url = f"{API_BASE}/api/global/{session_id}/process-frame"
    
    # Encode frame as JPEG
    success, buffer = cv2.imencode('.jpg', frame)
    if not success:
        raise ValueError("Failed to encode frame as JPEG")
    
    # Prepare multipart data
    files = {
        'frame_data': ('frame.jpg', buffer.tobytes(), 'image/jpeg')
    }
    data = {
        'timestamp': str(timestamp),
        'frame_number': str(frame_number)
    }
    
    response = requests.post(url, files=files, data=data)
    response.raise_for_status()
    return response.json()

def get_score(session_id: str) -> Dict:
    """Get current score"""
    url = f"{API_BASE}/api/global/{session_id}/score"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def get_errors(session_id: str) -> Dict:
    """Get all errors"""
    url = f"{API_BASE}/api/global/{session_id}/errors"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def delete_session(session_id: str) -> Dict:
    """Delete session"""
    url = f"{API_BASE}/api/global/{session_id}"
    response = requests.delete(url)
    response.raise_for_status()
    return response.json()

def format_error(error: Dict) -> str:
    """Format error for display"""
    error_type = error.get("type", "unknown")
    description = error.get("description", "")
    deduction = error.get("deduction", 0)
    
    if error_type == "rhythm":
        emoji = "🔴"
        prefix = "RHYTHM"
    else:
        emoji = "🟠"
        prefix = "POSTURE"
    
    return f"   {emoji} {prefix}: {description} (trừ {deduction:.1f} điểm)"

def display_motion_events(result: Dict) -> str:
    """Format motion events for display"""
    # Check if there are new motion events in the response
    # This depends on your API structure
    # For now, we'll just show a simple indicator
    return ""

# ============================================================
# Main Demo Flow
# ============================================================

def main():
    """Main demo function"""
    
    print("\n" + "#" * 60)
    print("#  DEMO: Global Mode API Workflow")
    print("#" * 60)
    
    # ========================================
    # Step 1: Start Session
    # ========================================
    print_header("🚀 Bước 1: Khởi tạo session")
    
    print(f"Session ID: {SESSION_ID}")
    print(f"Mode: {MODE}")
    
    try:
        result = start_session(SESSION_ID, MODE, AUDIO_PATH)
        print(f"✅ Session '{SESSION_ID}' đã được khởi tạo")
        print(f"   Mode: {result['mode']}")
        print(f"   Audio set: {result['audio_set']}")
    except Exception as e:
        print(f"❌ Lỗi khi khởi tạo session: {e}")
        return
    
    # ========================================
    # Step 2: Process Video
    # ========================================
    print_header("🎬 Bước 2: Xử lý video")
    
    # Check if video file exists
    video_path = os.path.join(os.path.dirname(__file__), VIDEO_PATH)
    if not os.path.exists(video_path):
        print(f"❌ Lỗi: Không tìm thấy video tại {video_path}")
        print("   Vui lòng cập nhật VIDEO_PATH trong script")
        return
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Lỗi: Không thể mở video {video_path}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"📹 Video: {VIDEO_PATH}")
    print(f"   FPS: {fps:.1f}")
    print(f"   Total frames: {total_frames}")
    print(f"   Duration: {duration:.1f}s")
    
    if MAX_FRAMES:
        print(f"   Processing: {MAX_FRAMES} frames (limit)")
    else:
        print(f"   Processing: All frames")
    
    print()
    
    # Process frames
    frame_count = 0
    processed_count = 0
    last_score = 100.0
    stopped = False
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Skip frames if needed
            if frame_count % FRAME_SKIP != 0:
                continue
            
            # Check frame limit
            if MAX_FRAMES and processed_count >= MAX_FRAMES:
                print(f"⏸️  Đạt giới hạn {MAX_FRAMES} frames")
                break
            
            timestamp = frame_count / fps if fps > 0 else frame_count * 0.033
            
            # Process frame
            try:
                result = process_frame(SESSION_ID, frame, timestamp, frame_count)
                processed_count += 1
                
                # Display progress
                errors_in_frame = result.get("errors", [])
                new_errors = [e for e in errors_in_frame if e.get("frame_number") == frame_count]
                score = result.get("score", 100.0)
                stopped = result.get("stopped", False)
                
                # Build status line
                status_parts = [
                    f"⏱️  Frame {frame_count:4d}",
                    f"{timestamp:6.2f}s",
                    f"Score: {format_score(score)}"
                ]
                
                # Show motion detection indicator (simplified)
                # In a real implementation, you'd parse motion events from result
                
                # Show new errors
                if new_errors:
                    status_parts.append(f"⚠️  {len(new_errors)} error(s)")
                
                print(" | ".join(status_parts))
                
                # Display error details
                for error in new_errors:
                    print(format_error(error))
                
                last_score = score
                
                # Check if stopped
                if stopped:
                    message = result.get("message", "")
                    print(f"\n🛑 {message}")
                    break
                
                # Small sleep to avoid overwhelming API
                time.sleep(SLEEP_BETWEEN_FRAMES)
                
            except Exception as e:
                print(f"❌ Lỗi khi xử lý frame {frame_count}: {e}")
                break
        
    finally:
        cap.release()
    
    print(f"\n✅ Đã xử lý {processed_count} frames")
    
    # ========================================
    # Step 3: Get Summary
    # ========================================
    print_header("📊 Bước 3: Tổng kết")
    
    try:
        # Get final score
        score_result = get_score(SESSION_ID)
        final_score = score_result.get("score", 0)
        
        # Get all errors
        errors_result = get_errors(SESSION_ID)
        all_errors = errors_result.get("errors", [])
        total_errors = errors_result.get("total_errors", 0)
        
        # Count by type
        rhythm_errors = [e for e in all_errors if e.get("type") == "rhythm"]
        posture_errors = [e for e in all_errors if e.get("type") == "posture"]
        
        print(f"🎯 Điểm cuối: {format_score(final_score)}/100")
        print(f"📝 Tổng lỗi: {total_errors}")
        print(f"   - Rhythm errors: {len(rhythm_errors)}")
        print(f"   - Posture errors: {len(posture_errors)}")
        
        if stopped:
            print(f"\n⚠️  Chế độ testing đã dừng do điểm số < 50")
        
    except Exception as e:
        print(f"❌ Lỗi khi lấy tổng kết: {e}")
    
    # ========================================
    # Step 4: Cleanup
    # ========================================
    print_header("🧹 Bước 4: Cleanup")
    
    try:
        delete_session(SESSION_ID)
        print(f"✅ Session '{SESSION_ID}' đã được xóa")
    except Exception as e:
        print(f"❌ Lỗi khi xóa session: {e}")
    
    print("\n✅ Demo hoàn tất!")
    print()

if __name__ == "__main__":
    main()
