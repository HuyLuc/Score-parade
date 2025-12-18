"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.database.connection import get_db
from backend.app.services.auth_service import (
    authenticate_user,
    create_user,
    create_access_token,
    verify_token,
    get_user_by_username,
    change_password
)
from backend.app.database.models import User

router = APIRouter(prefix="/api/auth", tags=["authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# Request/Response Models
class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    age: Optional[int] = None
    rank: Optional[str] = None
    insignia: Optional[str] = None
    gender: Optional[str] = None
    avatar_path: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    username: str
    full_name: Optional[str]
    age: Optional[int]
    rank: Optional[str]
    insignia: Optional[str]
    gender: Optional[str]
    avatar_path: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# Dependencies
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    
    return user


# Endpoints
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Đăng ký tài khoản mới
    
    Args:
        request: Thông tin đăng ký (username, password, full_name, age, rank, insignia, gender)
        db: Database session
        
    Returns:
        Thông tin user đã tạo
    """
    try:
        user = create_user(
            db=db,
            username=request.username,
            password=request.password,
            full_name=request.full_name,
            age=request.age,
            rank=request.rank,
            insignia=request.insignia,
            gender=request.gender,
            avatar_path=request.avatar_path
        )
        return UserResponse(
            id=str(user.id),
            username=user.username,
            full_name=user.full_name,
            age=user.age,
            rank=user.rank,
            insignia=user.insignia,
            gender=user.gender,
            avatar_path=user.avatar_path,
            is_active=user.is_active
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo tài khoản: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Đăng nhập và nhận JWT token
    
    Args:
        form_data: OAuth2 form với username và password
        db: Database session
        
    Returns:
        Access token và thông tin user
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
            "rank": user.rank,
            "insignia": user.insignia
        }
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Lấy thông tin user hiện tại
    
    Args:
        current_user: User đã authenticated (từ dependency)
        
    Returns:
        Thông tin user
    """
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        full_name=current_user.full_name,
        age=current_user.age,
        rank=current_user.rank,
        insignia=current_user.insignia,
        gender=current_user.gender,
        avatar_path=current_user.avatar_path,
        is_active=current_user.is_active
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_user_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Đổi mật khẩu
    
    Args:
        request: old_password và new_password
        current_user: User hiện tại
        db: Database session
        
    Returns:
        Thông báo thành công
    """
    success = change_password(
        db=db,
        user_id=str(current_user.id),
        old_password=request.old_password,
        new_password=request.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu cũ không đúng"
        )
    
    return {"message": "Đổi mật khẩu thành công"}

