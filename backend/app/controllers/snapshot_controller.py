"""
SnapshotController - Điều khiển việc trích xuất ảnh từ video streaming
"""
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from backend.app.config import CAMERA_CONFIG, OUTPUT_DIR


class SnapshotController:
    """Controller cho snapshot management"""
    
    def __init__(self, camera_controller):
        self.camera_controller = camera_controller
        self.snapshot_interval = CAMERA_CONFIG["snapshot_interval"]  # Giây
        self.last_snapshot_time = {}  # {camera_id: timestamp}
        self.snapshot_dir = OUTPUT_DIR / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    def capture_snapshot(
        self,
        camera_id: int,
        save: bool = True,
        session_id: Optional[int] = None
    ) -> Optional[Tuple[bytes, Path]]:
        """
        Chụp snapshot từ camera
        
        Args:
            camera_id: ID của camera
            save: Có lưu file không
            session_id: ID của session (để tổ chức thư mục)
            
        Returns:
            (frame_bytes, file_path) hoặc None nếu lỗi
        """
        # Kiểm tra interval
        current_time = datetime.now().timestamp()
        if camera_id in self.last_snapshot_time:
            elapsed = current_time - self.last_snapshot_time[camera_id]
            if elapsed < self.snapshot_interval:
                return None  # Chưa đến lúc chụp
        
        # Lấy frame
        frame_data = self.camera_controller.get_frame(camera_id)
        if not frame_data:
            return None
        
        frame_bytes, width, height = frame_data
        
        # Cập nhật thời gian
        self.last_snapshot_time[camera_id] = current_time
        
        # Lưu file nếu cần
        file_path = None
        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            if session_id:
                session_dir = self.snapshot_dir / f"session_{session_id}"
                session_dir.mkdir(parents=True, exist_ok=True)
                file_path = session_dir / f"camera_{camera_id}_{timestamp}.jpg"
            else:
                file_path = self.snapshot_dir / f"camera_{camera_id}_{timestamp}.jpg"
            
            # Lưu file
            with open(file_path, 'wb') as f:
                f.write(frame_bytes)
        
        return frame_bytes, file_path
    
    def capture_snapshot_if_needed(
        self,
        camera_id: int,
        session_id: Optional[int] = None
    ) -> Optional[Tuple[bytes, Path]]:
        """
        Chụp snapshot nếu đã đủ thời gian (theo interval)
        
        Args:
            camera_id: ID của camera
            session_id: ID của session
            
        Returns:
            (frame_bytes, file_path) hoặc None nếu chưa đến lúc
        """
        return self.capture_snapshot(camera_id, save=True, session_id=session_id)
    
    def set_snapshot_interval(self, interval: float):
        """
        Đặt interval cho snapshot (giây)
        
        Args:
            interval: Khoảng thời gian giữa các snapshot (giây)
        """
        self.snapshot_interval = max(0.1, interval)  # Tối thiểu 0.1 giây

