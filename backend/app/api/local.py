"""
API routes cho Local Mode (Làm chậm)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
import cv2
from backend.app.database.session import get_db
from backend.app.controllers.camera_controller import CameraController
from backend.app.controllers.snapshot_controller import SnapshotController
from backend.app.controllers.local_controller import LocalTestingController, LocalPractisingController
from backend.app.controllers.ai_controller import AIController
from backend.app.services.pose_service import PoseService
from backend.app.services.scoring_service import ScoringService
from backend.app.models.session import ScoringSession, SessionMode, SessionType, CriteriaType
from backend.app.api.auth import get_current_user
from backend.app.api.camera import get_camera_controller, get_snapshot_controller

router = APIRouter()

# Global instances (có thể cải thiện bằng dependency injection)
_pose_service: Optional[PoseService] = None
_scoring_service: Optional[ScoringService] = None


def get_pose_service() -> PoseService:
    """Get pose service instance"""
    global _pose_service
    if _pose_service is None:
        _pose_service = PoseService()
    return _pose_service


def get_scoring_service() -> ScoringService:
    """Get scoring service instance"""
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = ScoringService()
    return _scoring_service


# Pydantic models
class ProcessFrameRequest(BaseModel):
    camera_id: int
    session_id: int


class ProcessFrameResponse(BaseModel):
    errors: List[dict]
    score_deduction: float
    new_score: float
    is_failed: bool


class ErrorNotification(BaseModel):
    id: int
    type: str
    description: str
    timestamp: str
    snapshot_path: Optional[str] = None


@router.post("/process-frame", response_model=ProcessFrameResponse)
async def process_frame(
    request: ProcessFrameRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Xử lý một frame để phát hiện lỗi tư thế"""
    # Lấy scoring session
    scoring_session = db.query(ScoringSession).filter(
        ScoringSession.id == request.session_id
    ).first()
    
    if not scoring_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy scoring session"
        )
    
    # Kiểm tra session type phải là LOCAL
    if scoring_session.session_type != SessionType.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session không phải Local Mode"
        )
    
    # Lấy frame từ camera
    camera_controller = get_camera_controller()
    frame_data = camera_controller.get_frame(request.camera_id)
    
    if not frame_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể lấy frame từ camera {request.camera_id}"
        )
    
    frame_bytes, width, height = frame_data
    
    # Decode frame
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Tạo controller phù hợp
    snapshot_controller = get_snapshot_controller()
    pose_service = get_pose_service()
    scoring_service = get_scoring_service()
    ai_controller = AIController(pose_service)
    ai_controller.load_golden_template()
    
    if scoring_session.mode == SessionMode.TESTING:
        controller = LocalTestingController(
            db,
            scoring_session,
            camera_controller,
            snapshot_controller,
            pose_service,
            scoring_service,
            ai_controller
        )
    else:  # PRACTISING
        controller = LocalPractisingController(
            db,
            scoring_session,
            camera_controller,
            snapshot_controller,
            pose_service,
            scoring_service,
            ai_controller
        )
    
    # Xử lý frame
    result = controller.process_frame(request.camera_id, frame)
    
    return ProcessFrameResponse(**result)


@router.get("/{session_id}/notifications", response_model=List[ErrorNotification])
async def get_error_notifications(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lấy danh sách lỗi để hiển thị (cho Practising mode)"""
    scoring_session = db.query(ScoringSession).filter(
        ScoringSession.id == session_id
    ).first()
    
    if not scoring_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy scoring session"
        )
    
    if scoring_session.mode != SessionMode.PRACTISING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ áp dụng cho Practising mode"
        )
    
    snapshot_controller = get_snapshot_controller()
    pose_service = get_pose_service()
    scoring_service = get_scoring_service()
    camera_controller = get_camera_controller()
    ai_controller = AIController(pose_service)
    ai_controller.load_golden_template()
    
    controller = LocalPractisingController(
        db,
        scoring_session,
        camera_controller,
        snapshot_controller,
        pose_service,
        scoring_service,
        ai_controller
    )
    
    notifications = controller.get_error_notifications()
    
    return [
        ErrorNotification(**notif)
        for notif in notifications
    ]


@router.get("/{session_id}/score")
async def get_current_score(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lấy điểm hiện tại của session"""
    from backend.app.models.score import Score
    
    score = db.query(Score).filter(
        Score.session_id == session_id
    ).first()
    
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy score"
        )
    
    return {
        "value": score.value,
        "initial_value": score.initial_value,
        "is_passed": score.is_passed(),
        "deductions": score.list_of_modified_times or []
    }

