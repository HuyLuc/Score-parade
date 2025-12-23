"""
Wrapper cho pose estimation models (MMPose/RTMPose, AlphaPose, và YOLOv8-Pose)
"""
import numpy as np
import cv2
from typing import List, Tuple, Optional
import backend.app.config as config


def filter_low_confidence_keypoints(keypoints: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """
    Mask keypoints với confidence < threshold
    
    Args:
        keypoints: Keypoints array [17, 3] với (x, y, confidence)
        threshold: Ngưỡng confidence tối thiểu (default: 0.5)
    
    Returns:
        Keypoints array với các keypoints có confidence < threshold được mask (set về 0)
    """
    if keypoints.shape[1] < 3:
        # Nếu không có confidence channel, return nguyên bản
        return keypoints
    
    # Tạo copy để không modify original
    filtered_keypoints = keypoints.copy()
    
    # Mask keypoints có confidence < threshold (set x, y về 0, giữ nguyên confidence)
    low_confidence_mask = filtered_keypoints[:, 2] < threshold
    filtered_keypoints[low_confidence_mask, 0] = 0  # x
    filtered_keypoints[low_confidence_mask, 1] = 0  # y
    # Giữ nguyên confidence để có thể debug
    
    return filtered_keypoints


class PoseEstimator:
    """Base class cho pose estimation"""
    
    def __init__(self, model_type: str = None):
        self.model_type = model_type or config.POSE_CONFIG["model_type"]
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Khởi tạo model"""
        if self.model_type in ["rtmpose", "mmpose"]:
            self._init_mmpose()
        elif self.model_type == "alphapose":
            self._init_alphapose()
        elif self.model_type == "yolov8":
            self._init_yolov8()
        else:
            raise ValueError(f"Model type không được hỗ trợ: {self.model_type}. Hỗ trợ: rtmpose/mmpose, alphapose, yolov8")
    
    def _init_mmpose(self):
        """Khởi tạo MMPose (RTMPose hoặc các models khác từ MMPose)"""
        try:
            from mmpose.apis import MMPoseInferencer
            
            # Lấy model name từ config, mặc định là RTMPose
            model_name = config.POSE_CONFIG.get("mmpose_model", "rtmpose-m_8xb256-420e_coco-256x192")
            device = config.POSE_CONFIG.get("device", "cpu")
            
            # MMPoseInferencer tự động download model nếu chưa có
            self.model = MMPoseInferencer(
                pose2d=model_name,
                device=device
            )
            print(f"✅ Đã khởi tạo MMPose: {model_name} trên {device}")
        except ImportError:
            raise ImportError(
                "Cần cài đặt mmpose. Chạy: pip install openmim && mim install mmengine mmcv mmpose"
            )
        except Exception as e:
            raise RuntimeError(f"Lỗi khởi tạo MMPose: {e}")
    
    def _init_alphapose(self):
        """Khởi tạo AlphaPose"""
        try:
            # AlphaPose có thể được sử dụng qua API hoặc trực tiếp
            # Sử dụng thư viện alphapose nếu có, hoặc gọi qua API
            import sys
            import os
            
            # Kiểm tra xem có alphapose trong path không
            alphapose_path = config.POSE_CONFIG.get("alphapose_path", None)
            if alphapose_path and os.path.exists(alphapose_path):
                sys.path.insert(0, alphapose_path)
            
            try:
                from detector import YOLOv5Detector
                from pose import YOLOv5PoseEstimator
                
                # Khởi tạo detector và pose estimator
                detector_cfg = config.POSE_CONFIG.get("alphapose_detector", "yolov5s")
                pose_cfg = config.POSE_CONFIG.get("alphapose_model", "fastpose_duc")
                device = config.POSE_CONFIG.get("device", "cpu")
                
                self.detector = YOLOv5Detector(detector_cfg, device=device)
                self.pose_estimator = YOLOv5PoseEstimator(pose_cfg, device=device)
                self.model = {"detector": self.detector, "pose": self.pose_estimator}
                
                print(f"✅ Đã khởi tạo AlphaPose: detector={detector_cfg}, pose={pose_cfg}")
            except ImportError:
                # Fallback: Sử dụng API hoặc wrapper khác
                # Có thể sử dụng thư viện alphapose-api hoặc gọi trực tiếp
                raise ImportError(
                    "AlphaPose chưa được cài đặt. Vui lòng cài đặt AlphaPose hoặc sử dụng MMPose."
                )
        except Exception as e:
            raise RuntimeError(f"Lỗi khởi tạo AlphaPose: {e}. Gợi ý: Sử dụng MMPose (rtmpose) thay thế.")
    
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
        if self.model_type in ["rtmpose", "mmpose"]:
            return self._predict_mmpose(frame)
        elif self.model_type == "alphapose":
            return self._predict_alphapose(frame)
        elif self.model_type == "yolov8":
            return self._predict_yolov8(frame)
    
    def _predict_mmpose(self, frame: np.ndarray) -> List[np.ndarray]:
        """Dự đoán bằng MMPose (RTMPose hoặc các models khác)"""
        try:
            results = list(self.model(frame))
            
            if not results or len(results) == 0:
                return []
            
            # MMPose trả về dict với key 'predictions'
            result = results[0]
            if isinstance(result, dict):
                if 'predictions' in result:
                    predictions = result['predictions']
                elif 'keypoints' in result:
                    # Trường hợp trả về trực tiếp keypoints
                    predictions = [result]
                else:
                    predictions = []
            else:
                predictions = [result] if result else []
            
            keypoints_list = []
            conf_threshold = config.POSE_CONFIG.get("conf_threshold", 0.15)
            kpt_conf_threshold = config.POSE_CONFIG.get("keypoint_confidence_threshold", 0.20)
            min_valid = config.POSE_CONFIG.get('min_valid_keypoints', 4)
            max_persons = config.MULTI_PERSON_CONFIG.get("max_persons", 5)
            
            candidates = []
            
            for pred in predictions:
                if isinstance(pred, dict):
                    if 'keypoints' in pred:
                        kpts = pred['keypoints']  # [17, 2] hoặc [17, 3]
                        keypoint_scores = pred.get('keypoint_scores', None)
                    elif 'pred_instances' in pred:
                        # Format khác của MMPose
                        instances = pred['pred_instances']
                        kpts = instances.keypoints.cpu().numpy() if hasattr(instances, 'keypoints') else None
                        keypoint_scores = instances.keypoint_scores.cpu().numpy() if hasattr(instances, 'keypoint_scores') else None
                    else:
                        continue
                else:
                    continue
                
                if kpts is None:
                    continue
                
                # Chuyển đổi format về [17, 3]
                if kpts.shape[1] == 2:
                    # Chỉ có x, y, cần thêm confidence
                    if keypoint_scores is not None:
                        # Sử dụng keypoint_scores từ model
                        confidence = keypoint_scores.reshape(-1, 1) if len(keypoint_scores.shape) == 1 else keypoint_scores
                    else:
                        # Mặc định confidence = 1.0
                        confidence = np.ones((kpts.shape[0], 1))
                    kpts = np.concatenate([kpts, confidence], axis=1)
                elif kpts.shape[1] == 3:
                    # Đã có confidence
                    pass
                else:
                    continue
                
                # Đảm bảo có đúng 17 keypoints (COCO format)
                if kpts.shape[0] != 17:
                    # Nếu không đúng format, skip
                    continue
                
                # Lọc theo confidence
                valid_kpts = np.sum(kpts[:, 2] > kpt_conf_threshold)
                if valid_kpts < min_valid:
                    continue
                
                # Tính score để ưu tiên
                avg_conf = np.mean(kpts[kpts[:, 2] > kpt_conf_threshold, 2]) if valid_kpts > 0 else 0.0
                candidates.append((avg_conf, kpts))
            
            # Sắp xếp và giới hạn số người
            candidates.sort(key=lambda x: x[0], reverse=True)
            keypoints_list = [k for _, k in candidates[:max_persons]]
            
            return keypoints_list
        except Exception as e:
            print(f"⚠️ Lỗi trong _predict_mmpose: {e}")
            return []
    
    def _predict_alphapose(self, frame: np.ndarray) -> List[np.ndarray]:
        """Dự đoán bằng AlphaPose"""
        try:
            # AlphaPose workflow: detect -> pose estimation
            if isinstance(self.model, dict) and "detector" in self.model and "pose" in self.model:
                # Detect persons
                detections = self.model["detector"].detect(frame)
                
                if len(detections) == 0:
                    return []
                
                keypoints_list = []
                conf_threshold = config.POSE_CONFIG.get("conf_threshold", 0.15)
                kpt_conf_threshold = config.POSE_CONFIG.get("keypoint_confidence_threshold", 0.20)
                min_valid = config.POSE_CONFIG.get('min_valid_keypoints', 4)
                max_persons = config.MULTI_PERSON_CONFIG.get("max_persons", 5)
                
                candidates = []
                
                for det in detections:
                    # Lọc theo detection confidence
                    if det.get("confidence", 0) < conf_threshold:
                        continue
                    
                    # Estimate pose
                    bbox = det.get("bbox", None)
                    if bbox is None:
                        continue
                    
                    kpts = self.model["pose"].estimate(frame, bbox)
                    
                    if kpts is None or kpts.shape[0] != 17:
                        continue
                    
                    # Đảm bảo format [17, 3]
                    if kpts.shape[1] == 2:
                        # Thêm confidence
                        confidence = np.ones((kpts.shape[0], 1))
                        kpts = np.concatenate([kpts, confidence], axis=1)
                    
                    # Lọc theo keypoint confidence
                    valid_kpts = np.sum(kpts[:, 2] > kpt_conf_threshold)
                    if valid_kpts < min_valid:
                        continue
                    
                    # Tính score
                    avg_conf = np.mean(kpts[kpts[:, 2] > kpt_conf_threshold, 2]) if valid_kpts > 0 else 0.0
                    candidates.append((avg_conf, kpts))
                
                # Sắp xếp và giới hạn
                candidates.sort(key=lambda x: x[0], reverse=True)
                keypoints_list = [k for _, k in candidates[:max_persons]]
                
                return keypoints_list
            else:
                # Fallback: Nếu không có detector/pose riêng, thử API hoặc wrapper khác
                raise NotImplementedError("AlphaPose chưa được cấu hình đúng. Vui lòng sử dụng MMPose.")
        except Exception as e:
            print(f"⚠️ Lỗi trong _predict_alphapose: {e}")
            return []
    
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
        
        # Xử lý theo batch nếu model hỗ trợ
        if self.model_type == "yolov8" and batch_size > 1:
            # YOLOv8 hỗ trợ batch processing tốt
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
        elif self.model_type in ["rtmpose", "mmpose"] and batch_size > 1:
            # MMPose có thể xử lý batch nhưng cần xử lý từng frame để đảm bảo format đúng
            # Có thể optimize sau nếu cần
            for i in range(0, len(frames), batch_size):
                batch_frames = frames[i:i+batch_size]
                # MMPoseInferencer có thể nhận list frames
                batch_results = list(self.model(batch_frames))
                
                # Xử lý từng kết quả trong batch
                for result in batch_results:
                    keypoints = self._predict_mmpose_single_result(result)
                    results.append(keypoints)
        else:
            # Xử lý từng frame (cho alphapose hoặc batch_size=1)
            for frame in frames:
                keypoints = self.predict(frame)
                results.append(keypoints)
        
        return results
    
    def _predict_mmpose_single_result(self, result) -> List[np.ndarray]:
        """Helper method để xử lý một kết quả từ MMPose batch"""
        if not result:
            return []
        
        # Tương tự logic trong _predict_mmpose nhưng cho một result
        if isinstance(result, dict):
            if 'predictions' in result:
                predictions = result['predictions']
            elif 'keypoints' in result:
                predictions = [result]
            else:
                predictions = []
        else:
            predictions = [result] if result else []
        
        keypoints_list = []
        conf_threshold = config.POSE_CONFIG.get("conf_threshold", 0.15)
        kpt_conf_threshold = config.POSE_CONFIG.get("keypoint_confidence_threshold", 0.20)
        min_valid = config.POSE_CONFIG.get('min_valid_keypoints', 4)
        max_persons = config.MULTI_PERSON_CONFIG.get("max_persons", 5)
        
        candidates = []
        
        for pred in predictions:
            if isinstance(pred, dict):
                if 'keypoints' in pred:
                    kpts = pred['keypoints']
                    keypoint_scores = pred.get('keypoint_scores', None)
                elif 'pred_instances' in pred:
                    instances = pred['pred_instances']
                    kpts = instances.keypoints.cpu().numpy() if hasattr(instances, 'keypoints') else None
                    keypoint_scores = instances.keypoint_scores.cpu().numpy() if hasattr(instances, 'keypoint_scores') else None
                else:
                    continue
            else:
                continue
            
            if kpts is None:
                continue
            
            # Chuyển đổi format về [17, 3]
            if kpts.shape[1] == 2:
                if keypoint_scores is not None:
                    confidence = keypoint_scores.reshape(-1, 1) if len(keypoint_scores.shape) == 1 else keypoint_scores
                else:
                    confidence = np.ones((kpts.shape[0], 1))
                kpts = np.concatenate([kpts, confidence], axis=1)
            elif kpts.shape[1] == 3:
                pass
            else:
                continue
            
            if kpts.shape[0] != 17:
                continue
            
            valid_kpts = np.sum(kpts[:, 2] > kpt_conf_threshold)
            if valid_kpts < min_valid:
                continue
            
            avg_conf = np.mean(kpts[kpts[:, 2] > kpt_conf_threshold, 2]) if valid_kpts > 0 else 0.0
            candidates.append((avg_conf, kpts))
        
        candidates.sort(key=lambda x: x[0], reverse=True)
        keypoints_list = [k for _, k in candidates[:max_persons]]
        
        return keypoints_list


def extract_skeleton_from_video(
    video_path: str,
    model_type: Optional[str] = None
) -> Tuple[List[np.ndarray], dict]:
    """
    Trích xuất skeleton từ video
    
    Args:
        video_path: Đường dẫn video
        model_type: "rtmpose"/"mmpose", "alphapose", hoặc "yolov8", None để dùng config
        
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

