"""
Authentication Service - Xử lý đăng ký, đăng nhập, JWT tokens
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from backend.app.database.models import User
from backend.app.config import API_CONFIG
import os

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate user by username and password"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def create_user(
    db: Session,
    username: str,
    password: str,
    full_name: Optional[str] = None,
    age: Optional[int] = None,
    rank: Optional[str] = None,
    insignia: Optional[str] = None,
    gender: Optional[str] = None,
    avatar_path: Optional[str] = None
) -> User:
    """Create a new user"""
    # Check if username already exists
    if get_user_by_username(db, username):
        raise ValueError(f"Username '{username}' already exists")
    
    # Hash password
    password_hash = get_password_hash(password)
    
    # Create user
    user = User(
        username=username,
        password_hash=password_hash,
        full_name=full_name,
        age=age,
        rank=rank,
        insignia=insignia,
        gender=gender,
        avatar_path=avatar_path,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user_id: str, old_password: str, new_password: str) -> bool:
    """Change user password"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # Verify old password
    if not verify_password(old_password, user.password_hash):
        return False
    
    # Update password
    user.password_hash = get_password_hash(new_password)
    db.commit()
    return True

