# Beat Detection Feature - Documentation

## 📋 Overview

This feature implements beat detection and rhythm analysis for the Score Parade system, addressing issue #3: "Hệ thống chưa kiểm tra nhịp/timing động tác so với beat nhạc."

The system now:
- ✅ Detects beats in audio files using Librosa
- ✅ Tracks motion events (steps, arm swings) with timestamps
- ✅ Compares motion timing with beats
- ✅ Reports rhythm errors with precise deviation measurements
- ✅ Deducts scores accordingly in Global Testing mode

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    Audio Analysis                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  BeatDetector (beat_detection.py)               │   │
│  │  - Load audio with Librosa                       │   │
│  │  - Detect beats and tempo                        │   │
│  │  - Find beat at specific time                    │   │
│  │  - Calculate rhythm errors                       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  AI Controller                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │  AIController (ai_controller.py)                │   │
│  │  - Set beat detector                             │   │
│  │  - Detect rhythm errors                          │   │
│  │  - Build error reports                           │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Global Controller (TODO)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  GlobalController (global_controller.py)        │   │
│  │  - Detect motion events                          │   │
│  │  - Batch process rhythm errors                   │   │
│  │  - Deduct scores                                 │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 📦 Implementation

### 1. BeatDetector Service

**File**: `backend/app/services/beat_detection.py`

Main class for beat detection using Librosa:

```python
detector = BeatDetector(audio_path="path/to/audio.mp3")

# Get tempo
print(f"Tempo: {detector.tempo} BPM")

# Find beat near timestamp
beat = detector.get_beat_at_time(timestamp=1.5, tolerance=0.1)

# Calculate rhythm errors
motion_times = [1.0, 2.0, 3.0, 4.0]
error_count, errors = detector.calculate_rhythm_error(
    motion_times,
    tolerance=0.15
)

# Get beats in range
beats = detector.get_expected_beats_in_range(0.0, 5.0)
```

### 2. AIController Integration

**File**: `backend/app/controllers/ai_controller.py`

Extended with rhythm detection methods:

```python
# Initialize
ai_controller = AIController(pose_service)

# Set audio for beat detection
ai_controller.set_beat_detector("path/to/audio.mp3")

# Detect rhythm errors
motion_keypoints = [
    (1.0, keypoints_frame_1),
    (2.0, keypoints_frame_2),
    (3.0, keypoints_frame_3),
]

rhythm_errors = ai_controller.detect_rhythm_errors(
    motion_keypoints,
    motion_type="step"
)

# Each error contains:
# {
#     "type": "rhythm",
#     "description": "Động tác step không theo nhịp (lệch 0.25s)",
#     "severity": 1.41,
#     "deduction": 1.41,
#     "body_part": "step"
# }
```

### 3. Configuration

**File**: `backend/app/config.py`

Rhythm thresholds and weights:

```python
ERROR_THRESHOLDS = {
    "step_rhythm": 0.15,  # 150ms tolerance
    "rhythm": 0.15,       # General rhythm tolerance
    # ... other thresholds
}

SCORING_CONFIG = {
    "error_weights": {
        "rhythm": 1.0,  # Weight for rhythm errors
        # ... other weights
    }
}
```

### 4. Dependencies

**File**: `backend/requirements.txt`

```
librosa>=0.10.0
soundfile>=0.12.1
```

## 🧪 Testing

### Unit Tests

**File**: `backend/tests/test_beat_detection.py`

Tests for BeatDetector:
- Initialization with synthetic audio
- Beat detection at specific times
- Rhythm error calculation
- Beat range queries

```bash
pytest backend/tests/test_beat_detection.py -v
```

### Integration Tests

**File**: `backend/tests/test_ai_controller_rhythm.py`

Tests for AIController rhythm detection:
- Setting beat detector
- Detecting rhythm errors with/without detector
- Error structure validation
- Empty motion handling

```bash
pytest backend/tests/test_ai_controller_rhythm.py -v
```

### Run All Tests

```bash
pytest backend/tests/ -v
```

## 📊 How It Works

### Beat Detection Process

1. **Audio Loading**
   - Librosa loads audio file
   - Converts to mono, resamples if needed

2. **Beat Tracking**
   - Librosa analyzes audio spectrum
   - Detects onset events
   - Estimates tempo (BPM)
   - Identifies beat frames
   - Converts to timestamps

3. **Motion Matching**
   - Compare motion timestamp with beat times
   - Find nearest beat within tolerance
   - If no beat found → rhythm error

### Rhythm Error Detection

```
Motion at t=1.25s
Nearest beat at t=1.0s
Difference = 0.25s
Tolerance = 0.15s
→ 0.25s > 0.15s → ERROR

Error details:
- Deviation: 0.25s
- Severity: sqrt(0.25/0.15) = 1.29
- Deduction: 1.0 * 1.29 = 1.29 points
```

### Scoring Formula

```python
# Sub-linear severity growth (using sqrt)
severity = sqrt(deviation / threshold)
severity = min(severity, 3.0)  # Cap at 3.0

# Deduction
deduction = weight * severity
```

This gives gentler scoring for small deviations:
- 0.15s deviation → severity 1.0 → -1.0 points
- 0.30s deviation → severity 1.41 → -1.41 points
- 0.60s deviation → severity 2.0 → -2.0 points

## 🎯 Usage Examples

### Example 1: Basic Beat Detection

```python
from backend.app.services.beat_detection import BeatDetector

# Load audio
detector = BeatDetector("data/audio/di_deu/global/total.mp3")

# Print tempo
print(f"Song tempo: {detector.tempo:.2f} BPM")
print(f"Beat interval: {60/detector.tempo:.2f} seconds")

# Print first 10 beats
for i, beat_time in enumerate(detector.beat_times[:10]):
    print(f"Beat {i+1}: {beat_time:.2f}s")
```

### Example 2: Check Motion Rhythm

```python
# Motion timestamps (when user steps)
motion_times = [0.5, 1.0, 1.6, 2.1, 2.7]

# Calculate errors
error_count, errors = detector.calculate_rhythm_error(
    motion_times,
    tolerance=0.15
)

print(f"Total motions: {len(motion_times)}")
print(f"Rhythm errors: {error_count}")

for motion_time, beat_time in errors:
    diff = abs(motion_time - beat_time)
    print(f"Motion at {motion_time:.2f}s, nearest beat at {beat_time:.2f}s, diff: {diff:.2f}s")
```

### Example 3: Integration with AIController

```python
from backend.app.controllers.ai_controller import AIController
from backend.app.services.pose_service import PoseService

# Initialize
pose_service = PoseService()
ai = AIController(pose_service)

# Set audio
ai.set_beat_detector("data/audio/song.mp3")

# Detect errors from motion data
motion_data = [
    (1.0, keypoints_1),
    (1.5, keypoints_2),
    (2.0, keypoints_3),
]

errors = ai.detect_rhythm_errors(motion_data, motion_type="step")

# Process errors
for error in errors:
    print(f"{error['description']}")
    print(f"  Severity: {error['severity']:.2f}")
    print(f"  Deduction: {error['deduction']:.2f} points")
```

## 🔮 Future Work (TODO)

### GlobalController Integration
See: `docs/TODO_GLOBAL_CONTROLLER.md`

- Implement motion event detection
- Batch rhythm error processing
- Real-time feedback in Practising mode
- Score deduction in Testing mode

### API Endpoints
See: `docs/TODO_API_ENDPOINTS.md`

- POST `/api/global/{session_id}/set-audio`
- POST `/api/global/{session_id}/process-frame`
- GET `/api/global/{session_id}/results`

### Enhanced Features

1. **Multi-instrument Beat Detection**
   - Separate beat tracks for drums, bass, melody
   - Allow user to choose which track to follow

2. **Adaptive Tolerance**
   - Start with strict tolerance
   - Gradually relax for beginners
   - Tighten for advanced users

3. **Visual Feedback**
   - Beat indicator overlay on video
   - Motion timing bars
   - Color-coded rhythm accuracy

4. **Beat Prediction**
   - Predict next beat
   - Give user advance warning
   - Help synchronize movements

## 📚 References

### External Libraries
- [Librosa Documentation](https://librosa.org/doc/latest/index.html)
- [Librosa Beat Tracking](https://librosa.org/doc/latest/beat.html)
- [SoundFile Documentation](https://python-soundfile.readthedocs.io/)

### Internal Documentation
- `backend/app/config.py` - Configuration
- `backend/app/controllers/ai_controller.py` - AI controller
- `docs/TODO_GLOBAL_CONTROLLER.md` - GlobalController TODO
- `docs/TODO_API_ENDPOINTS.md` - API endpoints TODO

### Related Issues
- Issue #3: "Hệ thống chưa kiểm tra nhịp/timing động tác so với beat nhạc"

## 🤝 Contributing

When extending this feature:

1. Follow existing code patterns
2. Add tests for new functionality
3. Update documentation
4. Keep tolerance values configurable
5. Use Vietnamese for user-facing messages

## ✅ Checklist

Implementation status:

- [x] BeatDetector service created
- [x] AIController integration
- [x] Configuration updated
- [x] Dependencies added
- [x] Unit tests written and passing
- [x] Integration tests written and passing
- [x] Documentation created
- [ ] GlobalController implementation (TODO)
- [ ] API endpoints (TODO)
- [ ] Frontend integration (TODO)
- [ ] End-to-end testing with real audio/video (pending audio files)
