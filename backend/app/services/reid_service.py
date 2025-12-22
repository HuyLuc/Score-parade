"""
ReID Service
------------
- Cố gắng dùng torchreid (OSNet) nếu có sẵn.
- Nếu không có torchreid, fallback sang embedding dựa trên pose (keypoints) để giảm ID switch.
"""

import logging
from typing import Optional, Dict
import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torchreid  # type: ignore
    _TORCHREID_AVAILABLE = True
except Exception:
    _TORCHREID_AVAILABLE = False
    torch = None  # type: ignore
    torchreid = None  # type: ignore
    logger.warning("torchreid not available. Using pose-based embedding fallback.")


class ReIDService:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.similarity_threshold = float(self.config.get("similarity_threshold", 0.7))
        self.alpha = float(self.config.get("alpha", 0.5))  # weight for IoU vs appearance

        self.use_torchreid = False
        self.model = None
        self._init_torchreid()

    def _init_torchreid(self):
        if not self.enabled:
            return
        if not _TORCHREID_AVAILABLE:
            return
        try:
            # Dùng OSNet nhẹ, pretrained trên Market1501
            self.model = torchreid.models.build_model(
                name="osnet_x0_25",
                num_classes=1,
                pretrained=True,
            )
            self.model.eval()
            self.use_torchreid = True
            logger.info("ReIDService: Initialized OSNet (torchreid).")
        except Exception as e:
            logger.warning(f"ReIDService: Failed to init torchreid OSNet, fallback to pose embedding. Error: {e}")
            self.use_torchreid = False

    def _preprocess_crop(self, crop: np.ndarray):
        if crop is None or crop.size == 0 or torch is None:
            return None
        try:
            import cv2  # only used if available

            img = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (256, 128))
            img = img.astype(np.float32) / 255.0
            # Normalize
            img = (img - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
            img = img.transpose(2, 0, 1)  # C,H,W
            tensor = torch.from_numpy(img).unsqueeze(0)
            return tensor
        except Exception:
            return None

    def get_embedding(
        self,
        frame: Optional[np.ndarray],
        bbox: Optional[np.ndarray],
        keypoints: Optional[np.ndarray] = None,
    ) -> Optional[np.ndarray]:
        """
        Trả về embedding vector (np.ndarray) hoặc None.
        - Ưu tiên torchreid (OSNet) nếu có.
        - Fallback: pose-based embedding (flatten keypoints normalized).
        """
        if not self.enabled:
            return None

        # Torchreid branch
        if self.use_torchreid and frame is not None and bbox is not None:
            x1, y1, x2, y2 = bbox.astype(int)
            x1 = max(x1, 0)
            y1 = max(y1, 0)
            x2 = min(x2, frame.shape[1] - 1)
            y2 = min(y2, frame.shape[0] - 1)
            crop = frame[y1:y2, x1:x2]
            tensor = self._preprocess_crop(crop)
            if tensor is not None:
                with torch.no_grad():
                    feat = self.model(tensor)
                    emb = feat.detach().cpu().numpy().flatten()
                    # Normalize
                    norm = np.linalg.norm(emb) + 1e-6
                    emb = emb / norm
                    return emb

        # Pose-based fallback
        if keypoints is not None and keypoints.shape[0] >= 17:
            # Lấy x,y, normalize theo torso length
            kp = keypoints.copy()
            torso_len = self._torso_length(kp)
            if torso_len <= 1e-3:
                torso_len = 1.0
            xy = kp[:, :2] / torso_len
            emb = xy.flatten()
            norm = np.linalg.norm(emb) + 1e-6
            emb = emb / norm
            return emb

        return None

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        if a is None or b is None:
            return 0.0
        denom = (np.linalg.norm(a) * np.linalg.norm(b) + 1e-6)
        return float(np.dot(a, b) / denom)

    @staticmethod
    def _torso_length(kp: np.ndarray) -> float:
        # dùng vai-trái, vai-phải, hông-trái, hông-phải
        ls, rs, lh, rh = 5, 6, 11, 12
        pts = []
        for i in [ls, rs, lh, rh]:
            if kp[i, 2] > 0:
                pts.append(kp[i, :2])
        if len(pts) < 2:
            return 1.0
        pts = np.array(pts)
        return float(np.max(pts[:, 1]) - np.min(pts[:, 1]) + 1e-6)

