"""
Candidate model - Thí sinh
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from backend.app.database.base import Base


class CandidateStatus(enum.Enum):
    """Trạng thái thí sinh"""
    PENDING = "pending"  # Chưa chấm
    IN_PROGRESS = "in_progress"  # Đang chấm
    COMPLETED = "completed"  # Đã chấm xong
    FAILED = "failed"  # Trượt (< 50 điểm)


class Candidate(Base):
    """Lớp đại diện cho thí sinh"""
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=True, index=True)  # Mã thí sinh
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    unit = Column(String(255), nullable=True)  # Đơn vị
    notes = Column(String(500), nullable=True)  # Ghi chú
    
    status = Column(Enum(CandidateStatus), default=CandidateStatus.PENDING)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign key đến Person (người tạo/quản lý)
    created_by_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    
    # Relationships
    created_by = relationship("Person", foreign_keys=[created_by_id])
    scoring_sessions = relationship("ScoringSession", back_populates="candidate")
    
    def __repr__(self):
        return f"<Candidate(id={self.id}, name={self.name}, code={self.code}, status={self.status.value})>"

