# TODO: GlobalController Integration for Beat Detection

## Overview
This document outlines the planned integration of beat detection into GlobalController for Global Mode (Practising and Testing).

## Status
⚠️ **NOT YET IMPLEMENTED** - GlobalController does not exist in the codebase yet.

## Implementation Plan

### 1. Create `backend/app/controllers/global_controller.py`

The GlobalController will need to:

```python
class GlobalController:
    def __init__(self, session_id: str, candidate_id: int, db: Session, pose_service: PoseService):
        self.session_id = session_id
        self.candidate_id = candidate_id
        self.db = db
        self.pose_service = pose_service
        self.ai_controller = AIController(pose_service)
        
        # Beat detection tracking
        self.motion_events = []  # List[(timestamp, keypoints, motion_type)]
        
        # Frame buffer for motion detection
        self.frame_buffer = []
        
        # Error tracking
        self.errors = []
        
        # Score tracking (for testing mode)
        self.score = 100
    
    def _detect_motion_event(self, keypoints: np.ndarray, timestamp: float) -> Optional[str]:
        """
        Phát hiện sự kiện động tác (bước chân, vung tay)
        
        Returns:
            Loại motion ("step_left", "step_right", "arm_swing", ...) hoặc None
        """
        # TODO: Implement motion detection logic based on:
        # - Ankle movement for steps (keypoints 15, 16)
        # - Wrist movement for arm swings (keypoints 9, 10)
        # - Compare with previous frame in frame_buffer
        pass
    
    def process_frame(self, frame: np.ndarray, timestamp: float) -> Dict:
        """
        Process video frame and detect errors including rhythm errors
        """
        # 1. Detect pose
        keypoints_list = self.pose_service.predict(frame)
        
        # 2. Detect motion events
        if len(keypoints_list) > 0:
            keypoints = keypoints_list[0]
            motion_type = self._detect_motion_event(keypoints, timestamp)
            
            if motion_type:
                self.motion_events.append((timestamp, keypoints, motion_type))
        
        # 3. Batch rhythm error detection (every N motion events)
        if len(self.motion_events) >= 10:
            # Filter by motion type
            step_events = [(t, kp) for t, kp, mt in self.motion_events if "step" in mt]
            
            if len(step_events) > 0:
                rhythm_errors = self.ai_controller.detect_rhythm_errors(
                    step_events,
                    motion_type="step"
                )
                
                # Add to error list
                for error in rhythm_errors:
                    error["frame_number"] = frame_number
                    error["timestamp"] = timestamp
                    self.errors.append(error)
                    
                    # Deduct score (testing mode)
                    if hasattr(self, 'score'):
                        self.score -= error["deduction"]
            
            # Clear processed events
            self.motion_events = []
        
        # 4. Other error detections...
        
        return {
            "success": True,
            "timestamp": timestamp,
            "errors": self.errors,
            "score": self.score
        }
```

### 2. Motion Detection Algorithm

The `_detect_motion_event` method needs to detect:

#### Step Detection (Bước chân)
- Monitor left ankle (keypoint 15) and right ankle (keypoint 16)
- Compare Y-coordinate change between frames
- Threshold: dy > 20 pixels indicates a step
- Return "step_left" or "step_right"

#### Arm Swing Detection (Vung tay)
- Monitor left wrist (keypoint 9) and right wrist (keypoint 10)
- Compare position change between frames
- Threshold: movement > 30 pixels
- Return "arm_swing_left" or "arm_swing_right"

### 3. Batch Processing Strategy

To optimize performance:
1. Collect motion events in buffer (10-15 events)
2. Batch process rhythm errors
3. Clear buffer after processing
4. This reduces overhead of beat detection on every frame

### 4. Integration with AI Controller

```python
# In GlobalController initialization:
def set_audio(self, audio_path: str):
    """Set audio for beat detection"""
    self.ai_controller.set_beat_detector(audio_path)
```

## Expected Behavior

### Global Practising Mode
- Show rhythm error notifications in real-time
- Visual feedback when motion is off-beat
- No score deduction

### Global Testing Mode
- Track all rhythm errors
- Deduct score based on error severity and weight
- Generate final report with rhythm accuracy

## Testing

### Unit Tests
- Test `_detect_motion_event` with synthetic keypoints
- Test motion event buffering
- Test batch rhythm error detection

### Integration Tests
- Test with real video + audio
- Verify rhythm errors are detected correctly
- Verify score deduction works

## References
- BeatDetector: `backend/app/services/beat_detection.py`
- AIController: `backend/app/controllers/ai_controller.py`
- Config: `backend/app/config.py` (ERROR_THRESHOLDS, SCORING_CONFIG)
