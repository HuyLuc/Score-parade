"""
Global Mode API endpoints
Handles global practising and testing modes with beat detection
"""
import logging
import cv2
import numpy as np
from typing import Dict, Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel

from backend.app.controllers.global_controller import GlobalController
from backend.app.controllers.global_testing_controller import GlobalTestingController
from backend.app.controllers.global_practising_controller import GlobalPractisingController
from backend.app.services.pose_service import PoseService
from backend.app.utils.exceptions import ValidationException, NotFoundException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/global", tags=["global"])

# In-memory storage for active sessions
_controllers: Dict[str, GlobalController] = {}
_pose_service: Optional[PoseService] = None


def get_pose_service() -> PoseService:
    """Get or create pose service singleton"""
    global _pose_service
    if _pose_service is None:
        try:
            _pose_service = PoseService()
        except Exception as e:
            # If pose service fails to initialize (e.g., in tests without ultralytics),
            # create a minimal mock instead
            logger.error(f"Failed to initialize PoseService: {e}")
            logger.warning("Using mock PoseService for testing")
            from unittest.mock import MagicMock
            _pose_service = MagicMock(spec=PoseService)
            _pose_service.predict.return_value = []
    return _pose_service


class StartSessionRequest(BaseModel):
    """Request model for starting a session"""
    mode: str  # "testing" or "practising"
    audio_path: Optional[str] = None


class ProcessFrameResponse(BaseModel):
    """Response model for frame processing"""
    success: bool
    timestamp: float
    frame_number: int
    errors: list
    score: float
    motion_events_pending: int
    stopped: bool = False
    message: Optional[str] = None


class ScoreResponse(BaseModel):
    """Response model for score retrieval"""
    session_id: str
    score: float
    stopped: bool = False


class ErrorsResponse(BaseModel):
    """Response model for errors retrieval"""
    session_id: str
    errors: list
    total_errors: int


@router.post("/{session_id}/start")
async def start_session(
    session_id: str,
    mode: str = Form(...),
    audio_file: Optional[UploadFile] = File(None),
    audio_path: Optional[str] = Form(None)
):
    """
    Start a global mode session
    
    Args:
        session_id: Unique session identifier
        mode: Mode type ("testing" or "practising")
        audio_file: Optional uploaded audio file
        audio_path: Optional path to existing audio file
        
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
        controller = GlobalTestingController(session_id, pose_service)
    else:
        controller = GlobalPractisingController(session_id, pose_service)
    
    # Handle audio file if provided
    audio_file_path = None
    if audio_file:
        # Save uploaded audio file
        import tempfile
        import os
        temp_dir = tempfile.gettempdir()
        audio_file_path = os.path.join(temp_dir, f"{session_id}_audio.wav")
        
        with open(audio_file_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
    elif audio_path:
        audio_file_path = audio_path
    
    # Set audio for beat detection
    if audio_file_path:
        controller.set_audio(audio_file_path)
    
    # Store controller
    _controllers[session_id] = controller
    
    return {
        "success": True,
        "session_id": session_id,
        "mode": mode,
        "audio_set": audio_file_path is not None,
        "message": f"Session {session_id} đã được khởi tạo ở chế độ {mode}"
    }


@router.post("/{session_id}/process-frame")
async def process_frame(
    session_id: str,
    frame_data: UploadFile = File(...),
    timestamp: float = Form(...),
    frame_number: int = Form(...)
):
    """
    Process a video frame
    
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
    
    return ProcessFrameResponse(**result)


@router.get("/{session_id}/score")
async def get_score(session_id: str):
    """
    Get current score for a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Current score
    """
    if session_id not in _controllers:
        raise NotFoundException("Session", session_id)
    
    controller = _controllers[session_id]
    score = controller.get_score()
    
    stopped = False
    if isinstance(controller, GlobalTestingController):
        stopped = controller.is_stopped()
    
    return ScoreResponse(
        session_id=session_id,
        score=score,
        stopped=stopped
    )


@router.get("/{session_id}/errors")
async def get_errors(session_id: str):
    """
    Get all errors for a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of detected errors
    """
    if session_id not in _controllers:
        raise NotFoundException("Session", session_id)
    
    controller = _controllers[session_id]
    errors = controller.get_errors()
    
    return ErrorsResponse(
        session_id=session_id,
        errors=errors,
        total_errors=len(errors)
    )


@router.post("/{session_id}/reset")
async def reset_session(session_id: str):
    """
    Reset a session (clear errors and reset score)
    
    Args:
        session_id: Session identifier
        
    Returns:
        Reset confirmation
    """
    if session_id not in _controllers:
        raise NotFoundException("Session", session_id)
    
    controller = _controllers[session_id]
    controller.reset()
    
    return {
        "success": True,
        "session_id": session_id,
        "message": f"Session {session_id} đã được reset"
    }


@router.post("/{session_id}/upload-video")
async def upload_and_process_video(
    session_id: str,
    video_file: UploadFile = File(...)
):
    """
    Upload và xử lý toàn bộ video file
    
    Args:
        session_id: Session identifier
        video_file: Video file to upload and process
        
    Returns:
        Processing result with errors and score
    """
    import tempfile
    import os
    from pathlib import Path
    from backend.app.services.video_utils import load_video, get_frames
    
    # Get controller
    if session_id not in _controllers:
        raise NotFoundException("Session", session_id)
    
    controller = _controllers[session_id]
    
    # Load golden template trước khi xử lý
    controller.ai_controller.load_golden_template()
    
    # Save uploaded video to temp file
    temp_dir = tempfile.gettempdir()
    temp_video_path = Path(temp_dir) / f"{session_id}_video_{video_file.filename}"
    
    try:
        # Save video file
        with open(temp_video_path, "wb") as f:
            content = await video_file.read()
            f.write(content)
        
        # Load video
        cap, metadata = load_video(temp_video_path)
        fps = metadata.get('fps', 30.0)
        
        # Process video frame by frame
        frame_number = 0
        total_frames = metadata.get('frame_count', 0)
        
        logger.info(f"Bắt đầu xử lý video: {total_frames} frames, FPS: {fps}")
        
        for frame in get_frames(cap):
            frame_number += 1
            timestamp = frame_number / fps
            
            # Process frame
            controller.process_frame(frame, timestamp, frame_number)
            
            # Update progress every 30 frames
            if frame_number % 30 == 0:
                logger.info(f"Đã xử lý {frame_number}/{total_frames} frames cho session {session_id}")
        
        cap.release()
        
        # Finalize error grouping
        controller.finalize_errors()
        
        # Get final results
        final_score = controller.get_score()
        final_errors = controller.get_errors()
        
        # Update session status to completed
        if isinstance(controller, GlobalTestingController):
            controller.stopped = False  # Reset stopped flag
        
        logger.info(f"Hoàn thành xử lý video: {frame_number} frames, {len(final_errors)} lỗi, điểm: {final_score}")
        
        return {
            "success": True,
            "session_id": session_id,
            "total_frames": total_frames,
            "processed_frames": frame_number,
            "score": final_score,
            "total_errors": len(final_errors),
            "errors": final_errors,
            "message": f"Đã xử lý {frame_number} frames, phát hiện {len(final_errors)} lỗi"
        }
        
    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xử lý video: {str(e)}"
        )
    finally:
        # Clean up temp file
        if temp_video_path.exists():
            try:
                temp_video_path.unlink()
            except:
                pass


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and free resources
    
    Args:
        session_id: Session identifier
        
    Returns:
        Deletion confirmation
    """
    # Idempotent delete: if session exists, remove it; otherwise, return success anyway
    # This allows frontend to clean up sessions that may have been lost due to backend restart
    if session_id in _controllers:
        # Remove controller
        del _controllers[session_id]
        logger.info(f"Session {session_id} đã được xóa khỏi backend memory")
    else:
        logger.info(f"Session {session_id} không tồn tại trong backend memory (có thể đã bị xóa hoặc backend đã restart)")
    
    return {
        "success": True,
        "session_id": session_id,
        "message": f"Session {session_id} đã được xóa"
    }
