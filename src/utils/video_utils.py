"""
Utilities cho xử lý video cơ bản
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Iterator
import src.config as config


def load_video(video_path: Path) -> Tuple[cv2.VideoCapture, dict]:
    """
    Load video và trả về VideoCapture object cùng metadata
    
    Args:
        video_path: Đường dẫn đến file video
        
    Returns:
        Tuple (cap, metadata) với:
        - cap: cv2.VideoCapture object
        - metadata: dict chứa thông tin video (fps, width, height, frame_count)
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video không tồn tại: {video_path}")
    
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        raise ValueError(f"Không thể mở video: {video_path}")
    
    # Lấy metadata
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    metadata = {
        "fps": fps,
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "duration": frame_count / fps if fps > 0 else 0,
    }
    
    return cap, metadata


def get_frames(cap: cv2.VideoCapture) -> Iterator[np.ndarray]:
    """
    Generator để lấy từng frame từ video
    
    Args:
        cap: cv2.VideoCapture object
        
    Yields:
        Frame (numpy array) hoặc None nếu không đọc được
    """
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        yield frame


def save_video(
    frames: list,
    output_path: Path,
    fps: float,
    width: int,
    height: int,
    codec: str = "mp4v"
) -> None:
    """
    Lưu danh sách frames thành video file
    
    Args:
        frames: List các frame (numpy arrays)
        output_path: Đường dẫn file output
        fps: Frame rate
        width: Chiều rộng video
        height: Chiều cao video
        codec: Video codec (mặc định: mp4v)
    """
    fourcc = cv2.VideoWriter_fourcc(*codec)
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    for frame in frames:
        out.write(frame)
    
    out.release()


def resize_frame(frame: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
    """
    Resize frame về kích thước target
    
    Args:
        frame: Frame cần resize
        target_size: (width, height) mong muốn
        
    Returns:
        Frame đã được resize
    """
    return cv2.resize(frame, target_size, interpolation=cv2.INTER_LINEAR)


def validate_video(video_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra video có hợp lệ không
    
    Args:
        video_path: Đường dẫn đến video
        
    Returns:
        Tuple (is_valid, error_message)
    """
    if not video_path.exists():
        return False, f"File không tồn tại: {video_path}"
    
    if video_path.suffix.lower() not in config.VIDEO_CONFIG["supported_formats"]:
        return False, f"Format không được hỗ trợ: {video_path.suffix}"
    
    try:
        cap, metadata = load_video(video_path)
        cap.release()
        
        # Kiểm tra độ phân giải
        # Kiểm tra tổng số pixel thay vì width/height riêng lẻ (để hỗ trợ cả video ngang và dọc)
        min_w, min_h = config.VIDEO_CONFIG["min_resolution"]
        min_pixels = min_w * min_h  # 1280 * 720 = 921,600 pixels (720p)
        video_pixels = metadata["width"] * metadata["height"]
        
        # Hoặc kiểm tra chiều nhỏ hơn phải >= 720 (hỗ trợ video dọc)
        min_dimension = min(metadata["width"], metadata["height"])
        if video_pixels < min_pixels and min_dimension < 720:
            return False, f"Độ phân giải quá thấp: {metadata['width']}x{metadata['height']} (tối thiểu 720p: {min_w}x{min_h} hoặc tổng {min_pixels:,} pixels)"
        
        # Kiểm tra FPS
        min_fps = config.VIDEO_CONFIG["min_fps"]
        strict = config.VIDEO_CONFIG.get("strict_validation", False)
        
        if metadata["fps"] < min_fps:
            if strict:
                return False, f"FPS quá thấp: {metadata['fps']} (tối thiểu: {min_fps})"
            else:
                # Chỉ cảnh báo, không reject
                print(f"⚠️  Cảnh báo: FPS thấp ({metadata['fps']} < {min_fps}), nhưng vẫn tiếp tục xử lý...")
        
        return True, None
    except Exception as e:
        return False, f"Lỗi khi đọc video: {str(e)}"


def extract_frame_at_time(video_path: Path, time_seconds: float) -> Optional[np.ndarray]:
    """
    Trích xuất frame tại thời điểm cụ thể
    
    Args:
        video_path: Đường dẫn video
        time_seconds: Thời điểm (giây)
        
    Returns:
        Frame tại thời điểm đó hoặc None
    """
    cap, metadata = load_video(video_path)
    
    frame_number = int(time_seconds * metadata["fps"])
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    
    ret, frame = cap.read()
    cap.release()
    
    return frame if ret else None

