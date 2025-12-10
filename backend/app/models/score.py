"""
Score model - Điểm số
"""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database.base import Base


class Score(Base):
    """Lớp đại diện cho điểm số"""
    __tablename__ = "scores"
    
    id = Column(Integer, primary_key=True, index=True)
    value = Column(Float, nullable=False, default=100.0)  # Giá trị điểm (0-100)
    initial_value = Column(Float, nullable=False, default=100.0)  # Điểm ban đầu
    final_value = Column(Float, nullable=True)  # Điểm cuối cùng
    
    # Danh sách các lần trừ điểm: [{"time": timestamp, "deduction": value, "reason": "..."}, ...]
    list_of_modified_times = Column(JSON, nullable=True, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign key đến ScoringSession
    session_id = Column(Integer, ForeignKey("scoring_sessions.id"), nullable=False)
    
    # Relationships
    session = relationship("ScoringSession", back_populates="scores")
    
    def __repr__(self):
        return f"<Score(id={self.id}, value={self.value}, session_id={self.session_id})>"
    
    def add_deduction(self, deduction: float, reason: str = ""):
        """Thêm một lần trừ điểm"""
        import datetime
        if self.list_of_modified_times is None:
            self.list_of_modified_times = []
        
        self.list_of_modified_times.append({
            "time": datetime.datetime.now().isoformat(),
            "deduction": deduction,
            "reason": reason
        })
        self.value = max(0, self.value - deduction)
    
    def is_passed(self, threshold: float = 50.0) -> bool:
        """Kiểm tra có đạt hay không (mặc định >= 50 điểm)"""
        return self.value >= threshold

