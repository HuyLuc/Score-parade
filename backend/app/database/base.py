"""
SQLAlchemy base và database setup
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import backend.app.config as config

# Tạo engine
engine = create_engine(
    config.DATABASE_CONFIG["url"],
    echo=config.DATABASE_CONFIG["echo"],
    pool_size=config.DATABASE_CONFIG["pool_size"],
    max_overflow=config.DATABASE_CONFIG["max_overflow"]
)

# Tạo session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho tất cả models
Base = declarative_base()

def init_db():
    """Khởi tạo database - tạo tất cả tables"""
    Base.metadata.create_all(bind=engine)

