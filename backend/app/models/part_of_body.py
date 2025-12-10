"""
PartOfBody models - PartOfBody và 10 lớp con
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.base import Base


class PartOfBody(Base):
    """Lớp đại diện cho bộ phận của cơ thể"""
    __tablename__ = "parts_of_body"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Tên bộ phận
    position_x = Column(Float, nullable=True)  # Vị trí X
    position_y = Column(Float, nullable=True)  # Vị trí Y
    position_z = Column(Float, nullable=True)  # Vị trí Z (nếu có)
    confidence = Column(Float, nullable=True)  # Độ tin cậy (0-1)
    
    # Foreign key đến Error (nếu có lỗi)
    error_id = Column(Integer, ForeignKey("errors.id"), nullable=True)
    
    # Relationships
    error = relationship("Error", back_populates="part_of_body")
    
    def __repr__(self):
        return f"<PartOfBody(id={self.id}, name={self.name})>"


class Nose(PartOfBody):
    """Mũi"""
    __tablename__ = "noses"
    
    id = Column(Integer, primary_key=True)
    part_of_body_id = Column(Integer, nullable=False)  # FK to parts_of_body.id


class Neck(PartOfBody):
    """Cổ"""
    __tablename__ = "necks"
    
    id = Column(Integer, primary_key=True)
    part_of_body_id = Column(Integer, nullable=False)


class Shoulder(PartOfBody):
    """Vai"""
    __tablename__ = "shoulders"
    
    id = Column(Integer, primary_key=True)
    part_of_body_id = Column(Integer, nullable=False)
    side = Column(String(10), nullable=True)  # left, right


class Arm(PartOfBody):
    """Tay"""
    __tablename__ = "arms"
    
    id = Column(Integer, primary_key=True)
    part_of_body_id = Column(Integer, nullable=False)
    side = Column(String(10), nullable=True)  # left, right


class Elbow(PartOfBody):
    """Khuỷu tay"""
    __tablename__ = "elbows"
    
    id = Column(Integer, primary_key=True)
    part_of_body_id = Column(Integer, nullable=False)
    side = Column(String(10), nullable=True)  # left, right


class Fist(PartOfBody):
    """Nắm tay"""
    __tablename__ = "fists"
    
    id = Column(Integer, primary_key=True)
    part_of_body_id = Column(Integer, nullable=False)
    side = Column(String(10), nullable=True)  # left, right


class Hand(PartOfBody):
    """Bàn tay"""
    __tablename__ = "hands"
    
    id = Column(Integer, primary_key=True)
    part_of_body_id = Column(Integer, nullable=False)
    side = Column(String(10), nullable=True)  # left, right


class Back(PartOfBody):
    """Lưng"""
    __tablename__ = "backs"
    
    id = Column(Integer, primary_key=True)
    part_of_body_id = Column(Integer, nullable=False)


class Knee(PartOfBody):
    """Đầu gối"""
    __tablename__ = "knees"
    
    id = Column(Integer, primary_key=True)
    part_of_body_id = Column(Integer, nullable=False)
    side = Column(String(10), nullable=True)  # left, right


class Foot(PartOfBody):
    """Bàn chân"""
    __tablename__ = "feet"
    
    id = Column(Integer, primary_key=True)
    part_of_body_id = Column(Integer, nullable=False)
    side = Column(String(10), nullable=True)  # left, right

