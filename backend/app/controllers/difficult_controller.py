"""
DifficultController - Điều khiển mức độ khắt khe khi chấm
"""
from typing import Dict
from backend.app.config import SCORING_CONFIG


class DifficultController:
    """Controller cho mức độ khắt khe"""
    
    # Định nghĩa các hệ số điều chỉnh theo mức độ khắt khe
    DIFFICULTY_MULTIPLIERS = {
        "easy": 0.7,    # Giảm 30% điểm trừ
        "normal": 1.0,  # Bình thường
        "hard": 1.3,    # Tăng 30% điểm trừ
    }
    
    def __init__(self, difficulty: str = "normal"):
        self.difficulty = difficulty
        self.multiplier = self.DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)
    
    def get_adjusted_weight(self, base_weight: float) -> float:
        """
        Tính trọng số đã điều chỉnh theo mức độ khắt khe
        
        Args:
            base_weight: Trọng số gốc
            
        Returns:
            Trọng số đã điều chỉnh
        """
        return base_weight * self.multiplier
    
    def get_error_weights(self) -> Dict[str, float]:
        """
        Lấy error weights đã điều chỉnh
        
        Returns:
            Dict chứa error weights
        """
        base_weights = SCORING_CONFIG["error_weights"]
        return {
            error_type: self.get_adjusted_weight(weight)
            for error_type, weight in base_weights.items()
        }
    
    def calculate_deduction(self, error_type: str, error_value: float, base_weight: float = None) -> float:
        """
        Tính điểm trừ dựa trên mức độ khắt khe
        
        Args:
            error_type: Loại lỗi
            error_value: Giá trị lỗi
            base_weight: Trọng số gốc (nếu None, lấy từ config)
            
        Returns:
            Điểm trừ đã điều chỉnh
        """
        if base_weight is None:
            base_weights = SCORING_CONFIG["error_weights"]
            base_weight = base_weights.get(error_type, 1.0)
        
        adjusted_weight = self.get_adjusted_weight(base_weight)
        return error_value * adjusted_weight

