"""
Database connection and session management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

from backend.app.config import DATABASE_CONFIG

logger = logging.getLogger(__name__)

# Get database URL from environment or config
DATABASE_URL = os.getenv("DATABASE_URL") or DATABASE_CONFIG.get("url")

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=DATABASE_CONFIG.get("echo", False),
    pool_size=DATABASE_CONFIG.get("pool_size", 5),
    max_overflow=DATABASE_CONFIG.get("max_overflow", 10),
    pool_pre_ping=True,  # Verify connections before using
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency for FastAPI to get database session
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session():
    """
    Context manager for database session
    Usage:
        with db_session() as db:
            item = Item(name="test")
            db.add(item)
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        raise


def check_db_connection():
    """
    Check if database connection is working
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

