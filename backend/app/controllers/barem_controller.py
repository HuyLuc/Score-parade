"""
BaremController - Điều khiển việc quản lý barem điểm
"""
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.controllers.db_controller import DBController
from backend.app.models.criterion import Criterion


class BaremController:
    """Controller cho barem điểm"""
    
    def __init__(self, db_controller: DBController):
        self.db_controller = db_controller
    
    def get_all_criteria(self, criteria_type: str = None) -> List[Criterion]:
        """
        Lấy tất cả criteria
        
        Args:
            criteria_type: Loại tiêu chí (di_deu/di_nghiem) - None = tất cả
            
        Returns:
            List các Criterion
        """
        query = self.db_controller.db.query(Criterion)
        
        if criteria_type:
            query = query.filter(Criterion.applies_to == criteria_type)
        
        return query.order_by(Criterion.id).all()
    
    def get_criteria_by_type(self, criteria_type: str) -> List[Dict]:
        """
        Lấy criteria theo loại và format cho frontend
        
        Args:
            criteria_type: Loại tiêu chí (posture, rhythm, distance, speed)
            
        Returns:
            List các dict chứa thông tin criterion
        """
        criteria = self.db_controller.db.query(Criterion).filter(
            Criterion.criterion_type == criteria_type
        ).all()
        
        return [
            {
                "id": c.id,
                "content": c.content,
                "weight": c.weight,
                "criterion_type": c.criterion_type,
                "applies_to": c.applies_to,
            }
            for c in criteria
        ]
    
    def update_criterion_weight(self, criterion_id: int, weight: float) -> Tuple[bool, Optional[str]]:
        """
        Cập nhật trọng số của criterion
        
        Args:
            criterion_id: ID của criterion
            weight: Trọng số mới
            
        Returns:
            (success, error_message)
        """
        if weight < 0:
            return False, "Trọng số phải >= 0"
        
        criterion = self.db_controller.db.query(Criterion).filter(
            Criterion.id == criterion_id
        ).first()
        
        if not criterion:
            return False, "Không tìm thấy criterion"
        
        criterion.weight = weight
        self.db_controller.db.commit()
        
        return True, None
    
    def update_multiple_weights(self, updates: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Cập nhật nhiều trọng số cùng lúc
        
        Args:
            updates: List các dict {criterion_id: int, weight: float}
            
        Returns:
            (success, list_of_errors)
        """
        errors = []
        
        for update in updates:
            criterion_id = update.get("criterion_id")
            weight = update.get("weight")
            
            if criterion_id is None or weight is None:
                errors.append(f"Thiếu criterion_id hoặc weight")
                continue
            
            success, error = self.update_criterion_weight(criterion_id, weight)
            if not success:
                errors.append(f"Criterion {criterion_id}: {error}")
        
        return len(errors) == 0, errors

