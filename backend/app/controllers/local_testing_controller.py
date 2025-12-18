"""
LocalTestingController - Testing mode cho Local Mode (Làm chậm)
Trừ điểm và dừng khi điểm < 50
"""
import logging
from typing import Dict, Optional
from backend.app.controllers.local_controller import LocalController
from backend.app.config import SCORING_CONFIG

logger = logging.getLogger(__name__)


class LocalTestingController(LocalController):
    """
    Testing mode cho Local Mode (Làm chậm)
    - Trừ điểm khi phát hiện lỗi tư thế
    - Dừng khi điểm < 50 (trượt)
    """
    
    def __init__(self, session_id: str, pose_service):
        """Initialize local testing controller"""
        super().__init__(session_id, pose_service)
        self.stopped: Dict[int, bool] = {}
        # Ngưỡng trượt cho "Làm chậm" là 50 điểm
        self.fail_threshold = 50.0
    
    def _handle_error(self, person_id: int, error: Dict):
        """
        Handle error by deducting score.
        Stop if score falls below 50 (trượt).
        """
        if self.stopped.get(person_id, False):
            return
        
        # Ensure score exists
        if person_id not in self.scores:
            self.scores[person_id] = float(self.initial_score)

        # Trừ điểm
        deduction = error.get("deduction", 0)
        self.scores[person_id] -= deduction
        if self.scores[person_id] < 0:
            self.scores[person_id] = 0

        # Lưu lỗi vào database
        self._save_error_to_db(person_id, error)
        
        # Check if should stop (dưới 50 điểm = trượt)
        if self.scores[person_id] < self.fail_threshold:
            self.stopped[person_id] = True
            logger.warning(
                f"Làm chậm dừng cho person {person_id}: "
                f"điểm ({self.scores[person_id]:.2f}) < 50 (trượt)"
            )
    
    def process_frame(self, frame, timestamp: float, frame_number: int) -> Dict:
        """
        Process frame - skip if stopped for a given person
        """
        result = super().process_frame(frame, timestamp, frame_number)

        # Attach stopped flag per person
        for person in result.get("persons", []):
            pid = person.get("person_id")
            person["stopped"] = self.stopped.get(pid, False)
            if person["stopped"]:
                person["message"] = (
                    f"Đã trượt: điểm số ({self.scores.get(pid, 0):.2f}) "
                    f"dưới 50 điểm. Kết thúc kiểm tra."
                )
        return result
    
    def is_stopped(self, person_id: Optional[int] = None):
        """Check if testing has been stopped"""
        if person_id is None:
            return self.stopped
        return self.stopped.get(person_id, False)

