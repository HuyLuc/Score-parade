"""
API routes cho barem điểm
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from backend.app.database.session import get_db
from backend.app.controllers.db_controller import DBController
from backend.app.controllers.barem_controller import BaremController
from backend.app.api.auth import get_current_user

router = APIRouter()


# Pydantic models
class CriterionResponse(BaseModel):
    id: int
    content: str
    weight: float
    criterion_type: str
    applies_to: Optional[str] = None
    
    class Config:
        from_attributes = True


class UpdateWeightRequest(BaseModel):
    criterion_id: int
    weight: float


class UpdateMultipleWeightsRequest(BaseModel):
    updates: List[UpdateWeightRequest]


@router.get("/", response_model=List[CriterionResponse])
async def get_all_criteria(
    criteria_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lấy tất cả criteria"""
    db_controller = DBController(db)
    barem_controller = BaremController(db_controller)
    
    criteria = barem_controller.get_all_criteria(criteria_type)
    
    return [
        CriterionResponse(
            id=c.id,
            content=c.content,
            weight=c.weight,
            criterion_type=c.criterion_type,
            applies_to=c.applies_to
        )
        for c in criteria
    ]


@router.get("/by-type/{criteria_type}", response_model=List[CriterionResponse])
async def get_criteria_by_type(
    criteria_type: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lấy criteria theo loại (posture, rhythm, distance, speed)"""
    db_controller = DBController(db)
    barem_controller = BaremController(db_controller)
    
    criteria = barem_controller.get_criteria_by_type(criteria_type)
    
    return [
        CriterionResponse(**c) for c in criteria
    ]


@router.put("/weight/{criterion_id}")
async def update_criterion_weight(
    criterion_id: int,
    weight: float,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cập nhật trọng số của một criterion"""
    db_controller = DBController(db)
    barem_controller = BaremController(db_controller)
    
    success, error = barem_controller.update_criterion_weight(criterion_id, weight)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"success": True, "message": "Cập nhật trọng số thành công"}


@router.put("/weights", response_model=dict)
async def update_multiple_weights(
    request: UpdateMultipleWeightsRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cập nhật nhiều trọng số cùng lúc"""
    db_controller = DBController(db)
    barem_controller = BaremController(db_controller)
    
    updates = [u.dict() for u in request.updates]
    success, errors = barem_controller.update_multiple_weights(updates)
    
    if not success:
        return {
            "success": False,
            "errors": errors,
            "message": f"Có {len(errors)} lỗi khi cập nhật"
        }
    
    return {
        "success": True,
        "message": f"Cập nhật thành công {len(updates)} trọng số"
    }

