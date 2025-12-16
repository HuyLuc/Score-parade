"""
GlobalTestingController - Testing mode controller for Global Mode
Deducts score on errors and stops when score falls below threshold
"""
import logging
from typing import Dict
from backend.app.controllers.global_controller import GlobalController
from backend.app.config import SCORING_CONFIG

logger = logging.getLogger(__name__)


class GlobalTestingController(GlobalController):
    """
    Testing mode controller
    - Deducts score when errors are detected
    - Stops testing when score falls below fail threshold
    """
    
    def __init__(self, session_id: str, pose_service):
        """Initialize testing controller"""
        super().__init__(session_id, pose_service)
        self.stopped = False
        self.fail_threshold = SCORING_CONFIG.get("fail_threshold", SCORING_CONFIG["fail_threshold"])
    
    def _handle_error(self, error: Dict):
        """
        Handle error by deducting score.
        Stop if score falls below threshold.

        Không giới hạn điểm trừ theo từng loại lỗi (theo yêu cầu mới).
        """
        if self.stopped:
            return
        
        # Trừ điểm đúng theo deduction đã tính
        deduction = error.get("deduction", 0)
        self.score -= deduction
        if self.score < 0:
            self.score = 0
        
        # Check if should stop
        if self.score < self.fail_threshold:
            self.stopped = True
            logger.warning(f"Testing stopped: score ({self.score:.2f}) < threshold ({self.fail_threshold})")
    
    def process_frame(self, frame, timestamp: float, frame_number: int) -> Dict:
        """
        Process frame - skip if stopped
        
        Args:
            frame: Video frame
            timestamp: Frame timestamp
            frame_number: Frame number
            
        Returns:
            Processing results with stopped flag
        """
        if self.stopped:
            return {
                "success": False,
                "stopped": True,
                "timestamp": timestamp,
                "frame_number": frame_number,
                "errors": self.errors,
                "score": self.score,
                "message": f"Testing stopped: điểm số ({self.score:.2f}) dưới ngưỡng ({self.fail_threshold})"
            }
        
        result = super().process_frame(frame, timestamp, frame_number)
        result["stopped"] = self.stopped
        
        if self.stopped:
            result["message"] = f"Testing stopped: điểm số ({self.score:.2f}) dưới ngưỡng ({self.fail_threshold})"
        
        return result
    
    def is_stopped(self) -> bool:
        """Check if testing has been stopped"""
        return self.stopped
