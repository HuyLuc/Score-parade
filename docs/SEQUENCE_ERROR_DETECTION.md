# Sequence-Based Error Detection

## Overview

Sequence-based error detection is a feature that prevents over-penalization of persistent errors. Instead of penalizing each frame individually, consecutive frames with the same error type are grouped into sequences, and only one deduction is applied per sequence.

## Problem Statement

**Before**: The system compared and penalized each frame individually:
- 600 frames with small error (2-3°) → 600 separate errors
- Total deduction: 600 × 0.5 = 300 points ❌
- Final score: -200 (unfair!)

**After**: Consecutive frames are grouped into sequences:
- 600 frames with small error (2-3°) → 1 sequence
- Total deduction: 1 × 0.5 = 0.5 points ✅
- Final score: 99.5 (fair!)

## How It Works

### 1. Error Grouping

Errors are grouped into sequences based on:
- **Error type** (e.g., `arm_angle`, `leg_angle`)
- **Body part** (e.g., `arm`, `leg`)
- **Side** (e.g., `left`, `right`)

Only **consecutive frames** with the same error signature are grouped together.

### 2. Sequence Length Threshold

Errors must occur for at least `min_sequence_length` consecutive frames (default: 3) to be considered a sequence. Shorter error bursts remain as individual errors.

**Example**:
- 10 consecutive frames with arm error → 1 sequence
- 2 consecutive frames with arm error → 2 individual errors

### 3. Severity Aggregation

The severity of a sequence is calculated by aggregating the individual frame severities:
- **Mean** (default): Average severity across all frames
- **Max**: Maximum severity observed
- **Median**: Median severity value

## Usage

### Basic Usage

```python
from backend.app.controllers.ai_controller import AIController
from backend.app.services.pose_service import PoseService

# Initialize controller
pose_service = PoseService()
controller = AIController(pose_service)

# Collect errors from all frames
frame_errors = []
for frame_number in range(num_frames):
    keypoints = pose_service.estimate_pose(frame)
    errors = controller.detect_posture_errors(keypoints, frame_number, timestamp)
    frame_errors.extend(errors)

# Process with sequence comparison
result = controller.process_video_sequence(frame_errors)

# Access results
sequences = result["sequences"]
total_deduction = result["total_deduction"]
sequence_count = result["sequence_count"]
original_error_count = result["original_error_count"]

print(f"Reduced {original_error_count} errors to {sequence_count} sequences")
print(f"Total deduction: {total_deduction:.2f} points")
```

### Result Structure

```python
{
    "sequences": [
        {
            "type": "arm_angle",
            "description": "Tay trái quá cao",
            "severity": 2.0,
            "deduction": 0.5,
            "body_part": "arm",
            "side": "left",
            "start_frame": 0,
            "end_frame": 599,
            "frame_count": 600,
            "start_timestamp": 0.0,
            "end_timestamp": 19.8,
            "is_sequence": True
        }
    ],
    "total_deduction": 0.5,
    "sequence_count": 1,
    "original_error_count": 600
}
```

## Configuration

Edit `backend/app/config.py`:

```python
SEQUENCE_COMPARISON_CONFIG = {
    "enabled": True,                   # Enable/disable sequence comparison
    "min_sequence_length": 3,          # Minimum frames to form a sequence
    "severity_aggregation": "mean",    # Aggregation method: "mean", "max", "median"
}
```

### Configuration Options

#### `enabled` (bool)
- **Default**: `True`
- **Description**: Enable or disable sequence-based error detection
- **Impact**: When disabled, all frame errors are returned as-is without grouping

#### `min_sequence_length` (int)
- **Default**: `3`
- **Description**: Minimum consecutive frames required to form a sequence
- **Impact**: 
  - Higher values (e.g., 5) = More strict, fewer sequences
  - Lower values (e.g., 2) = More lenient, more sequences
- **Recommended**: 3-5 frames (100-167ms at 30fps)

#### `severity_aggregation` (str)
- **Default**: `"mean"`
- **Options**: `"mean"`, `"max"`, `"median"`
- **Description**: Method to aggregate severity across frames in a sequence
- **Impact**:
  - `"mean"`: Balanced, represents average error
  - `"max"`: Conservative, focuses on worst error
  - `"median"`: Robust to outliers

## Examples

### Example 1: Persistent Error

```python
# User's arm is consistently 2° off for 600 frames (20 seconds)
frame_errors = [
    {"type": "arm_angle", "severity": 2.0, "deduction": 0.5, "frame_number": i, ...}
    for i in range(600)
]

result = controller.process_video_sequence(frame_errors)
# Result: 1 sequence, 0.5 point deduction
# Improvement: 99.8% reduction vs. 300 points!
```

### Example 2: Multiple Error Types

```python
# User has both arm and leg errors
arm_errors = [arm_error for i in range(100)]  # 100 arm errors
leg_errors = [leg_error for i in range(100)]  # 100 leg errors

result = controller.process_video_sequence(arm_errors + leg_errors)
# Result: 2 sequences (one for arm, one for leg)
# Each error type is grouped separately
```

### Example 3: Interrupted Sequences

```python
# Error occurs, disappears, then returns
errors = (
    [error for i in range(10)] +     # Frames 0-9: error present
    [] +                              # Frames 10-19: no error (gap)
    [error for i in range(10)]       # Frames 20-29: error returns
)

result = controller.process_video_sequence(errors)
# Result: 2 sequences (separated by the gap)
```

### Example 4: Isolated Errors

```python
# User makes only 2 brief mistakes
frame_errors = [
    {"type": "arm_angle", "severity": 2.0, "frame_number": 0, ...},
    {"type": "arm_angle", "severity": 2.0, "frame_number": 1, ...}
]

result = controller.process_video_sequence(frame_errors)
# Result: 2 individual errors (not grouped, < min_sequence_length)
# Full deduction applied (no reduction)
```

## Testing

Run tests:
```bash
python -m pytest backend/tests/test_sequence_comparison.py -v
```

Run demo:
```bash
python demo_sequence_comparison.py
```

## Performance Impact

- **Computation**: Minimal overhead (~O(n log n) for sorting + O(n) for grouping)
- **Memory**: Negligible (stores sequences instead of individual frame errors)
- **Scoring time**: Reduced (fewer deductions to calculate)

## Benefits

1. **Fair Scoring**: Persistent errors are not over-penalized
2. **Better User Experience**: Users with consistent form don't get unfairly low scores
3. **More Meaningful Feedback**: Sequences show the duration and persistence of errors
4. **Configurable**: Can be tuned for different use cases

## Limitations

1. **Sequence breaks**: Brief corrections (e.g., 1 good frame) will break a sequence
2. **Not for rhythm errors**: Rhythm errors typically don't need sequence grouping
3. **Delayed feedback**: Requires collecting all frames before processing (not real-time)

## Future Enhancements

Possible improvements:
- [ ] Allow small gaps in sequences (e.g., ignore 1-2 frame corrections)
- [ ] Add weighted aggregation (recent frames weighted higher)
- [ ] Support real-time sequence detection with sliding windows
- [ ] Add sequence visualization in error reports

## See Also

- [Demo Script](../demo_sequence_comparison.py)
- [Test Cases](../backend/tests/test_sequence_comparison.py)
- [Implementation](../backend/app/services/sequence_comparison.py)
