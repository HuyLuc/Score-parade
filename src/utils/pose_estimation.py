"""
Wrapper cho pose estimation models (RTMPose và YOLOv8-Pose)
"""
import numpy as np
import cv2
from typing import List, Tuple, Optional
import src.config as config


class PoseEstimator:
    """Base class cho pose estimation"""
    
    def __init__(self, model_type: str = None):
        self.model_type = model_type or config.POSE_CONFIG["model_type"]
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Khởi tạo model"""
        if self.model_type == "rtmpose":
            self._init_rtmpose()
        elif self.model_type == "yolov8":
            self._init_yolov8()
        else:
            raise ValueError(f"Model type không được hỗ trợ: {self.model_type}")
    
    def _init_rtmpose(self):
        """Khởi tạo RTMPose"""
        try:
            from mmpose.apis import MMPoseInferencer
            
            model_name = config.POSE_CONFIG["rtmpose_model"]
            device = config.POSE_CONFIG["device"]
            
            self.model = MMPoseInferencer(
                pose2d=model_name,
                device=device
            )
            print(f"Đã khởi tạo RTMPose: {model_name}")
        except ImportError:
            raise ImportError(
                "Cần cài đặt mmpose. Chạy: pip install mmpose mmcv mmengine"
            )
    
    def _init_yolov8(self):
        """Khởi tạo YOLOv8-Pose"""
        try:
            from ultralytics import YOLO
            
            model_path = config.MODELS_DIR / config.POSE_CONFIG["yolov8_model"]
            if not model_path.exists():
                # Tự động download nếu chưa có
                print(f"Downloading YOLOv8-Pose model...")
                model = YOLO(config.POSE_CONFIG["yolov8_model"])
                model_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                model = YOLO(str(model_path))
            
            self.model = model
            print(f"Đã khởi tạo YOLOv8-Pose")
        except ImportError:
            raise ImportError(
                "Cần cài đặt ultralytics. Chạy: pip install ultralytics"
            )
    
    def predict(self, frame: np.ndarray) -> List[np.ndarray]:
        """
        Dự đoán pose cho một frame
        
        Args:
            frame: Frame ảnh (BGR format)
            
        Returns:
            List các keypoints, mỗi người là array [17, 3] với (x, y, confidence)
        """
        if self.model_type == "rtmpose":
            return self._predict_rtmpose(frame)
        elif self.model_type == "yolov8":
            return self._predict_yolov8(frame)
    
    def _predict_rtmpose(self, frame: np.ndarray) -> List[np.ndarray]:
        """Dự đoán bằng RTMPose"""
        results = list(self.model(frame))
        
        if not results or len(results) == 0:
            return []
        
        # RTMPose trả về dict với key 'predictions'
        result = results[0]
        if isinstance(result, dict) and 'predictions' in result:
            predictions = result['predictions']
        else:
            predictions = result
        
        keypoints_list = []
        for pred in predictions:
            if 'keypoints' in pred:
                kpts = pred['keypoints']  # [17, 2] hoặc [17, 3]
                if kpts.shape[1] == 2:
                    # Thêm confidence = 1.0 nếu không có
                    confidence = np.ones((kpts.shape[0], 1))
                    kpts = np.concatenate([kpts, confidence], axis=1)
                keypoints_list.append(kpts)
        
        return keypoints_list
    
    def _predict_yolov8(self, frame: np.ndarray) -> List[np.ndarray]:
        """Dự đoán bằng YOLOv8-Pose"""
        results = self.model(frame, verbose=False)
        
        keypoints_list = []
        for result in results:
            if result.keypoints is not None:
                keypoints = result.keypoints.data.cpu().numpy()  # [n_people, 17, 3]
                for kpts in keypoints:
                    keypoints_list.append(kpts)
        
        return keypoints_list
    
    def predict_batch(self, frames: List[np.ndarray]) -> List[List[np.ndarray]]:
        """
        Dự đoán pose cho nhiều frames
        
        Args:
            frames: List các frame
            
        Returns:
            List các kết quả, mỗi phần tử là list keypoints cho frame đó
        """
        results = []
        for frame in frames:
            keypoints = self.predict(frame)
            results.append(keypoints)
        return results


def extract_skeleton_from_video(
    video_path: str,
    model_type: Optional[str] = None
) -> Tuple[List[np.ndarray], dict]:
    """
    Trích xuất skeleton từ video
    
    Args:
        video_path: Đường dẫn video
        model_type: "rtmpose" hoặc "yolov8", None để dùng config
        
    Returns:
        Tuple (skeletons, metadata):
        - skeletons: List các frame, mỗi frame là list keypoints
        - metadata: Thông tin video
    """
    from src.utils.video_utils import load_video, get_frames
    
    estimator = PoseEstimator(model_type)
    cap, metadata = load_video(video_path)
    
    skeletons = []
    for frame in get_frames(cap):
        keypoints = estimator.predict(frame)
        skeletons.append(keypoints)
    
    cap.release()
    
    return skeletons, metadata

