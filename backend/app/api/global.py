"""
API routes cho Global Mode (Tổng hợp)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
import cv2
from backend.app.database.session import get_db
from backend.app.controllers.camera_controller import CameraController
from backend.app.controllers.video_controller import VideoController
from backend.app.controllers.global_controller import GlobalTestingController, GlobalPractisingController
from backend.app.controllers.ai_controller import AIController
from backend.app.services.pose_service import PoseService
from backend.app.services.scoring_service import ScoringService
from backend.app.models.session import ScoringSession, SessionMode, SessionType
from backend.app.api.auth import get_current_user
from backend.app.api.camera import get_camera_controller
from backend.app.api.local import get_pose_service, get_scoring_service

router = APIRouter()


# Pydantic models
class ProcessFrameRequest(BaseModel):
    camera_id: int
    session_id: int
    timestamp: float  # Timestamp của frame (giây)


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
    video_path: Optional[str] = None
    video_start_time: Optional[float] = None
    video_end_time: Optional[float] = None


def get_video_controller() -> VideoController:
    """Get video controller instance"""
    from backend.app.controllers.video_controller import VideoController
    return VideoController(get_camera_controller())


@router.post("/process-frame", response_model=ProcessFrameResponse)
async def process_frame(
    request: ProcessFrameRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Xử lý một frame để phát hiện lỗi tổng hợp"""
    # Lấy scoring session
    scoring_session = db.query(ScoringSession).filter(
        ScoringSession.id == request.session_id
    ).first()
    
    if not scoring_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy scoring session"
        )
    
    # Kiểm tra session type phải là GLOBAL
    if scoring_session.session_type != SessionType.GLOBAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session không phải Global Mode"
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
    video_controller = get_video_controller()
    pose_service = get_pose_service()
    scoring_service = get_scoring_service()
    ai_controller = AIController(pose_service)
    ai_controller.load_golden_template()
    
    if scoring_session.mode == SessionMode.TESTING:
        controller = GlobalTestingController(
            db,
            scoring_session,
            camera_controller,
            video_controller,
            pose_service,
            scoring_service,
            ai_controller
        )
    else:  # PRACTISING
        controller = GlobalPractisingController(
            db,
            scoring_session,
            camera_controller,
            video_controller,
            pose_service,
            scoring_service,
            ai_controller
        )
    
    # Xử lý frame
    result = controller.process_frame(
        request.camera_id,
        frame,
        request.timestamp
    )
    
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
    
    video_controller = get_video_controller()
    pose_service = get_pose_service()
    scoring_service = get_scoring_service()
    camera_controller = get_camera_controller()
    ai_controller = AIController(pose_service)
    ai_controller.load_golden_template()
    
    controller = GlobalPractisingController(
        db,
        scoring_session,
        camera_controller,
        video_controller,
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

