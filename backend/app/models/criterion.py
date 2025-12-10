"""
Criterion model - Tiêu chí chấm điểm
"""
from sqlalchemy import Column, Integer, String, Float, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.database.base import Base


class Criterion(Base):
    """Lớp đại diện cho tiêu chí chấm điểm"""
    __tablename__ = "criteria"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)  # Nội dung tiêu chí
    weight = Column(Float, nullable=False, default=1.0)  # Trọng số (để tính điểm trừ)
    
    # Action là một lambda function được lưu dưới dạng JSON hoặc string
    # Trong thực tế, có thể lưu tên function hoặc code để eval
    action_name = Column(String(255), nullable=True)  # Tên function/action
    action_params = Column(JSON, nullable=True)  # Parameters cho action
    
    # Loại tiêu chí: posture (tư thế), rhythm (nhịp), distance (khoảng cách), speed (tốc độ)
    criterion_type = Column(String(50), nullable=False, default="posture")
    
    # Áp dụng cho: di_deu (đi đều) hoặc di_nghiem (đi nghiêm)
    applies_to = Column(String(50), nullable=True)  # di_deu, di_nghiem, hoặc cả hai
    
    # Relationships
    errors = relationship("Error", back_populates="criterion")
    
    def __repr__(self):
        return f"<Criterion(id={self.id}, content={self.content[:50]}..., weight={self.weight})>"

