"""
GlobalPractisingController - Practising mode controller for Global Mode
Shows errors without deducting score, and does not stop
"""
import logging
from typing import Dict
from backend.app.controllers.global_controller import GlobalController

logger = logging.getLogger(__name__)


class GlobalPractisingController(GlobalController):
    """
    Practising mode controller
    - Shows errors for learning purposes
    - Deducts score (like testing mode)
    - Does NOT stop when score is low (allows full practice)
    """
    
    def __init__(self, session_id: str, pose_service):
        """Initialize practising controller"""
        super().__init__(session_id, pose_service)
    
    def _handle_error(self, error: Dict):
        """
        Handle error in practising mode
        - CHỈ hiển thị lỗi cho người luyện tập
        - KHÔNG trừ điểm (score giữ nguyên)
        - Không dừng khi điểm thấp
        
        Args:
            error: Error dictionary with deduction value
        """
        # Không trừ điểm trong chế độ luyện tập
        return
