"""
GlobalTestingController - Testing mode controller for Global Mode
Deducts score on errors and stops when score falls below threshold
"""
import logging
from typing import Dict, Optional
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
        self.stopped: Dict[int, bool] = {}
        # Dùng ngưỡng cho chế độ testing, fallback về default nếu thiếu
        thresholds = SCORING_CONFIG.get("fail_thresholds", {})
        self.fail_threshold = thresholds.get("testing", thresholds.get("default", 50.0))
    
    def _handle_error(self, person_id: int, error: Dict):
        """
        Handle error by deducting score.
        Stop if score falls below threshold.

        Không giới hạn điểm trừ theo từng loại lỗi (theo yêu cầu mới).
        """
        if self.stopped.get(person_id, False):
            return
        
        # Ensure score exists
        if person_id not in self.scores:
            self.scores[person_id] = float(self.initial_score)

        # Trừ điểm đúng theo deduction đã tính
        deduction = error.get("deduction", 0)
        self.scores[person_id] -= deduction
        if self.scores[person_id] < 0:
            self.scores[person_id] = 0

        # Lưu lỗi vào database
        self._save_error_to_db(person_id, error)
        
        # Check if should stop
        if self.scores[person_id] < self.fail_threshold:
            self.stopped[person_id] = True
            logger.warning(
                f"Testing stopped for person {person_id}: "
                f"score ({self.scores[person_id]:.2f}) < threshold ({self.fail_threshold})"
            )
    
    def process_frame(self, frame, timestamp: float, frame_number: int) -> Dict:
        """
        Process frame - skip if stopped for a given person
        
        Args:
            frame: Video frame
            timestamp: Frame timestamp
            frame_number: Frame number
            
        Returns:
            Processing results with stopped flag per person
        """
        result = super().process_frame(frame, timestamp, frame_number)

        # Attach stopped flag per person
        for person in result.get("persons", []):
            pid = person.get("person_id")
            person["stopped"] = self.stopped.get(pid, False)
            if person["stopped"]:
                person["message"] = (
                    f"Testing stopped: điểm số ({self.scores.get(pid, 0):.2f}) "
                    f"dưới ngưỡng ({self.fail_threshold})"
                )
        return result
    
    def is_stopped(self, person_id: Optional[int] = None):
        """Check if testing has been stopped"""
        if person_id is None:
            return self.stopped
        return self.stopped.get(person_id, False)
