"""
Local Mode API endpoints - Làm chậm (chỉ kiểm tra tư thế)
"""
import logging
import cv2
import numpy as np
from typing import Dict, Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel

from backend.app.controllers.local_testing_controller import LocalTestingController
from backend.app.controllers.local_practising_controller import LocalPractisingController
from backend.app.services.pose_service import PoseService
from backend.app.services.database_service import DatabaseService
from backend.app.utils.exceptions import ValidationException, NotFoundException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/local", tags=["local"])

# In-memory storage for active sessions
_controllers: Dict[str, LocalTestingController | LocalPractisingController] = {}
_pose_service: Optional[PoseService] = None
_db_service = DatabaseService()


def get_pose_service() -> PoseService:
    """Get or create pose service singleton"""
    global _pose_service
    if _pose_service is None:
        try:
            _pose_service = PoseService()
        except Exception as e:
            logger.error(f"Failed to initialize PoseService: {e}")
            logger.warning("Using mock PoseService for testing")
            from unittest.mock import MagicMock
            _pose_service = MagicMock(spec=PoseService)
            _pose_service.predict.return_value = []
    return _pose_service


class StartLocalSessionRequest(BaseModel):
    """Request model for starting a local session"""
    mode: str  # "testing" or "practising"
    candidate_id: Optional[str] = None  # ID thí sinh được chấm


class ProcessFrameResponse(BaseModel):
    """Response model for frame processing"""
    success: bool
    timestamp: float
    frame_number: int
    persons: list
    stopped: Optional[Dict[int, bool]] = None


@router.post("/{session_id}/start")
async def start_local_session(
    session_id: str,
    mode: str = Form(...),
    candidate_id: Optional[str] = Form(None)
):
    """
    Start a local mode session (Làm chậm)
    
    Args:
        session_id: Unique session identifier
        mode: Mode type ("testing" or "practising")
        candidate_id: Optional candidate ID
        
    Returns:
        Session initialization result
    """
    # Validate mode
    if mode not in ["testing", "practising"]:
        raise ValidationException(
            detail=f"Chế độ không hợp lệ: {mode}. Chọn 'testing' hoặc 'practising'",
            field="mode"
        )
    
    # Check if session already exists
    if session_id in _controllers:
        raise ValidationException(
            detail=f"Session {session_id} đã tồn tại. Vui lòng xóa hoặc sử dụng session khác",
            field="session_id"
        )
    
    # Create appropriate controller
    pose_service = get_pose_service()
    
    if mode == "testing":
        controller = LocalTestingController(session_id, pose_service)
    else:
        controller = LocalPractisingController(session_id, pose_service)
    
    # Lưu session vào database
    _db_service.create_or_update_session(
        session_id=session_id,
        mode=f"local_{mode}",  # "local_testing" hoặc "local_practising"
        status="active",
        video_path=None,
        total_frames=0,
        candidate_id=candidate_id,
    )

    # Store controller
    _controllers[session_id] = controller
    
    return {
        "success": True,
        "session_id": session_id,
        "mode": mode,
        "candidate_id": candidate_id,
        "message": f"Session {session_id} đã được khởi tạo ở chế độ Làm chậm ({mode})"
    }


@router.post("/{session_id}/process-frame")
async def process_local_frame(
    session_id: str,
    frame_data: UploadFile = File(...),
    timestamp: float = Form(...),
    frame_number: int = Form(...)
):
    """
    Process a video frame (Local Mode - Làm chậm)
    
    Args:
        session_id: Session identifier
        frame_data: Frame image data
        timestamp: Frame timestamp in seconds
        frame_number: Frame number in sequence
        
    Returns:
        Processing results including errors and score
    """
    # Get controller
    if session_id not in _controllers:
        raise NotFoundException("Session", session_id)
    
    controller = _controllers[session_id]
    
    # Read frame data
    contents = await frame_data.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise ValidationException(
            detail="Không thể đọc dữ liệu frame",
            field="frame_data"
        )
    
    # Process frame
    result = controller.process_frame(frame, timestamp, frame_number)
    
    # Add stopped flag if testing mode
    if isinstance(controller, LocalTestingController):
        result["stopped"] = controller.is_stopped()
    
    return ProcessFrameResponse(**result)


@router.get("/{session_id}/score")
async def get_local_score(session_id: str):
    """
    Get current score for a local session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Current score per person
    """
    if session_id not in _controllers:
        scores = _db_service.get_scores_map(session_id)
        if not scores:
            raise NotFoundException("Session", session_id)
        return {"session_id": session_id, "scores": scores}
    
    controller = _controllers[session_id]
    scores = controller.get_score()
    
    stopped = None
    if isinstance(controller, LocalTestingController):
        stopped = controller.is_stopped()
    
    return {
        "session_id": session_id,
        "scores": scores,
        "stopped": stopped
    }


@router.get("/{session_id}/errors")
async def get_local_errors(session_id: str):
    """
    Get all errors for a local session
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of detected errors per person
    """
    if session_id not in _controllers:
        errors = _db_service.get_errors_map(session_id)
        if not errors:
            raise NotFoundException("Session", session_id)
        totals = {pid: len(errs) for pid, errs in errors.items()}
        return {"session_id": session_id, "errors": errors, "total_errors": totals}
    
    controller = _controllers[session_id]
    errors = controller.get_errors()
    totals = {pid: len(errs) for pid, errs in errors.items()}
    
    return {
        "session_id": session_id,
        "errors": errors,
        "total_errors": totals
    }


@router.post("/{session_id}/reset")
async def reset_local_session(session_id: str):
    """
    Reset a local session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Reset confirmation
    """
    if session_id not in _controllers:
        raise NotFoundException("Session", session_id)
    
    controller = _controllers[session_id]
    controller.reset()

    # Đặt lại trạng thái session trong DB
    _db_service.create_or_update_session(
        session_id=session_id,
        mode="local_testing" if isinstance(controller, LocalTestingController) else "local_practising",
        status="active",
        total_frames=0,
        video_path=None,
    )
    
    return {
        "success": True,
        "session_id": session_id,
        "message": f"Session {session_id} đã được reset"
    }


@router.delete("/{session_id}")
async def delete_local_session(session_id: str):
    """
    Delete a local session and free resources
    
    Args:
        session_id: Session identifier
        
    Returns:
        Deletion confirmation
    """
    if session_id in _controllers:
        del _controllers[session_id]
        logger.info(f"Local session {session_id} đã được xóa khỏi backend memory")

    # Xóa dữ liệu trong DB
    _db_service.delete_session_data(session_id)
    
    return {
        "success": True,
        "session_id": session_id,
        "message": f"Session {session_id} đã được xóa"
    }

