"""
Scoring service - Xử lý logic chấm điểm
"""
import numpy as np
from typing import Dict, List
from backend.app.config import SCORING_CONFIG


class ScoringService:
    """Service cho scoring"""
    
    def __init__(self):
        self.initial_score = SCORING_CONFIG["initial_score"]
        self.fail_threshold = SCORING_CONFIG["fail_threshold"]
        self.error_weights = SCORING_CONFIG["error_weights"]
    
    def calculate_score(self, errors: Dict) -> float:
        """
        Tính điểm dựa trên các lỗi
        
        Args:
            errors: Dict chứa các lỗi và mức độ nghiêm trọng
            
        Returns:
            Điểm số (0-100)
        """
        score = self.initial_score
        
        for error_type, error_value in errors.items():
            if error_type in self.error_weights:
                # Trừ điểm dựa trên mức độ lỗi
                deduction = error_value * self.error_weights[error_type]
                score -= deduction
        
        return max(0, min(100, score))
    
    def is_passed(self, score: float) -> bool:
        """Kiểm tra có đạt hay không"""
        return score >= self.fail_threshold

