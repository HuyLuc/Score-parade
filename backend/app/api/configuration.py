"""
API routes cho configuration
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.app.database.session import get_db
from backend.app.controllers.db_controller import DBController
from backend.app.controllers.configuration_controller import ConfigurationController
from backend.app.api.auth import get_current_user

router = APIRouter()


# Pydantic models
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ConfigurationResponse(BaseModel):
    mode: str
    criteria: str
    difficulty: str
    operation_mode: str


class UpdateConfigurationRequest(BaseModel):
    mode: Optional[str] = None
    criteria: Optional[str] = None
    difficulty: Optional[str] = None
    operation_mode: Optional[str] = None


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Đổi mật khẩu"""
    db_controller = DBController(db)
    config_controller = ConfigurationController(db_controller)
    
    success, error = config_controller.change_password(
        person_id=current_user["id"],
        old_password=request.old_password,
        new_password=request.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"success": True, "message": "Đổi mật khẩu thành công"}


@router.get("/", response_model=ConfigurationResponse)
async def get_configuration(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lấy cấu hình hiện tại"""
    db_controller = DBController(db)
    config_controller = ConfigurationController(db_controller)
    
    config = config_controller.get_configuration(current_user["id"])
    return ConfigurationResponse(**config)


@router.put("/", response_model=ConfigurationResponse)
async def update_configuration(
    request: UpdateConfigurationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cập nhật cấu hình"""
    db_controller = DBController(db)
    config_controller = ConfigurationController(db_controller)
    
    success, error = config_controller.update_configuration(
        person_id=current_user["id"],
        mode=request.mode,
        criteria=request.criteria,
        difficulty=request.difficulty,
        operation_mode=request.operation_mode
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Lấy lại config đã cập nhật
    config = config_controller.get_configuration(current_user["id"])
    return ConfigurationResponse(**config)

