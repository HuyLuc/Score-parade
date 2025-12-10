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
    type = Column(String(50), nullable=False, default="part")
    
    # Relationships
    errors = relationship(
        "Error",
        back_populates="part_of_body",
        cascade="all, delete-orphan",
        foreign_keys="Error.part_of_body_id",
    )
    
    __mapper_args__ = {
        "polymorphic_identity": "part",
        "polymorphic_on": type,
    }
    
    def __repr__(self):
        return f"<PartOfBody(id={self.id}, name={self.name})>"


class Nose(PartOfBody):
    """Mũi"""
    __tablename__ = "noses"
    
    id = Column(Integer, ForeignKey("parts_of_body.id"), primary_key=True)
    
    __mapper_args__ = {
        "polymorphic_identity": "nose",
    }


class Neck(PartOfBody):
    """Cổ"""
    __tablename__ = "necks"
    
    id = Column(Integer, ForeignKey("parts_of_body.id"), primary_key=True)
    
    __mapper_args__ = {
        "polymorphic_identity": "neck",
    }


class Shoulder(PartOfBody):
    """Vai"""
    __tablename__ = "shoulders"
    
    id = Column(Integer, ForeignKey("parts_of_body.id"), primary_key=True)
    side = Column(String(10), nullable=True)  # left, right
    
    __mapper_args__ = {
        "polymorphic_identity": "shoulder",
    }


class Arm(PartOfBody):
    """Tay"""
    __tablename__ = "arms"
    
    id = Column(Integer, ForeignKey("parts_of_body.id"), primary_key=True)
    side = Column(String(10), nullable=True)  # left, right
    
    __mapper_args__ = {
        "polymorphic_identity": "arm",
    }


class Elbow(PartOfBody):
    """Khuỷu tay"""
    __tablename__ = "elbows"
    
    id = Column(Integer, ForeignKey("parts_of_body.id"), primary_key=True)
    side = Column(String(10), nullable=True)  # left, right
    
    __mapper_args__ = {
        "polymorphic_identity": "elbow",
    }


class Fist(PartOfBody):
    """Nắm tay"""
    __tablename__ = "fists"
    
    id = Column(Integer, ForeignKey("parts_of_body.id"), primary_key=True)
    side = Column(String(10), nullable=True)  # left, right
    
    __mapper_args__ = {
        "polymorphic_identity": "fist",
    }


class Hand(PartOfBody):
    """Bàn tay"""
    __tablename__ = "hands"
    
    id = Column(Integer, ForeignKey("parts_of_body.id"), primary_key=True)
    side = Column(String(10), nullable=True)  # left, right
    
    __mapper_args__ = {
        "polymorphic_identity": "hand",
    }


class Back(PartOfBody):
    """Lưng"""
    __tablename__ = "backs"
    
    id = Column(Integer, ForeignKey("parts_of_body.id"), primary_key=True)
    
    __mapper_args__ = {
        "polymorphic_identity": "back",
    }


class Knee(PartOfBody):
    """Đầu gối"""
    __tablename__ = "knees"
    
    id = Column(Integer, ForeignKey("parts_of_body.id"), primary_key=True)
    side = Column(String(10), nullable=True)  # left, right
    
    __mapper_args__ = {
        "polymorphic_identity": "knee",
    }


class Foot(PartOfBody):
    """Bàn chân"""
    __tablename__ = "feet"
    
    id = Column(Integer, ForeignKey("parts_of_body.id"), primary_key=True)
    side = Column(String(10), nullable=True)  # left, right
    
    __mapper_args__ = {
        "polymorphic_identity": "foot",
    }

