"""
Database session management
"""
from backend.app.database.base import SessionLocal

def get_db():
    """
    Dependency để lấy database session
    
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

