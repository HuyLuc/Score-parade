"""
API routes cho authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.app.database.session import get_db
from backend.app.controllers.db_controller import DBController
from backend.app.controllers.register_controller import RegisterController
from backend.app.controllers.login_controller import LoginController
from backend.app.utils.auth import decode_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


# Pydantic models
class RegisterRequest(BaseModel):
    name: str
    username: str
    password: str
    age: Optional[int] = None
    gender: Optional[str] = None
    rank: Optional[str] = None
    insignia: Optional[str] = None
    avatar: Optional[str] = None


class RegisterResponse(BaseModel):
    success: bool
    message: str
    person_id: Optional[int] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    person_id: int
    username: str
    name: str


class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    gender: Optional[str] = None
    rank: Optional[str] = None
    insignia: Optional[str] = None


# Helper function để get current user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> dict:
    """Lấy current user từ token"""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = payload.get("sub")
    db_controller = DBController(db)
    person = db_controller.get_person_by_username(username)
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User không tồn tại",
        )
    
    return {
        "id": person.id,
        "username": person.username,
        "name": person.name,
        "gender": person.gender.value if person.gender else None,
        "rank": person.rank.value if person.rank else None,
        "insignia": person.insignia
    }


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Đăng ký user mới"""
    db_controller = DBController(db)
    register_controller = RegisterController(db_controller)
    
    person, error = register_controller.register(request.dict())
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return RegisterResponse(
        success=True,
        message="Đăng ký thành công",
        person_id=person.id
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Đăng nhập"""
    db_controller = DBController(db)
    login_controller = LoginController(db_controller)
    
    user_data, error = login_controller.login({
        "username": form_data.username,
        "password": form_data.password
    })
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    person = user_data["person"]
    return LoginResponse(
        access_token=user_data["token"],
        token_type="bearer",
        person_id=person.id,
        username=person.username,
        name=person.name
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """Lấy thông tin user hiện tại"""
    return UserResponse(**current_user)

