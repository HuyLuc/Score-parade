"""
Media models - Audio, Video, Log
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from backend.app.database.base import Base


class AudioType(enum.Enum):
    """Loại audio"""
    COMMAND = "command"  # Lệnh (vd: "Nghiêm. Đi đều bước")
    DI_DEU_LOCAL_TESTING = "di_deu_local_testing"
    DI_DEU_LOCAL_PRACTISING = "di_deu_local_practising"
    DI_DEU_GLOBAL = "di_deu_global"
    DI_NGHIEM_LOCAL_TESTING = "di_nghiem_local_testing"
    DI_NGHIEM_LOCAL_PRACTISING = "di_nghiem_local_practising"
    DI_NGHIEM_GLOBAL = "di_nghiem_global"


class LogLevel(enum.Enum):
    """Mức độ log"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Audio(Base):
    """Lớp đại diện cho file audio"""
    __tablename__ = "audios"
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(500), nullable=False)  # Đường dẫn file
    audio_type = Column(Enum(AudioType), nullable=False)
    duration = Column(Float, nullable=True)  # Thời lượng (giây)
    file_size = Column(Integer, nullable=True)  # Kích thước file (bytes)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Audio(id={self.id}, audio_type={self.audio_type.value}, file_path={self.file_path})>"


class Video(Base):
    """Lớp đại diện cho file video"""
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String(500), nullable=False)  # Đường dẫn file
    duration = Column(Float, nullable=True)  # Thời lượng (giây)
    fps = Column(Float, nullable=True)  # FPS
    width = Column(Integer, nullable=True)  # Chiều rộng
    height = Column(Integer, nullable=True)  # Chiều cao
    file_size = Column(Integer, nullable=True)  # Kích thước file (bytes)
    
    # Loại video: input (video đầu vào), output (video kết quả), error (video lỗi)
    video_type = Column(String(50), nullable=False, default="input")
    
    # Foreign key đến Error (nếu là video lỗi)
    error_id = Column(Integer, ForeignKey("errors.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    error = relationship("Error", foreign_keys=[error_id])
    
    def __repr__(self):
        return f"<Video(id={self.id}, video_type={self.video_type}, file_path={self.file_path})>"


class Log(Base):
    """Lớp đại diện cho log"""
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(Enum(LogLevel), nullable=False)
    message = Column(Text, nullable=False)
    module = Column(String(255), nullable=True)  # Module/component tạo log
    details = Column(Text, nullable=True)  # Chi tiết bổ sung (JSON string)
    
    # Foreign key đến Person (nếu có)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    person = relationship("Person", foreign_keys=[person_id])
    
    def __repr__(self):
        return f"<Log(id={self.id}, level={self.level.value}, message={self.message[:50]}...)>"

