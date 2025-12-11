# TODO: API Endpoints for Beat Detection

## Overview
This document outlines the planned API endpoints for beat detection integration in Global Mode.

## Status
⚠️ **NOT YET IMPLEMENTED** - API routes for global mode do not exist in the codebase yet.

## Implementation Plan

### 1. Create `backend/app/api/global.py`

This will contain FastAPI routes for Global Mode operations.

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

router = APIRouter(prefix="/api/global", tags=["global"])

# Request/Response models
class SetAudioRequest(BaseModel):
    audio_path: str

class SetAudioResponse(BaseModel):
    success: bool
    message: str
    tempo: Optional[float] = None

# Endpoint implementation
@router.post("/{session_id}/set-audio")
async def set_audio(
    session_id: str,
    request: SetAudioRequest,
    db: Session = Depends(get_db)
) -> SetAudioResponse:
    """
    Set audio file cho beat detection
    
    Args:
        session_id: ID của session hiện tại
        request: Request body chứa audio_path
        
    Returns:
        Response với tempo của bài nhạc
    """
    # Get or create controller
    controller = get_or_create_controller(session_id, db)
    
    # Set beat detector
    try:
        controller.ai_controller.set_beat_detector(request.audio_path)
        
        tempo = None
        if controller.ai_controller.beat_detector:
            tempo = float(controller.ai_controller.beat_detector.tempo)
        
        return SetAudioResponse(
            success=True,
            message="Beat detector initialized successfully",
            tempo=tempo
        )
    except Exception as e:
        return SetAudioResponse(
            success=False,
            message=f"Failed to initialize beat detector: {str(e)}",
            tempo=None
        )
```

### 2. Controller Management

Need a global controller registry:

```python
# Global registry for active controllers
_active_controllers = {}

def get_or_create_controller(
    session_id: str,
    db: Session
) -> GlobalController:
    """
    Get existing controller or create new one
    """
    if session_id not in _active_controllers:
        # TODO: Get candidate_id from session or request
        candidate_id = 1  # Placeholder
        
        from backend.app.services.pose_service import PoseService
        pose_service = PoseService()
        
        controller = GlobalController(
            session_id=session_id,
            candidate_id=candidate_id,
            db=db,
            pose_service=pose_service
        )
        
        _active_controllers[session_id] = controller
    
    return _active_controllers[session_id]

def cleanup_controller(session_id: str):
    """Remove controller from registry"""
    if session_id in _active_controllers:
        del _active_controllers[session_id]
```

### 3. Additional Endpoints

#### Start Session
```python
@router.post("/sessions/start")
async def start_session(
    candidate_id: int,
    mode: str,  # "practising" or "testing"
    db: Session = Depends(get_db)
):
    """Start a new global mode session"""
    session_id = str(uuid.uuid4())
    controller = get_or_create_controller(session_id, db)
    
    return {
        "session_id": session_id,
        "mode": mode,
        "started_at": datetime.now().isoformat()
    }
```

#### Process Frame
```python
@router.post("/{session_id}/process-frame")
async def process_frame(
    session_id: str,
    frame: UploadFile,
    timestamp: float,
    db: Session = Depends(get_db)
):
    """Process a video frame"""
    controller = get_or_create_controller(session_id, db)
    
    # Read frame
    frame_data = await frame.read()
    frame_array = np.frombuffer(frame_data, dtype=np.uint8)
    frame_decoded = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
    
    # Process
    result = controller.process_frame(frame_decoded, timestamp)
    
    return result
```

#### Get Results
```python
@router.get("/{session_id}/results")
async def get_results(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get session results including rhythm errors"""
    controller = get_or_create_controller(session_id, db)
    
    # Categorize errors
    rhythm_errors = [e for e in controller.errors if e["type"] == "rhythm"]
    other_errors = [e for e in controller.errors if e["type"] != "rhythm"]
    
    return {
        "session_id": session_id,
        "score": controller.score,
        "total_errors": len(controller.errors),
        "rhythm_errors": len(rhythm_errors),
        "rhythm_error_details": rhythm_errors,
        "other_errors": len(other_errors),
        "tempo": controller.ai_controller.beat_detector.tempo if controller.ai_controller.beat_detector else None
    }
```

#### End Session
```python
@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """End session and cleanup"""
    controller = get_or_create_controller(session_id, db)
    
    # Get final results
    results = {
        "session_id": session_id,
        "score": controller.score,
        "errors": controller.errors,
        "ended_at": datetime.now().isoformat()
    }
    
    # Cleanup
    cleanup_controller(session_id)
    
    return results
```

## Example API Usage

### 1. Start Session
```bash
curl -X POST http://localhost:8000/api/global/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": 1,
    "mode": "testing"
  }'

# Response:
# {
#   "session_id": "abc-123-def",
#   "mode": "testing",
#   "started_at": "2024-01-01T10:00:00"
# }
```

### 2. Set Audio
```bash
curl -X POST http://localhost:8000/api/global/abc-123-def/set-audio \
  -H "Content-Type: application/json" \
  -d '{
    "audio_path": "data/audio/di_deu/global/total.mp3"
  }'

# Response:
# {
#   "success": true,
#   "message": "Beat detector initialized successfully",
#   "tempo": 120.5
# }
```

### 3. Process Frames
```bash
# For each frame in video:
curl -X POST http://localhost:8000/api/global/abc-123-def/process-frame \
  -F "frame=@frame_001.jpg" \
  -F "timestamp=0.033"

# Response:
# {
#   "success": true,
#   "timestamp": 0.033,
#   "errors": [...],
#   "score": 98.5
# }
```

### 4. Get Results
```bash
curl http://localhost:8000/api/global/abc-123-def/results

# Response:
# {
#   "session_id": "abc-123-def",
#   "score": 85.3,
#   "total_errors": 25,
#   "rhythm_errors": 8,
#   "rhythm_error_details": [...],
#   "other_errors": 17,
#   "tempo": 120.5
# }
```

### 5. End Session
```bash
curl -X POST http://localhost:8000/api/global/abc-123-def/end

# Response:
# {
#   "session_id": "abc-123-def",
#   "score": 85.3,
#   "errors": [...],
#   "ended_at": "2024-01-01T10:05:00"
# }
```

## Security Considerations

1. **Authentication**: Add JWT token validation
2. **Authorization**: Verify candidate_id matches session owner
3. **File Upload**: Validate audio file format and size
4. **Path Traversal**: Sanitize audio_path to prevent directory traversal attacks
5. **Rate Limiting**: Prevent abuse of process-frame endpoint

## Testing

### Unit Tests
- Test each endpoint with mock controllers
- Test error handling
- Test validation

### Integration Tests
- Test full workflow: start → set audio → process frames → get results → end
- Test with real video and audio files
- Verify rhythm errors are correctly reported

## References
- BeatDetector: `backend/app/services/beat_detection.py`
- AIController: `backend/app/controllers/ai_controller.py`
- GlobalController: `docs/TODO_GLOBAL_CONTROLLER.md`
