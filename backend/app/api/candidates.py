"""
Candidates API endpoints - Quản lý danh sách thí sinh
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import pandas as pd
import io

from backend.app.database.connection import get_db
from backend.app.database.models import Candidate, User

# Auth dependency - import with fallback
try:
    from backend.app.api.auth import get_current_user
    _auth_available = True
except ImportError:
    _auth_available = False
    # Create a dummy dependency that returns None
    def get_current_user():
        def _dummy():
            return None
        return Depends(_dummy)

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


# Request/Response Models
class CandidateCreate(BaseModel):
    full_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    rank: Optional[str] = None
    insignia: Optional[str] = None
    avatar_path: Optional[str] = None
    notes: Optional[str] = None


class CandidateUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    rank: Optional[str] = None
    insignia: Optional[str] = None
    avatar_path: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CandidateResponse(BaseModel):
    id: str
    full_name: str
    age: Optional[int]
    gender: Optional[str]
    rank: Optional[str]
    insignia: Optional[str]
    avatar_path: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[CandidateResponse])
async def get_candidates(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user) if _auth_available else None
):
    """
    Lấy danh sách thí sinh
    
    Args:
        skip: Số bản ghi bỏ qua
        limit: Số bản ghi tối đa
        is_active: Lọc theo trạng thái active
        db: Database session
        current_user: User hiện tại
        
    Returns:
        Danh sách thí sinh
    """
    query = db.query(Candidate)
    
    if is_active is not None:
        query = query.filter(Candidate.is_active == is_active)
    
    candidates = query.offset(skip).limit(limit).all()
    
    return [
        CandidateResponse(
            id=str(c.id),
            full_name=c.full_name,
            age=c.age,
            gender=c.gender,
            rank=c.rank,
            insignia=c.insignia,
            avatar_path=c.avatar_path,
            notes=c.notes,
            is_active=c.is_active,
            created_at=c.created_at.isoformat() if c.created_at else "",
            updated_at=c.updated_at.isoformat() if c.updated_at else ""
        )
        for c in candidates
    ]


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user) if _auth_available else None
):
    """
    Lấy thông tin một thí sinh
    
    Args:
        candidate_id: ID thí sinh
        db: Database session
        current_user: User hiện tại
        
    Returns:
        Thông tin thí sinh
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thí sinh"
        )
    
    return CandidateResponse(
        id=str(candidate.id),
        full_name=candidate.full_name,
        age=candidate.age,
        gender=candidate.gender,
        rank=candidate.rank,
        insignia=candidate.insignia,
        avatar_path=candidate.avatar_path,
        notes=candidate.notes,
        is_active=candidate.is_active,
        created_at=candidate.created_at.isoformat() if candidate.created_at else "",
        updated_at=candidate.updated_at.isoformat() if candidate.updated_at else ""
    )


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user) if _auth_available else None
):
    """
    Tạo thí sinh mới
    
    Args:
        candidate: Thông tin thí sinh
        db: Database session
        current_user: User hiện tại
        
    Returns:
        Thông tin thí sinh đã tạo
    """
    new_candidate = Candidate(
        full_name=candidate.full_name,
        age=candidate.age,
        gender=candidate.gender,
        rank=candidate.rank,
        insignia=candidate.insignia,
        avatar_path=candidate.avatar_path,
        notes=candidate.notes,
        created_by=current_user.id if current_user else None,
        is_active=True
    )
    
    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)
    
    return CandidateResponse(
        id=str(new_candidate.id),
        full_name=new_candidate.full_name,
        age=new_candidate.age,
        gender=new_candidate.gender,
        rank=new_candidate.rank,
        insignia=new_candidate.insignia,
        avatar_path=new_candidate.avatar_path,
        notes=new_candidate.notes,
        is_active=new_candidate.is_active,
        created_at=new_candidate.created_at.isoformat() if new_candidate.created_at else "",
        updated_at=new_candidate.updated_at.isoformat() if new_candidate.updated_at else ""
    )


@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    candidate_update: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user) if _auth_available else None
):
    """
    Cập nhật thông tin thí sinh
    
    Args:
        candidate_id: ID thí sinh
        candidate_update: Thông tin cập nhật
        db: Database session
        current_user: User hiện tại
        
    Returns:
        Thông tin thí sinh đã cập nhật
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thí sinh"
        )
    
    # Update fields
    if candidate_update.full_name is not None:
        candidate.full_name = candidate_update.full_name
    if candidate_update.age is not None:
        candidate.age = candidate_update.age
    if candidate_update.gender is not None:
        candidate.gender = candidate_update.gender
    if candidate_update.rank is not None:
        candidate.rank = candidate_update.rank
    if candidate_update.insignia is not None:
        candidate.insignia = candidate_update.insignia
    if candidate_update.avatar_path is not None:
        candidate.avatar_path = candidate_update.avatar_path
    if candidate_update.notes is not None:
        candidate.notes = candidate_update.notes
    if candidate_update.is_active is not None:
        candidate.is_active = candidate_update.is_active
    
    db.commit()
    db.refresh(candidate)
    
    return CandidateResponse(
        id=str(candidate.id),
        full_name=candidate.full_name,
        age=candidate.age,
        gender=candidate.gender,
        rank=candidate.rank,
        insignia=candidate.insignia,
        avatar_path=candidate.avatar_path,
        notes=candidate.notes,
        is_active=candidate.is_active,
        created_at=candidate.created_at.isoformat() if candidate.created_at else "",
        updated_at=candidate.updated_at.isoformat() if candidate.updated_at else ""
    )


@router.delete("/{candidate_id}", status_code=status.HTTP_200_OK)
async def delete_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user) if _auth_available else None
):
    """
    Xóa thí sinh (soft delete - set is_active = False)
    
    Args:
        candidate_id: ID thí sinh
        db: Database session
        current_user: User hiện tại
        
    Returns:
        Thông báo thành công
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thí sinh"
        )
    
    # Soft delete
    candidate.is_active = False
    db.commit()
    
    return {"message": "Đã xóa thí sinh thành công"}


@router.post("/import-excel", status_code=status.HTTP_201_CREATED)
async def import_candidates_from_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user) if _auth_available else None
):
    """
    Import danh sách thí sinh từ file Excel
    
    File Excel cần có các cột:
    - full_name (bắt buộc)
    - age (tùy chọn)
    - gender (tùy chọn)
    - rank (tùy chọn)
    - insignia (tùy chọn)
    - notes (tùy chọn)
    
    Args:
        file: File Excel (.xlsx hoặc .xls)
        db: Database session
        current_user: User hiện tại
        
    Returns:
        Số lượng thí sinh đã import
    """
    try:
        # Read Excel file
        contents = await file.read()
        
        # Try to read as .xlsx first, then .xls
        try:
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        except:
            df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
        
        # Validate required columns
        if 'full_name' not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File Excel phải có cột 'full_name'"
            )
        
        # Import candidates
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                candidate = Candidate(
                    full_name=str(row['full_name']).strip(),
                    age=int(row['age']) if pd.notna(row.get('age')) else None,
                    gender=str(row['gender']).strip() if pd.notna(row.get('gender')) else None,
                    rank=str(row['rank']).strip() if pd.notna(row.get('rank')) else None,
                    insignia=str(row['insignia']).strip() if pd.notna(row.get('insignia')) else None,
                    notes=str(row['notes']).strip() if pd.notna(row.get('notes')) else None,
                    created_by=current_user.id if current_user else None,
                    is_active=True
                )
                db.add(candidate)
                imported_count += 1
            except Exception as e:
                errors.append(f"Dòng {index + 2}: {str(e)}")
        
        db.commit()
        
        return {
            "message": f"Đã import {imported_count} thí sinh thành công",
            "imported_count": imported_count,
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi khi đọc file Excel: {str(e)}"
        )

