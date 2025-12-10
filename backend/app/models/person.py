"""
Person models - Person, Soldier, Officer
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from backend.app.database.base import Base


class Rank(enum.Enum):
    """Cấp bậc"""
    CHIEN_SI = "chiến_sĩ"
    HA_SI = "hạ_sĩ"
    TRUNG_SI = "trung_sĩ"
    THUONG_SI = "thượng_sĩ"
    THIEU_UY = "thiếu_úy"
    TRUNG_UY = "trung_úy"
    THUONG_UY = "thượng_úy"
    DAI_UY = "đại_úy"
    THIEU_TA = "thiếu_tá"
    TRUNG_TA = "trung_tá"
    THUONG_TA = "thượng_tá"
    DAI_TA = "đại_tá"


class Gender(enum.Enum):
    """Giới tính"""
    MALE = "male"
    FEMALE = "female"


class Person(Base):
    """Lớp đại diện cho người chung"""
    __tablename__ = "persons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # Hashed password
    token = Column(String(500), nullable=True)  # JWT token
    gender = Column(Enum(Gender), nullable=True)
    rank = Column(Enum(Rank), nullable=True)  # Cấp bậc
    insignia = Column(String(100), nullable=True)  # Quân hàm
    avatar = Column(String(500), nullable=True)  # Đường dẫn avatar
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    type = Column(String(50), nullable=False, default="person")
    
    # Relationships
    scoring_sessions = relationship("ScoringSession", back_populates="person")
    
    __mapper_args__ = {
        "polymorphic_identity": "person",
        "polymorphic_on": type,
    }
    
    def __repr__(self):
        return f"<Person(id={self.id}, username={self.username}, name={self.name})>"


class Soldier(Person):
    """Chiến sĩ - kế thừa từ Person"""
    __tablename__ = "soldiers"
    
    id = Column(Integer, ForeignKey("persons.id"), primary_key=True)
    unit = Column(String(255), nullable=True)  # Đơn vị
    
    __mapper_args__ = {
        "polymorphic_identity": "soldier",
    }
    
    def __repr__(self):
        return f"<Soldier(id={self.id}, unit={self.unit})>"


class Officer(Person):
    """Sĩ quan - kế thừa từ Person"""
    __tablename__ = "officers"
    
    id = Column(Integer, ForeignKey("persons.id"), primary_key=True)
    position = Column(String(255), nullable=True)  # Chức vụ (vd: đại đội trưởng)
    
    __mapper_args__ = {
        "polymorphic_identity": "officer",
    }
    
    def __repr__(self):
        return f"<Officer(id={self.id}, position={self.position})>"

