"""
API routes cho EndOfSection và Summary
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.database.session import get_db
from backend.app.controllers.end_of_section_controller import EndOfSectionController
from backend.app.controllers.summary_controller import SummaryController
from backend.app.api.auth import get_current_user

router = APIRouter()


@router.get("/session/{session_id}")
async def get_session_result(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lấy kết quả cho một session"""
    controller = EndOfSectionController(db)
    result = controller.get_session_result(session_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy session")
    return result


@router.get("/sessions")
async def list_sessions(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Liệt kê các phiên chấm gần đây"""
    controller = EndOfSectionController(db)
    return controller.list_sessions(limit=limit)


@router.get("/summary")
async def get_summary(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Tổng hợp kết quả (Summary)"""
    controller = SummaryController(db)
    return controller.list_results(limit=limit)


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Xoá session"""
    controller = SummaryController(db)
    ok = controller.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy session")
    return {"success": True}

