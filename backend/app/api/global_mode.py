"""
Global Mode API endpoints
Handles global practising and testing modes with beat detection
"""
import logging
import time
import cv2
import numpy as np
import subprocess
from typing import Dict, Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel

from backend.app.controllers.global_controller import GlobalController
from backend.app.controllers.global_testing_controller import GlobalTestingController
from backend.app.controllers.global_practising_controller import GlobalPractisingController
from backend.app.services.pose_service import PoseService
from backend.app.services.database_service import DatabaseService
from backend.app.utils.exceptions import ValidationException, NotFoundException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/global", tags=["global"])

# In-memory storage for active sessions
_controllers: Dict[str, GlobalController] = {}
_pose_service: Optional[PoseService] = None
_db_service = DatabaseService()


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


class PersonFrameResult(BaseModel):
    person_id: int
    errors: list
    score: float
    stopped: Optional[bool] = False
    message: Optional[str] = None


class ProcessFrameResponse(BaseModel):
    """Response model for frame processing (multi-person)"""
    success: bool
    timestamp: float
    frame_number: int
    multi_person: bool = False
    persons: list[PersonFrameResult]
    # Danh sách ID xuất hiện trong frame hiện tại
    person_ids: list[int] = []
    # Danh sách ID được coi là "người thật" (track ổn định theo thời gian)
    stable_person_ids: list[int] = []
    # Tổng số người được chấm (ưu tiên stable_person_ids nếu có)
    total_persons: int = 0


class ScoreResponse(BaseModel):
    """Response model for score retrieval (multi-person)"""
    session_id: str
    scores: Dict[int, float]
    stopped: Optional[Dict[int, bool]] = None


class ErrorsResponse(BaseModel):
    """Response model for errors retrieval (multi-person)"""
    session_id: str
    errors: Dict[int, list]
    total_errors: Dict[int, int]


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
    
    # Lưu session vào database
    _db_service.create_or_update_session(
        session_id=session_id,
        mode=mode,
        status="active",
        video_path=None,
        total_frames=0,
    )

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
        # Fallback: lấy từ database nếu controller không còn trong memory
        scores = _db_service.get_scores_map(session_id)
        if not scores:
            raise NotFoundException("Session", session_id)
        return ScoreResponse(session_id=session_id, scores=scores, stopped=None)
    
    controller = _controllers[session_id]
    scores = controller.get_score()
    
    stopped = None
    if isinstance(controller, GlobalTestingController):
        stopped = controller.is_stopped()
    
    return ScoreResponse(
        session_id=session_id,
        scores=scores,
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
        # Fallback: lấy từ database
        errors = _db_service.get_errors_map(session_id)
        if not errors:
            raise NotFoundException("Session", session_id)
        totals = {pid: len(errs) for pid, errs in errors.items()}
        return ErrorsResponse(session_id=session_id, errors=errors, total_errors=totals)
    
    controller = _controllers[session_id]
    errors = controller.get_errors()
    totals = {pid: len(errs) for pid, errs in errors.items()}
    
    return ErrorsResponse(
        session_id=session_id,
        errors=errors,
        total_errors=totals
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

    # Đặt lại trạng thái session trong DB (đánh dấu active, không xóa dữ liệu cũ)
    _db_service.create_or_update_session(
        session_id=session_id,
        mode="testing" if isinstance(controller, GlobalTestingController) else "practising",
        status="active",
        total_frames=0,
        video_path=None,
    )
    
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
    
    print(f"\n{'='*60}")
    print(f"UPLOAD VIDEO - Session: {session_id}")
    print(f"Filename: {video_file.filename}")
    print(f"{'='*60}\n")
    logger.info(f"Upload video request - Session: {session_id}, File: {video_file.filename}")
    
    # Get controller
    if session_id not in _controllers:
        print(f"[ERROR] Session {session_id} not found in controllers!")
        raise NotFoundException("Session", session_id)
    
    controller = _controllers[session_id]
    print(f"[OK] Controller found: {type(controller)}")
    
    # Load golden template trước khi xử lý
    print("[INFO] Loading golden template...")
    controller.ai_controller.load_golden_template()
    print("[OK] Golden template loaded")
    
    # Save uploaded video to temp file
    temp_dir_str = tempfile.gettempdir()
    temp_dir = Path(temp_dir_str)
    temp_video_path = temp_dir / f"{session_id}_video_{video_file.filename}"
    
    print(f"[INFO] Saving video to temp: {temp_video_path}")
    
    # Variables for skeleton video (needed in finally block)
    skeleton_video_filename = None
    skeleton_video_url = None
    
    try:
        # Save video file
        print("[INFO] Reading video file...")
        with open(temp_video_path, "wb") as f:
            content = await video_file.read()
            f.write(content)
        print(f"[OK] Video saved: {len(content)} bytes")
        
        # Load video
        print("[INFO] Loading video...")
        cap, metadata = load_video(temp_video_path)
        fps = metadata.get('fps', 30.0)
        
        # Process video frame by frame
        frame_number = 0
        total_frames = metadata.get('frame_count', 0)

        # Cập nhật thông tin session vào database (total_frames, video_path)
        _db_service.create_or_update_session(
            session_id=session_id,
            mode="testing" if isinstance(controller, GlobalTestingController) else "practising",
            status="active",
            total_frames=total_frames,
            video_path=str(temp_video_path),
        )
        
        print(f"[INFO] Video loaded: {total_frames} frames, FPS: {fps}")
        logger.info(f"Bắt đầu xử lý video: {total_frames} frames, FPS: {fps}")
        
        for frame in get_frames(cap):
            frame_number += 1
            timestamp = frame_number / fps
            
            # Process frame
            controller.process_frame(frame, timestamp, frame_number)
            
            # Update progress every 30 frames
            if frame_number % 30 == 0:
                logger.info(f"Đã xử lý {frame_number}/{total_frames} frames cho session {session_id}")
                print(f"[PROGRESS] Processed {frame_number}/{total_frames} frames")
        
        cap.release()
        print(f"[OK] Finished processing {frame_number} frames")
        
        # Finalize error grouping
        print("[INFO] Finalizing errors...")
        controller.finalize_errors()
        
        # Get final results
        final_score = controller.get_score()  # dict person_id -> score
        final_errors = controller.get_errors()  # dict person_id -> list
        total_errors = {pid: len(errs) for pid, errs in final_errors.items()}

        print(f"[RESULT] Scores per person: {final_score}, Errors per person: {total_errors}")
        
        logger.info(f"Hoàn thành xử lý video: {frame_number} frames, errors per person: {total_errors}, scores: {final_score}")
        
        # Create video with skeleton overlay BEFORE cleaning up input video
        # Write to debug log file
        debug_log_path = Path("skeleton_debug.log")
        try:
            with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                debug_log.write(f"\n{'='*60}\n")
                debug_log.write(f"BAT DAU TAO SKELETON VIDEO - Session: {session_id}\n")
                debug_log.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
                debug_log.write(f"{'='*60}\n")
        except Exception as log_error:
            logger.error(f"Failed to write to debug log: {log_error}")
        
        logger.info("=" * 60)
        logger.info("BAT DAU TAO SKELETON VIDEO")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Temp dir: {temp_dir}")
        print(f"\n{'='*60}")
        print(f"BAT DAU TAO SKELETON VIDEO - Session: {session_id}")
        print(f"{'='*60}\n")
        
        try:
            # Write to debug log
            with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                debug_log.write(f"[INFO] Importing create_skeleton_video...\n")
            
            from backend.app.services.skeleton_visualization import create_skeleton_video
            from backend.app.config import OUTPUT_DIR
            
            with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                debug_log.write(f"[OK] Import successful\n")
            
            # Save skeleton video to data/output/{session_id}/ directory
            # This ensures the video persists and is accessible even if codec is not browser-compatible
            # Create a dedicated folder for each session (an toàn với trường hợp thư mục đã tồn tại)
            session_output_dir = OUTPUT_DIR / session_id
            try:
                session_output_dir.mkdir(parents=True, exist_ok=True)
            except FileExistsError:
                # Nếu đã tồn tại file/dir cùng tên, chỉ bỏ qua khi nó là thư mục
                if not session_output_dir.is_dir():
                    logger.error(
                        f"[SKELETON] session_output_dir tồn tại nhưng không phải thư mục: {session_output_dir}"
                    )
                    raise
            skeleton_video_path = session_output_dir / "skeleton_video.mp4"
            
            logger.info(f"[SKELETON] Bat dau tao video voi skeleton tu: {temp_video_path}")
            logger.info(f"[SKELETON] Output path se la: {skeleton_video_path}")
            logger.info(f"[SKELETON] Output directory: {session_output_dir.absolute()}")
            print(f"[SKELETON] Input video: {temp_video_path}")
            print(f"[SKELETON] Output video: {skeleton_video_path}")
            print(f"[SKELETON] Output dir: {session_output_dir.absolute()}")
            
            # Make sure input video still exists
            if not temp_video_path.exists():
                logger.error(f"[ERROR] Input video khong ton tai: {temp_video_path}")
                logger.error(f"   Current working directory: {Path.cwd()}")
                logger.error(f"   Temp dir exists: {Path(temp_dir).exists()}")
                print(f"[ERROR] Input video khong ton tai: {temp_video_path}")
                print(f"   Current working directory: {Path.cwd()}")
                skeleton_video_url = None
            else:
                input_size = temp_video_path.stat().st_size
                logger.info(f"[OK] Input video exists: {input_size} bytes")
                logger.info(f"[OK] Input video path: {temp_video_path}")
                print(f"[OK] Input video exists: {input_size} bytes")
                print(f"[OK] Input video path: {temp_video_path}")
                
                # Check pose_service
                with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                    debug_log.write(f"[INFO] Checking pose_service...\n")
                    debug_log.write(f"   Controller type: {type(controller)}\n")
                    debug_log.write(f"   Has pose_service: {hasattr(controller, 'pose_service')}\n")
                    debug_log.write(f"   pose_service value: {controller.pose_service}\n")
                    debug_log.write(f"   pose_service type: {type(controller.pose_service) if controller.pose_service else 'None'}\n")
                
                if controller.pose_service is None:
                    error_msg = "[ERROR] pose_service is None!"
                    logger.error(error_msg)
                    logger.error(f"   Controller type: {type(controller)}")
                    logger.error(f"   Controller has pose_service attr: {hasattr(controller, 'pose_service')}")
                    print(error_msg)
                    print(f"   Controller type: {type(controller)}")
                    print(f"   Controller attributes: {dir(controller)}")
                    with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                        debug_log.write(f"{error_msg}\n")
                        debug_log.write(f"   Controller attributes: {dir(controller)}\n")
                    # Try to get pose_service from global function
                    try:
                        pose_service = get_pose_service()
                        logger.info(f"[FALLBACK] Using global pose_service: {type(pose_service)}")
                        print(f"[FALLBACK] Using global pose_service: {type(pose_service)}")
                        with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                            debug_log.write(f"[FALLBACK] Using global pose_service: {type(pose_service)}\n")
                        # Use fallback pose_service
                        controller_pose_service = pose_service
                    except Exception as fallback_error:
                        logger.error(f"[ERROR] Cannot get fallback pose_service: {fallback_error}")
                        print(f"[ERROR] Cannot get fallback pose_service: {fallback_error}")
                        skeleton_video_url = None
                        controller_pose_service = None
                else:
                    ok_msg = f"[OK] pose_service is available: {type(controller.pose_service)}"
                    logger.info(ok_msg)
                    print(ok_msg)
                    with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                        debug_log.write(f"{ok_msg}\n")
                    controller_pose_service = controller.pose_service
                
                # Only proceed if we have a valid pose_service
                if controller_pose_service is not None:
                    
                    try:
                        logger.info("[SKELETON] Dang goi create_skeleton_video...")
                        logger.info(f"   Input: {temp_video_path}")
                        logger.info(f"   Output: {skeleton_video_path}")
                        logger.info(f"   Output dir exists: {session_output_dir.exists()}")
                        logger.info(f"   Output dir: {session_output_dir.absolute()}")
                        logger.info(f"   Confidence threshold: 0.3")
                        print("[SKELETON] Dang goi create_skeleton_video...")
                        print(f"   Input: {temp_video_path}")
                        print(f"   Output: {skeleton_video_path}")
                        
                        # Ensure output directory exists
                        session_output_dir.mkdir(parents=True, exist_ok=True)
                        logger.info(f"[OK] Ensured output directory exists: {session_output_dir.absolute()}")
                        print(f"[OK] Output directory exists: {session_output_dir.absolute()}")
                        
                        skeleton_metadata = create_skeleton_video(
                            str(temp_video_path),
                            str(skeleton_video_path),
                            controller_pose_service,
                            confidence_threshold=0.3
                        )
                        
                        logger.info("[OK] create_skeleton_video returned successfully!")
                        logger.info(f"[METADATA] {skeleton_metadata}")
                        print("[OK] create_skeleton_video returned successfully!")
                        print(f"[METADATA] {skeleton_metadata}")
                        
                        # Wait a bit and check again (file might be written asynchronously)
                        time.sleep(0.5)
                        print("[WAIT] Waiting 0.5s for file to be written...")
                        
                        # Check if file exists immediately after function returns
                        if skeleton_video_path.exists():
                            file_size = skeleton_video_path.stat().st_size
                            processed_frames = skeleton_metadata.get('processed_frames', 0)
                            total_frames = skeleton_metadata.get('total_frames', 0)
                            codec = skeleton_metadata.get('codec', 'unknown')

                            # ---------------------------------------------
                            # Convert skeleton video sang H.264/AAC thân thiện với trình duyệt
                            # ---------------------------------------------
                            web_skeleton_path = session_output_dir / "skeleton_video_web.mp4"
                            try:
                                ffmpeg_cmd = [
                                    "ffmpeg",
                                    "-y",
                                    "-i",
                                    str(skeleton_video_path),
                                    "-c:v",
                                    "libx264",
                                    "-preset",
                                    "fast",
                                    "-crf",
                                    "23",
                                    "-c:a",
                                    "aac",
                                    "-b:a",
                                    "128k",
                                    "-movflags",
                                    "+faststart",
                                    str(web_skeleton_path),
                                ]
                                logger.info(f"[FFMPEG] Converting skeleton video for web: {' '.join(ffmpeg_cmd)}")
                                subprocess.run(
                                    ffmpeg_cmd,
                                    check=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                )
                                if web_skeleton_path.exists() and web_skeleton_path.stat().st_size > 0:
                                    logger.info(
                                        f"[FFMPEG] Web skeleton video created: {web_skeleton_path} "
                                        f"({web_skeleton_path.stat().st_size} bytes)"
                                    )
                                    target_path = web_skeleton_path
                                else:
                                    logger.warning(
                                        "[FFMPEG] Web skeleton video not found or empty, "
                                        "falling back to original skeleton_video.mp4"
                                    )
                                    target_path = skeleton_video_path
                            except subprocess.CalledProcessError as ff_err:
                                logger.error(
                                    f"[FFMPEG] Error converting skeleton video for web: {ff_err}",
                                    exc_info=True,
                                )
                                target_path = skeleton_video_path
                            except Exception as ff_unexpected:
                                logger.error(
                                    f"[FFMPEG] Unexpected error during conversion: {ff_unexpected}",
                                    exc_info=True,
                                )
                                target_path = skeleton_video_path

                            # Use relative path from OUTPUT_DIR for URL (ưu tiên bản web nếu có)
                            skeleton_video_filename = f"{session_id}/{target_path.name}"
                            skeleton_video_url = f"/api/videos/{skeleton_video_filename}"
                            
                            logger.info("[SUCCESS] Da tao video voi skeleton:")
                            logger.info(f"   Path: {skeleton_video_path}")
                            logger.info(f"   Absolute path: {skeleton_video_path.absolute()}")
                            logger.info(f"   Size: {file_size} bytes")
                            logger.info(f"   Frames: {processed_frames}/{total_frames} co skeleton")
                            logger.info(f"   Codec: {codec}")
                            logger.info(f"   URL: {skeleton_video_url}")
                            print("[SUCCESS] Da tao video voi skeleton!")
                            print(f"   Path: {skeleton_video_path.absolute()}")
                            print(f"   Size: {file_size} bytes")
                            print(f"   Frames: {processed_frames}/{total_frames} co skeleton")
                            print(f"   URL: {skeleton_video_url}")
                            
                            if processed_frames == 0:
                                logger.warning("[WARNING] Khong co skeleton nao duoc phat hien trong video!")
                                print("[WARNING] Khong co skeleton nao duoc phat hien trong video!")
                        else:
                            logger.error(f"[ERROR] Video skeleton khong duoc tao (file khong ton tai): {skeleton_video_path}")
                            logger.error(f"   Absolute path: {skeleton_video_path.absolute()}")
                            logger.error(f"   Parent dir exists: {skeleton_video_path.parent.exists()}")
                            logger.error(f"   Parent dir: {skeleton_video_path.parent}")
                            logger.error(f"   Parent dir absolute: {skeleton_video_path.parent.absolute()}")
                            print(f"[ERROR] Video skeleton khong duoc tao!")
                            print(f"   Path: {skeleton_video_path.absolute()}")
                            print(f"   Parent dir exists: {skeleton_video_path.parent.exists()}")
                            # List files in parent directory
                            if skeleton_video_path.parent.exists():
                                files = list(skeleton_video_path.parent.iterdir())
                                logger.error(f"   Files in parent dir: {files}")
                                print(f"   Files in parent dir: {[f.name for f in files]}")
                            skeleton_video_url = None
                    except RuntimeError as runtime_error:
                        logger.error(f"[ERROR] RuntimeError trong create_skeleton_video: {runtime_error}", exc_info=True)
                        logger.error(f"   RuntimeError details: {str(runtime_error)}")
                        print(f"[ERROR] RuntimeError: {runtime_error}")
                        import traceback
                        print(traceback.format_exc())
                        skeleton_video_url = None
                    except Exception as create_error:
                        error_msg = f"[ERROR] Exception trong create_skeleton_video: {type(create_error).__name__}: {create_error}"
                        logger.error(error_msg, exc_info=True)
                        import traceback
                        traceback_str = traceback.format_exc()
                        logger.error(f"   Traceback: {traceback_str}")
                        print(error_msg)
                        print(traceback_str)
                        with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                            debug_log.write(f"{error_msg}\n")
                            debug_log.write(f"Traceback:\n{traceback_str}\n")
                        skeleton_video_url = None
                else:
                    error_msg = "[ERROR] controller_pose_service is None - Cannot create skeleton video!"
                    logger.error(error_msg)
                    print(error_msg)
                    with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                        debug_log.write(f"{error_msg}\n")
                    skeleton_video_url = None
        except ImportError as import_error:
            logger.error(f"[ERROR] ImportError khi import create_skeleton_video: {import_error}", exc_info=True)
            print(f"[ERROR] ImportError: {import_error}")
            skeleton_video_filename = None
            skeleton_video_url = None
        except Exception as e:
            error_msg = f"[ERROR] Loi khi tao video voi skeleton: {type(e).__name__}: {e}"
            logger.error(error_msg, exc_info=True)
            import traceback
            traceback_str = traceback.format_exc()
            logger.error(f"   Full traceback: {traceback_str}")
            print(error_msg)
            print(traceback_str)
            with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                debug_log.write(f"{error_msg}\n")
                debug_log.write(f"Full traceback:\n{traceback_str}\n")
            skeleton_video_filename = None
            skeleton_video_url = None
        
        logger.info("=" * 60)
        logger.info("KET THUC TAO SKELETON VIDEO")
        logger.info(f"Final skeleton_video_url: {skeleton_video_url}")
        logger.info(f"Final skeleton_video_filename: {skeleton_video_filename}")
        print(f"\n{'='*60}")
        print(f"KET THUC TAO SKELETON VIDEO")
        print(f"Final skeleton_video_url: {skeleton_video_url}")
        print(f"Final skeleton_video_filename: {skeleton_video_filename}")
        print(f"{'='*60}\n")
        if skeleton_video_url:
            logger.info(f"[SUCCESS] Skeleton video saved to: {skeleton_video_path}")
            logger.info(f"[URL] Access via: http://localhost:8000{skeleton_video_url}")
            logger.info(f"[PATH] Or download from: {skeleton_video_path}")
            print(f"[SUCCESS] Skeleton video saved to: {skeleton_video_path}")
            print(f"[URL] Access via: http://localhost:8000{skeleton_video_url}")
        else:
            error_msg = "[ERROR] skeleton_video_url is None - Video khong duoc tao!"
            logger.error(error_msg)
            print(error_msg)
            with open(debug_log_path, "a", encoding="utf-8") as debug_log:
                debug_log.write(f"{error_msg}\n")
                debug_log.write(f"Final skeleton_video_url: {skeleton_video_url}\n")
                debug_log.write(f"Final skeleton_video_filename: {skeleton_video_filename}\n")
        
        # Cập nhật lại session trong DB với trạng thái completed và skeleton_video_url (nếu có)
        try:
            _db_service.create_or_update_session(
                session_id=session_id,
                mode="testing" if isinstance(controller, GlobalTestingController) else "practising",
                status="completed",
                total_frames=total_frames,
                video_path=str(temp_video_path),
                skeleton_video_url=skeleton_video_url,
            )
        except Exception as db_err:
            logger.error(f"❌ Error updating session with skeleton_video_url: {db_err}", exc_info=True)

        return {
            "success": True,
            "session_id": session_id,
            "total_frames": total_frames,
            "processed_frames": frame_number,
            "scores": final_score,
            "total_errors": total_errors,
            "errors": final_errors,
            "skeleton_video_url": skeleton_video_url,
            "skeleton_video_filename": skeleton_video_filename,
            "message": f"Đã xử lý {frame_number} frames, phát hiện {sum(total_errors.values())} lỗi (tổng tất cả người)"
        }
        
    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xử lý video: {str(e)}"
        )
    finally:
        # Clean up temp file AFTER skeleton video is created
        # Only delete if skeleton video was successfully created
        if temp_video_path.exists():
            if skeleton_video_url:  # Only delete if skeleton video exists
                try:
                    temp_video_path.unlink()
                    logger.info(f"Đã xóa video input tạm: {temp_video_path}")
                except Exception as e:
                    logger.warning(f"Không thể xóa video input: {e}")
            else:
                # Keep input video if skeleton creation failed (for debugging)
                logger.info(f"Giữ lại video input vì skeleton video không được tạo: {temp_video_path}")


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

    # Xóa dữ liệu trong DB (sessions, persons, errors)
    _db_service.delete_session_data(session_id)
    
    return {
        "success": True,
        "session_id": session_id,
        "message": f"Session {session_id} đã được xóa"
    }
