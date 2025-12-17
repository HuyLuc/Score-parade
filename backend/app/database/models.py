"""
SQLAlchemy models for Score Parade database
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, foreign
from sqlalchemy.sql import func
import uuid

from backend.app.database.connection import Base


class Session(Base):
    """Sessions table - Lưu thông tin các phiên chấm điểm"""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    mode = Column(String(20), nullable=False, default="testing")  # 'testing' or 'practising'
    status = Column(String(20), nullable=False, default="active")  # 'active', 'completed', 'cancelled'
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    total_frames = Column(Integer, default=0)
    video_path = Column(String(500), nullable=True)
    # URL tương đối để truy cập skeleton video qua API (vd: /api/videos/session_id/skeleton_video_web.mp4)
    skeleton_video_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    persons = relationship("Person", back_populates="session", cascade="all, delete-orphan")
    errors = relationship("Error", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', mode='{self.mode}', status='{self.status}')>"


class Person(Base):
    """Persons table - Lưu thông tin từng người trong session"""
    __tablename__ = "persons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(Integer, nullable=False)  # Track ID từ tracker
    score = Column(Float, default=100.00)
    total_errors = Column(Integer, default=0)
    status = Column(String(20), default="active")  # 'active', 'stopped', 'completed'
    first_frame = Column(Integer, nullable=True)
    last_frame = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    session = relationship("Session", back_populates="persons")
    # Optional convenience relationship: tất cả errors thuộc cùng session.
    # Dùng primaryjoin rõ ràng để SQLAlchemy không yêu cầu foreign key trực tiếp.
    errors = relationship(
        "Error",
        primaryjoin="Person.session_id == foreign(Error.session_id)",
        viewonly=True,
    )

    __table_args__ = (
        {"postgresql_partition_by": "RANGE (created_at)"} if False else {},  # Placeholder for future partitioning
    )

    def __repr__(self):
        return f"<Person(session_id={self.session_id}, person_id={self.person_id}, score={self.score})>"


class Error(Base):
    """Errors table - Lưu chi tiết các lỗi phát hiện được"""
    __tablename__ = "errors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    # Giữ person_id là INT để khớp schema hiện tại (persons.person_id), không khai báo quan hệ trực tiếp
    person_id = Column(Integer, nullable=False, index=True)
    error_type = Column(String(50), nullable=False, index=True)  # 'arm_angle', 'leg_angle', etc.
    severity = Column(Float, nullable=False)
    deduction = Column(Float, nullable=False)
    message = Column(Text, nullable=True)
    frame_number = Column(Integer, nullable=True, index=True)
    timestamp_sec = Column(Float, nullable=True)
    is_sequence = Column(Boolean, default=False)
    sequence_length = Column(Integer, nullable=True)
    start_frame = Column(Integer, nullable=True)
    end_frame = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="errors")

    def __repr__(self):
        return f"<Error(session_id={self.session_id}, person_id={self.person_id}, error_type='{self.error_type}', frame={self.frame_number})>"


class GoldenTemplate(Base):
    """Golden Templates table - Lưu thông tin các template chuẩn"""
    __tablename__ = "golden_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    video_path = Column(String(500), nullable=True)
    skeleton_path = Column(String(500), nullable=True)
    profile_path = Column(String(500), nullable=True)
    camera_angle = Column(String(50), default="front")
    total_frames = Column(Integer, nullable=True)
    fps = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<GoldenTemplate(name='{self.name}', camera_angle='{self.camera_angle}', is_active={self.is_active})>"


class Config(Base):
    """Configs table - Lưu cấu hình hệ thống"""
    __tablename__ = "configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Config(key='{self.key}')>"

