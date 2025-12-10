"""
CameraController - Điều khiển việc kết nối và nhận dữ liệu từ Camera
"""
import cv2
from typing import List, Optional, Dict, Tuple
from backend.app.config import CAMERA_CONFIG


class CameraController:
    """Controller cho camera management"""
    
    def __init__(self):
        self.cameras: Dict[int, cv2.VideoCapture] = {}
        self.max_cameras = CAMERA_CONFIG["max_cameras"]
    
    def connect_camera(self, camera_id: int) -> Tuple[bool, Optional[str]]:
        """
        Kết nối camera
        
        Args:
            camera_id: ID của camera (0, 1, 2, ...)
            
        Returns:
            (success, error_message)
        """
        if len(self.cameras) >= self.max_cameras:
            return False, f"Đã đạt số lượng camera tối đa ({self.max_cameras})"
        
        if camera_id in self.cameras:
            return False, f"Camera {camera_id} đã được kết nối"
        
        try:
            cap = cv2.VideoCapture(camera_id)
            
            if not cap.isOpened():
                return False, f"Không thể mở camera {camera_id}"
            
            # Set resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_CONFIG["default_resolution"][0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_CONFIG["default_resolution"][1])
            cap.set(cv2.CAP_PROP_FPS, CAMERA_CONFIG["default_fps"])
            
            self.cameras[camera_id] = cap
            return True, None
        
        except Exception as e:
            return False, f"Lỗi kết nối camera {camera_id}: {str(e)}"
    
    def disconnect_camera(self, camera_id: int) -> Tuple[bool, Optional[str]]:
        """
        Ngắt kết nối camera
        
        Args:
            camera_id: ID của camera
            
        Returns:
            (success, error_message)
        """
        if camera_id not in self.cameras:
            return False, f"Camera {camera_id} chưa được kết nối"
        
        try:
            cap = self.cameras.pop(camera_id)
            cap.release()
            return True, None
        except Exception as e:
            return False, f"Lỗi ngắt kết nối camera {camera_id}: {str(e)}"
    
    def get_frame(self, camera_id: int) -> Optional[Tuple[bytes, int, int]]:
        """
        Lấy frame từ camera
        
        Args:
            camera_id: ID của camera
            
        Returns:
            (frame_bytes, width, height) hoặc None nếu lỗi
        """
        if camera_id not in self.cameras:
            return None
        
        cap = self.cameras[camera_id]
        ret, frame = cap.read()
        
        if not ret:
            return None
        
        # Encode frame thành JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        height, width = frame.shape[:2]
        return frame_bytes, width, height
    
    def get_all_frames(self) -> Dict[int, Optional[Tuple[bytes, int, int]]]:
        """
        Lấy frame từ tất cả cameras
        
        Returns:
            Dict {camera_id: (frame_bytes, width, height)}
        """
        frames = {}
        for camera_id in list(self.cameras.keys()):
            frames[camera_id] = self.get_frame(camera_id)
        return frames
    
    def get_camera_info(self, camera_id: int) -> Optional[Dict]:
        """
        Lấy thông tin camera
        
        Args:
            camera_id: ID của camera
            
        Returns:
            Dict chứa thông tin camera hoặc None
        """
        if camera_id not in self.cameras:
            return None
        
        cap = self.cameras[camera_id]
        return {
            "camera_id": camera_id,
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "is_opened": cap.isOpened(),
        }
    
    def get_all_cameras_info(self) -> List[Dict]:
        """Lấy thông tin tất cả cameras"""
        return [
            self.get_camera_info(camera_id)
            for camera_id in self.cameras.keys()
        ]
    
    def disconnect_all(self):
        """Ngắt kết nối tất cả cameras"""
        for camera_id in list(self.cameras.keys()):
            self.disconnect_camera(camera_id)
    
    def __del__(self):
        """Cleanup khi object bị destroy"""
        self.disconnect_all()

