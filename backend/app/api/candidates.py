"""
API routes cho candidate management
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from backend.app.database.session import get_db
from backend.app.controllers.db_controller import DBController
from backend.app.controllers.candidate_controller import CandidateController
from backend.app.api.auth import get_current_user

router = APIRouter()


# Pydantic models
class CandidateCreate(BaseModel):
    name: str
    code: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class CandidateResponse(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_at: str
    
    class Config:
        from_attributes = True


class ImportResponse(BaseModel):
    success: bool
    created_count: int
    errors: List[str]
    candidates: List[CandidateResponse]


@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Tạo candidate mới"""
    db_controller = DBController(db)
    candidate_controller = CandidateController(db_controller)
    
    candidate_obj, error = candidate_controller.create_candidate(
        candidate.dict(),
        created_by_id=current_user["id"]
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return CandidateResponse(
        id=candidate_obj.id,
        name=candidate_obj.name,
        code=candidate_obj.code,
        age=candidate_obj.age,
        gender=candidate_obj.gender,
        unit=candidate_obj.unit,
        notes=candidate_obj.notes,
        status=candidate_obj.status.value,
        created_at=candidate_obj.created_at.isoformat()
    )


@router.get("/", response_model=List[CandidateResponse])
async def get_all_candidates(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lấy tất cả candidates"""
    db_controller = DBController(db)
    candidate_controller = CandidateController(db_controller)
    
    candidates = candidate_controller.get_all_candidates(created_by_id=current_user["id"])
    
    return [
        CandidateResponse(
            id=c.id,
            name=c.name,
            code=c.code,
            age=c.age,
            gender=c.gender,
            unit=c.unit,
            notes=c.notes,
            status=c.status.value,
            created_at=c.created_at.isoformat()
        )
        for c in candidates
    ]


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lấy candidate theo ID"""
    db_controller = DBController(db)
    candidate_controller = CandidateController(db_controller)
    
    candidate = candidate_controller.get_candidate_by_id(candidate_id)
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy candidate"
        )
    
    return CandidateResponse(
        id=candidate.id,
        name=candidate.name,
        code=candidate.code,
        age=candidate.age,
        gender=candidate.gender,
        unit=candidate.unit,
        notes=candidate.notes,
        status=candidate.status.value,
        created_at=candidate.created_at.isoformat()
    )


@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: int,
    candidate_update: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Cập nhật candidate"""
    db_controller = DBController(db)
    candidate_controller = CandidateController(db_controller)
    
    # Chỉ lấy các trường không None
    update_data = {k: v for k, v in candidate_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không có dữ liệu để cập nhật"
        )
    
    # Xử lý status nếu có
    if "status" in update_data:
        from backend.app.models.candidate import CandidateStatus
        try:
            update_data["status"] = CandidateStatus(update_data["status"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status không hợp lệ"
            )
    
    success, error = candidate_controller.update_candidate(candidate_id, update_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Lỗi cập nhật candidate"
        )
    
    candidate = candidate_controller.get_candidate_by_id(candidate_id)
    return CandidateResponse(
        id=candidate.id,
        name=candidate.name,
        code=candidate.code,
        age=candidate.age,
        gender=candidate.gender,
        unit=candidate.unit,
        notes=candidate.notes,
        status=candidate.status.value,
        created_at=candidate.created_at.isoformat()
    )


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Xóa candidate"""
    db_controller = DBController(db)
    candidate_controller = CandidateController(db_controller)
    
    success, error = candidate_controller.delete_candidate(candidate_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Lỗi xóa candidate"
        )


@router.post("/import", response_model=ImportResponse)
async def import_candidates(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Import candidates từ file Excel"""
    # Kiểm tra file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File phải là Excel (.xlsx hoặc .xls)"
        )
    
    # Đọc file content
    file_content = await file.read()
    
    db_controller = DBController(db)
    candidate_controller = CandidateController(db_controller)
    
    created_candidates, errors = candidate_controller.import_from_excel(
        file_content,
        created_by_id=current_user["id"]
    )
    
    return ImportResponse(
        success=len(errors) == 0,
        created_count=len(created_candidates),
        errors=errors,
        candidates=[
            CandidateResponse(
                id=c.id,
                name=c.name,
                code=c.code,
                age=c.age,
                gender=c.gender,
                unit=c.unit,
                notes=c.notes,
                status=c.status.value,
                created_at=c.created_at.isoformat()
            )
            for c in created_candidates
        ]
    )


@router.post("/{candidate_id}/select", response_model=CandidateResponse)
async def select_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Chọn candidate (để chấm)"""
    db_controller = DBController(db)
    candidate_controller = CandidateController(db_controller)
    
    candidate, error = candidate_controller.select_candidate(candidate_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return CandidateResponse(
        id=candidate.id,
        name=candidate.name,
        code=candidate.code,
        age=candidate.age,
        gender=candidate.gender,
        unit=candidate.unit,
        notes=candidate.notes,
        status=candidate.status.value,
        created_at=candidate.created_at.isoformat()
    )

