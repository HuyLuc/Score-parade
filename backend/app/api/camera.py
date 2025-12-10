"""
API routes cho camera management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import io
from backend.app.database.session import get_db
from backend.app.controllers.camera_controller import CameraController
from backend.app.controllers.snapshot_controller import SnapshotController
from backend.app.controllers.video_controller import VideoController
from backend.app.api.auth import get_current_user

router = APIRouter()

# Global camera controller instance (có thể cải thiện bằng dependency injection)
_camera_controller: Optional[CameraController] = None
_snapshot_controller: Optional[SnapshotController] = None
_video_controller: Optional[VideoController] = None


def get_camera_controller() -> CameraController:
    """Get camera controller instance"""
    global _camera_controller
    if _camera_controller is None:
        _camera_controller = CameraController()
    return _camera_controller


def get_snapshot_controller() -> SnapshotController:
    """Get snapshot controller instance"""
    global _snapshot_controller
    if _snapshot_controller is None:
        _snapshot_controller = SnapshotController(get_camera_controller())
    return _snapshot_controller


def get_video_controller() -> VideoController:
    """Get video controller instance"""
    global _video_controller
    if _video_controller is None:
        _video_controller = VideoController(get_camera_controller())
    return _video_controller


# Pydantic models
class CameraConnectRequest(BaseModel):
    camera_id: int


class CameraInfoResponse(BaseModel):
    camera_id: int
    width: int
    height: int
    fps: float
    is_opened: bool


class SnapshotResponse(BaseModel):
    success: bool
    message: str
    file_path: Optional[str] = None


@router.post("/connect")
async def connect_camera(
    request: CameraConnectRequest,
    current_user: dict = Depends(get_current_user)
):
    """Kết nối camera"""
    camera_controller = get_camera_controller()
    success, error = camera_controller.connect_camera(request.camera_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"success": True, "message": f"Đã kết nối camera {request.camera_id}"}


@router.post("/disconnect/{camera_id}")
async def disconnect_camera(
    camera_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Ngắt kết nối camera"""
    camera_controller = get_camera_controller()
    success, error = camera_controller.disconnect_camera(camera_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"success": True, "message": f"Đã ngắt kết nối camera {camera_id}"}


@router.get("/info", response_model=List[CameraInfoResponse])
async def get_all_cameras_info(
    current_user: dict = Depends(get_current_user)
):
    """Lấy thông tin tất cả cameras"""
    camera_controller = get_camera_controller()
    cameras_info = camera_controller.get_all_cameras_info()
    
    return [
        CameraInfoResponse(**info)
        for info in cameras_info
    ]


@router.get("/{camera_id}/frame")
async def get_camera_frame(
    camera_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Lấy frame từ camera (streaming)"""
    camera_controller = get_camera_controller()
    frame_data = camera_controller.get_frame(camera_id)
    
    if not frame_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không thể lấy frame từ camera {camera_id}"
        )
    
    frame_bytes, width, height = frame_data
    
    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={
            "X-Frame-Width": str(width),
            "X-Frame-Height": str(height),
        }
    )


@router.post("/{camera_id}/snapshot")
async def capture_snapshot(
    camera_id: int,
    session_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Chụp snapshot từ camera"""
    snapshot_controller = get_snapshot_controller()
    result = snapshot_controller.capture_snapshot(
        camera_id,
        save=True,
        session_id=session_id
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể chụp snapshot từ camera {camera_id}"
        )
    
    frame_bytes, file_path = result
    
    return SnapshotResponse(
        success=True,
        message="Chụp snapshot thành công",
        file_path=str(file_path) if file_path else None
    )


@router.post("/{camera_id}/video/start")
async def start_video_recording(
    camera_id: int,
    session_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Bắt đầu ghi video"""
    video_controller = get_video_controller()
    success, error = video_controller.start_recording(camera_id, session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"success": True, "message": f"Đã bắt đầu ghi video từ camera {camera_id}"}


@router.post("/{camera_id}/video/stop")
async def stop_video_recording(
    camera_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Dừng ghi video"""
    video_controller = get_video_controller()
    file_path = video_controller.stop_recording(camera_id)
    
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể dừng ghi video từ camera {camera_id}"
        )
    
    return {
        "success": True,
        "message": "Đã dừng ghi video",
        "file_path": str(file_path)
    }

