"""
Wrapper cho pose estimation models (RTMPose và YOLOv8-Pose)
"""
import numpy as np
import cv2
from typing import List, Tuple, Optional
import backend.app.config as config


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
        conf_threshold = config.POSE_CONFIG.get("conf_threshold", 0.20)
        kpt_conf_threshold = config.POSE_CONFIG.get("keypoint_confidence_threshold", 0.25)
        
        results = self.model(frame, verbose=False, conf=conf_threshold)
        
        keypoints_list = []
        candidates = []
        
        for result in results:
            if result.keypoints is not None and len(result.boxes) > 0:
                keypoints = result.keypoints.data.cpu().numpy()  # [n_people, 17, 3]
                boxes = result.boxes.data.cpu().numpy()  # [n_people, 6] (x1,y1,x2,y2,conf,cls)
                
                for i, kpts in enumerate(keypoints):
                    # Lọc theo box confidence
                    box_conf = boxes[i, 4]
                    if box_conf < conf_threshold:
                        continue
                    
                    # Đếm số keypoints có confidence cao
                    valid_kpts = np.sum(kpts[:, 2] > kpt_conf_threshold)
                    
                    # Lấy min từ config, mặc định 5 keypoints
                    min_valid = config.POSE_CONFIG.get('min_valid_keypoints', 5)
                    if valid_kpts >= min_valid:
                        # Tính bbox area để ưu tiên người lớn hơn
                        x1, y1, x2, y2 = boxes[i, :4]
                        bbox_area = (x2 - x1) * (y2 - y1)
                        # Sử dụng combination của confidence và size
                        score = float(box_conf) * 0.7 + (bbox_area / (frame.shape[0] * frame.shape[1])) * 0.3
                        candidates.append((score, kpts))
        
        # Giới hạn số người theo cấu hình, ưu tiên score cao nhất
        max_persons = config.MULTI_PERSON_CONFIG.get("max_persons", 5)
        candidates.sort(key=lambda x: x[0], reverse=True)
        keypoints_list = [k for _, k in candidates[:max_persons]]
        
        return keypoints_list
    
    def predict_batch(self, frames: List[np.ndarray], batch_size: int = None) -> List[List[np.ndarray]]:
        """
        Dự đoán pose cho nhiều frames với batch processing
        
        Args:
            frames: List các frame
            batch_size: Số frame xử lý cùng lúc
            
        Returns:
            List các kết quả, mỗi phần tử là list keypoints cho frame đó
        """
        if batch_size is None:
            batch_size = config.POSE_CONFIG.get("batch_size", 1)
        
        results = []
        
        # Xử lý theo batch nếu model là YOLOv8
        if self.model_type == "yolov8" and batch_size > 1:
            for i in range(0, len(frames), batch_size):
                batch_frames = frames[i:i+batch_size]
                batch_results = self.model(batch_frames, verbose=False, 
                                          conf=config.POSE_CONFIG.get("conf_threshold", 0.20))
                
                for result in batch_results:
                    keypoints_list = []
                    candidates = []
                    if result.keypoints is not None and len(result.boxes) > 0:
                        keypoints = result.keypoints.data.cpu().numpy()
                        boxes = result.boxes.data.cpu().numpy()
                        kpt_conf_threshold = config.POSE_CONFIG.get("keypoint_confidence_threshold", 0.25)
                        conf_threshold = config.POSE_CONFIG.get("conf_threshold", 0.20)
                        
                        for j, kpts in enumerate(keypoints):
                            if boxes[j, 4] >= conf_threshold:
                                valid_kpts = np.sum(kpts[:, 2] > kpt_conf_threshold)
                                min_valid = config.POSE_CONFIG.get('min_valid_keypoints', 5)
                                if valid_kpts >= min_valid:
                                    # Tính score combination
                                    x1, y1, x2, y2 = boxes[j, :4]
                                    bbox_area = (x2 - x1) * (y2 - y1)
                                    frame_area = result.orig_shape[0] * result.orig_shape[1] if hasattr(result, 'orig_shape') else 1
                                    score = float(boxes[j, 4]) * 0.7 + (bbox_area / frame_area) * 0.3
                                    candidates.append((score, kpts))
                        
                        # Sắp xếp và giới hạn
                        max_persons = config.MULTI_PERSON_CONFIG.get("max_persons", 5)
                        candidates.sort(key=lambda x: x[0], reverse=True)
                        keypoints_list = [k for _, k in candidates[:max_persons]]
                    results.append(keypoints_list)
        else:
            # Xử lý từng frame
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
    from backend.app.services.video_utils import load_video, get_frames
    
    estimator = PoseEstimator(model_type)
    cap, metadata = load_video(video_path)
    
    skeletons = []
    for frame in get_frames(cap):
        keypoints = estimator.predict(frame)
        skeletons.append(keypoints)
    
    cap.release()
    
    return skeletons, metadata

