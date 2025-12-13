"""
GlobalPractisingController - Practising mode controller for Global Mode
Shows errors and deducts score, but does not stop
"""
import logging
from typing import Dict
from backend.app.controllers.global_controller import GlobalController
from backend.app.config import ERROR_GROUPING_CONFIG

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
        Handle error by deducting score
        Unlike testing mode, does NOT stop when score is low
        
        Args:
            error: Error dictionary with deduction value
        """
        # Deduct score
        # Nếu là sequence error, chỉ trừ một lần (deduction đã được tính cho toàn sequence)
        # Nếu là frame error đơn lẻ, trừ điểm như bình thường
        deduction = error.get("deduction", 0)
        
        # Giới hạn deduction tối đa cho mỗi loại lỗi (tránh trừ quá nhiều)
        error_type = error.get("type", "unknown")
        max_deduction = ERROR_GROUPING_CONFIG.get("max_deduction_per_error_type", 10.0)
        
        # Đếm tổng deduction đã trừ cho loại lỗi này
        total_deduction_for_type = sum(
            e.get("deduction", 0) for e in self.errors 
            if e.get("type") == error_type
        )
        
        # Chỉ trừ nếu chưa vượt quá max
        if total_deduction_for_type < max_deduction:
            remaining_quota = max_deduction - total_deduction_for_type
            actual_deduction = min(deduction, remaining_quota)
            self.score -= actual_deduction
            
            # Đảm bảo điểm không âm
            if self.score < 0:
                self.score = 0
            
            # Cập nhật deduction thực tế trong error
            error["deduction"] = actual_deduction
            if actual_deduction < deduction:
                error["deduction_original"] = deduction
                error["deduction_capped"] = True
        
        # Note: Practising mode does NOT stop, even if score is low
        # This allows users to see their full performance
