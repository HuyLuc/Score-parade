"""
VideoController - Điều khiển việc cắt lấy video từ video streaming
"""
import cv2
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
from backend.app.config import CAMERA_CONFIG, OUTPUT_DIR


class VideoController:
    """Controller cho video recording"""
    
    def __init__(self, camera_controller):
        self.camera_controller = camera_controller
        self.chunk_duration = CAMERA_CONFIG["video_chunk_duration"]  # Giây
        self.recordings: Dict[int, VideoRecorder] = {}  # {camera_id: VideoRecorder}
    
    def start_recording(
        self,
        camera_id: int,
        session_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Bắt đầu ghi video
        
        Args:
            camera_id: ID của camera
            session_id: ID của session
            
        Returns:
            (success, error_message)
        """
        if camera_id in self.recordings:
            return False, f"Camera {camera_id} đang ghi video"
        
        try:
            recorder = VideoRecorder(
                camera_id,
                self.camera_controller,
                session_id,
                self.chunk_duration
            )
            self.recordings[camera_id] = recorder
            recorder.start()
            return True, None
        except Exception as e:
            return False, f"Lỗi bắt đầu ghi video: {str(e)}"
    
    def stop_recording(self, camera_id: int) -> Optional[Path]:
        """
        Dừng ghi video và lưu file
        
        Args:
            camera_id: ID của camera
            
        Returns:
            Đường dẫn file video hoặc None nếu lỗi
        """
        if camera_id not in self.recordings:
            return None
        
        recorder = self.recordings.pop(camera_id)
        return recorder.stop()
    
    def get_current_chunk_path(self, camera_id: int) -> Optional[Path]:
        """
        Lấy đường dẫn video chunk hiện tại
        
        Args:
            camera_id: ID của camera
            
        Returns:
            Đường dẫn file hoặc None
        """
        if camera_id not in self.recordings:
            return None
        
        return self.recordings[camera_id].get_current_chunk_path()
    
    def stop_all_recordings(self) -> List[Path]:
        """Dừng tất cả recordings và trả về danh sách file paths"""
        paths = []
        for camera_id in list(self.recordings.keys()):
            path = self.stop_recording(camera_id)
            if path:
                paths.append(path)
        return paths


class VideoRecorder:
    """Class để ghi video từ camera"""
    
    def __init__(
        self,
        camera_id: int,
        camera_controller,
        session_id: Optional[int],
        chunk_duration: float
    ):
        self.camera_id = camera_id
        self.camera_controller = camera_controller
        self.session_id = session_id
        self.chunk_duration = chunk_duration
        self.video_dir = OUTPUT_DIR / "videos"
        self.video_dir.mkdir(parents=True, exist_ok=True)
        
        self.writer: Optional[cv2.VideoWriter] = None
        self.current_chunk_path: Optional[Path] = None
        self.chunk_start_time: Optional[datetime] = None
        self.fps = CAMERA_CONFIG["default_fps"]
        self.width = CAMERA_CONFIG["default_resolution"][0]
        self.height = CAMERA_CONFIG["default_resolution"][1]
    
    def start(self):
        """Bắt đầu ghi video"""
        self._create_new_chunk()
    
    def _create_new_chunk(self):
        """Tạo chunk video mới"""
        # Đóng chunk cũ nếu có
        if self.writer:
            self.writer.release()
        
        # Tạo file mới
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        if self.session_id:
            session_dir = self.video_dir / f"session_{self.session_id}"
            session_dir.mkdir(parents=True, exist_ok=True)
            self.current_chunk_path = session_dir / f"camera_{self.camera_id}_{timestamp}.mp4"
        else:
            self.current_chunk_path = self.video_dir / f"camera_{self.camera_id}_{timestamp}.mp4"
        
        # Tạo VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            str(self.current_chunk_path),
            fourcc,
            self.fps,
            (self.width, self.height)
        )
        
        self.chunk_start_time = datetime.now()
    
    def add_frame(self, frame: np.ndarray):
        """
        Thêm frame vào video
        
        Args:
            frame: Frame từ camera
        """
        if not self.writer:
            return
        
        # Kiểm tra nếu cần tạo chunk mới
        if self.chunk_start_time:
            elapsed = (datetime.now() - self.chunk_start_time).total_seconds()
            if elapsed >= self.chunk_duration:
                self._create_new_chunk()
        
        # Resize frame nếu cần
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        
        self.writer.write(frame)
    
    def get_current_chunk_path(self) -> Optional[Path]:
        """Lấy đường dẫn chunk hiện tại"""
        return self.current_chunk_path
    
    def stop(self) -> Optional[Path]:
        """
        Dừng ghi và trả về đường dẫn file cuối cùng
        
        Returns:
            Đường dẫn file video
        """
        if self.writer:
            self.writer.release()
            self.writer = None
        
        return self.current_chunk_path

