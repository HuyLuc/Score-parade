"""
LocalPractisingController - Practising mode cho Local Mode (Làm chậm)
Hiển thị lỗi theo kiểu Stack, không trừ điểm
"""
import logging
from typing import Dict
from backend.app.controllers.local_controller import LocalController

logger = logging.getLogger(__name__)


class LocalPractisingController(LocalController):
    """
    Practising mode cho Local Mode (Làm chậm)
    - Hiển thị lỗi theo kiểu Stack (không trừ điểm)
    - Không dừng khi điểm thấp
    """
    
    def __init__(self, session_id: str, pose_service):
        """Initialize local practising controller"""
        super().__init__(session_id, pose_service)
    
    def _handle_error(self, person_id: int, error: Dict):
        """
        Handle error in practising mode
        - CHỈ hiển thị lỗi (Stack style)
        - KHÔNG trừ điểm
        - Không dừng
        """
        # Không trừ điểm trong chế độ luyện tập, chỉ lưu log vào DB
        self._save_error_to_db(person_id, error)

