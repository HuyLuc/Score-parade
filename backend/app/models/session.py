"""
Session models - ScoringSession, Error
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from backend.app.database.base import Base


class SessionMode(enum.Enum):
    """Chế độ chấm"""
    TESTING = "testing"  # Kiểm tra (trừ điểm)
    PRACTISING = "practising"  # Luyện tập (chỉ hiển thị lỗi)


class SessionType(enum.Enum):
    """Loại phiên chấm"""
    LOCAL = "local"  # Làm chậm (chỉ tư thế)
    GLOBAL = "global"  # Tổng hợp (nhịp, khoảng cách, tốc độ)


class CriteriaType(enum.Enum):
    """Tiêu chí"""
    DI_DEU = "di_deu"  # Đi đều
    DI_NGHIEM = "di_nghiem"  # Đi nghiêm


class ScoringSession(Base):
    """Lớp đại diện cho phiên chấm điểm"""
    __tablename__ = "scoring_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Thông tin phiên chấm
    mode = Column(Enum(SessionMode), nullable=False)  # testing hoặc practising
    session_type = Column(Enum(SessionType), nullable=False)  # local hoặc global
    criteria_type = Column(Enum(CriteriaType), nullable=False)  # di_deu hoặc di_nghiem
    
    # Thời gian
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)  # Thời gian chấm (giây)
    
    # Foreign keys
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)  # Người chấm
    
    # Relationships
    candidate = relationship("Candidate", back_populates="scoring_sessions")
    person = relationship("Person", foreign_keys=[person_id])
    scores = relationship("Score", back_populates="session", cascade="all, delete-orphan")
    errors = relationship("Error", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ScoringSession(id={self.id}, candidate_id={self.candidate_id}, mode={self.mode.value})>"


class Error(Base):
    """Lớp đại diện cho lỗi"""
    __tablename__ = "errors"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Thông tin lỗi
    error_type = Column(String(100), nullable=False)  # arm_angle, leg_angle, rhythm, etc.
    description = Column(Text, nullable=True)  # Mô tả lỗi
    severity = Column(Float, nullable=False, default=1.0)  # Mức độ nghiêm trọng (1-10)
    deduction = Column(Float, nullable=True)  # Điểm trừ (nếu ở chế độ testing)
    
    # Thời gian xảy ra lỗi
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    frame_number = Column(Integer, nullable=True)  # Số frame trong video
    timestamp = Column(Float, nullable=True)  # Timestamp trong video (giây)
    
    # Media liên quan
    snapshot_path = Column(String(500), nullable=True)  # Đường dẫn ảnh (nếu local mode)
    video_path = Column(String(500), nullable=True)  # Đường dẫn video (nếu global mode)
    video_start_time = Column(Float, nullable=True)  # Thời điểm bắt đầu trong video (giây)
    video_end_time = Column(Float, nullable=True)  # Thời điểm kết thúc trong video (giây)
    
    # Foreign keys
    session_id = Column(Integer, ForeignKey("scoring_sessions.id"), nullable=False)
    criterion_id = Column(Integer, ForeignKey("criteria.id"), nullable=True)
    part_of_body_id = Column(Integer, ForeignKey("parts_of_body.id"), nullable=True)
    
    # Relationships
    session = relationship("ScoringSession", back_populates="errors")
    criterion = relationship("Criterion", back_populates="errors")
    part_of_body = relationship("PartOfBody", back_populates="error")
    
    def __repr__(self):
        return f"<Error(id={self.id}, error_type={self.error_type}, session_id={self.session_id})>"

