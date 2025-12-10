"""
Pose estimation service - Wrapper cho PoseEstimator
"""
from backend.app.services.pose_estimation import PoseEstimator


class PoseService:
    """Service cho pose estimation"""
    
    def __init__(self, model_type: str = None):
        self.estimator = PoseEstimator(model_type)
    
    def predict(self, frame):
        """Dự đoán pose từ frame"""
        return self.estimator.predict(frame)
    
    def predict_batch(self, frames):
        """Dự đoán pose từ nhiều frames"""
        return self.estimator.predict_batch(frames)

