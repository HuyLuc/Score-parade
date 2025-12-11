"""
Tests for GlobalController and its subclasses
"""
import pytest
import numpy as np
import tempfile
import soundfile as sf
from pathlib import Path
from unittest.mock import MagicMock
from contextlib import contextmanager

from backend.app.controllers.global_controller import GlobalController
from backend.app.controllers.global_testing_controller import GlobalTestingController
from backend.app.controllers.global_practising_controller import GlobalPractisingController
from backend.app.config import KEYPOINT_INDICES


@contextmanager
def create_test_audio(duration: float = 5.0, tempo: float = 120.0, sr: int = 22050):
    """Create a simple test audio file with context manager"""
    beat_interval = 60.0 / tempo
    samples = int(duration * sr)
    audio = np.zeros(samples)
    
    click_duration = 0.01
    click_samples = int(click_duration * sr)
    
    t = 0.0
    while t < duration:
        start_idx = int(t * sr)
        end_idx = min(start_idx + click_samples, samples)
        click = np.sin(2 * np.pi * 1000 * np.linspace(0, click_duration, end_idx - start_idx))
        audio[start_idx:end_idx] = click
        t += beat_interval
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        sf.write(temp_path, audio, sr)
        yield temp_path
    finally:
        Path(temp_path).unlink(missing_ok=True)


def create_mock_keypoints(left_ankle_y=100, right_ankle_y=100, 
                          left_wrist_x=50, right_wrist_x=50):
    """Create mock keypoints array [17, 3] with specified positions"""
    keypoints = np.zeros((17, 3))
    # Set all confidences to 1.0
    keypoints[:, 2] = 1.0
    
    # Set specific keypoints
    left_ankle_idx = KEYPOINT_INDICES["left_ankle"]
    right_ankle_idx = KEYPOINT_INDICES["right_ankle"]
    left_wrist_idx = KEYPOINT_INDICES["left_wrist"]
    right_wrist_idx = KEYPOINT_INDICES["right_wrist"]
    
    keypoints[left_ankle_idx, 1] = left_ankle_y
    keypoints[right_ankle_idx, 1] = right_ankle_y
    keypoints[left_wrist_idx, 0] = left_wrist_x
    keypoints[right_wrist_idx, 0] = right_wrist_x
    
    return keypoints


def test_global_controller_initialization():
    """Test GlobalController initialization"""
    pose_service = MagicMock()
    controller = GlobalController("test_session", pose_service)
    
    assert controller.session_id == "test_session"
    assert controller.score == 100.0
    assert len(controller.errors) == 0
    assert len(controller.motion_events) == 0
    assert controller.prev_keypoints is None


def test_global_controller_set_audio():
    """Test setting audio for beat detection"""
    pose_service = MagicMock()
    controller = GlobalController("test_session", pose_service)
    
    with create_test_audio(duration=5.0, tempo=120.0) as audio_path:
        controller.set_audio(audio_path)
        
        # Beat detector should be set in ai_controller
        assert controller.ai_controller.beat_detector is not None


def test_motion_detection_step_left():
    """Test detection of left step motion"""
    pose_service = MagicMock()
    controller = GlobalController("test_session", pose_service)
    
    # Create initial keypoints
    kp1 = create_mock_keypoints(left_ankle_y=100)
    controller.prev_keypoints = kp1
    controller.prev_timestamp = 0.0
    
    # Create keypoints with left ankle moved
    kp2 = create_mock_keypoints(left_ankle_y=130)  # Moved 30 pixels (> threshold)
    
    motion = controller._detect_motion_event(kp2, 0.1)
    
    assert motion == "step_left"


def test_motion_detection_step_right():
    """Test detection of right step motion"""
    pose_service = MagicMock()
    controller = GlobalController("test_session", pose_service)
    
    # Create initial keypoints
    kp1 = create_mock_keypoints(right_ankle_y=100)
    controller.prev_keypoints = kp1
    controller.prev_timestamp = 0.0
    
    # Create keypoints with right ankle moved
    kp2 = create_mock_keypoints(right_ankle_y=130)  # Moved 30 pixels (> threshold)
    
    motion = controller._detect_motion_event(kp2, 0.1)
    
    assert motion == "step_right"


def test_motion_detection_arm_swing():
    """Test detection of arm swing motion"""
    pose_service = MagicMock()
    controller = GlobalController("test_session", pose_service)
    
    # Create initial keypoints
    kp1 = create_mock_keypoints(left_wrist_x=50)
    controller.prev_keypoints = kp1
    controller.prev_timestamp = 0.0
    
    # Create keypoints with left wrist moved
    kp2 = create_mock_keypoints(left_wrist_x=100)  # Moved 50 pixels (> threshold)
    
    motion = controller._detect_motion_event(kp2, 0.1)
    
    assert motion == "arm_swing_left"


def test_motion_detection_no_motion():
    """Test no motion detected when movement is small"""
    pose_service = MagicMock()
    controller = GlobalController("test_session", pose_service)
    
    # Create initial keypoints
    kp1 = create_mock_keypoints(left_ankle_y=100)
    controller.prev_keypoints = kp1
    controller.prev_timestamp = 0.0
    
    # Create keypoints with small movement (below threshold)
    kp2 = create_mock_keypoints(left_ankle_y=105)  # Moved 5 pixels (< threshold)
    
    motion = controller._detect_motion_event(kp2, 0.1)
    
    assert motion is None


def test_process_frame_accumulates_motion_events():
    """Test that motion events are accumulated"""
    pose_service = MagicMock()
    controller = GlobalController("test_session", pose_service)
    
    # Mock pose service to return keypoints
    kp1 = create_mock_keypoints(left_ankle_y=100)
    pose_service.predict.return_value = [kp1]
    
    # Create dummy frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Process first frame (no motion yet, just sets prev_keypoints)
    result = controller.process_frame(frame, 0.0, 0)
    assert len(controller.motion_events) == 0
    
    # Process second frame with motion
    kp2 = create_mock_keypoints(left_ankle_y=130)
    pose_service.predict.return_value = [kp2]
    
    result = controller.process_frame(frame, 0.1, 1)
    
    # Should detect motion
    assert len(controller.motion_events) == 1
    assert controller.motion_events[0][2] == "step_left"


def test_testing_controller_deducts_score():
    """Test that testing controller deducts score on errors"""
    pose_service = MagicMock()
    controller = GlobalTestingController("test_session", pose_service)
    
    # Create a mock error
    error = {
        "type": "rhythm",
        "description": "Test error",
        "deduction": 5.0,
        "severity": 1.0
    }
    
    initial_score = controller.score
    controller._handle_error(error)
    
    assert controller.score == initial_score - 5.0


def test_testing_controller_stops_on_low_score():
    """Test that testing controller stops when score < 50"""
    pose_service = MagicMock()
    controller = GlobalTestingController("test_session", pose_service)
    
    # Set score just above threshold
    controller.score = 52.0
    
    # Add error that brings score below threshold
    error = {
        "type": "rhythm",
        "description": "Test error",
        "deduction": 5.0,
        "severity": 1.0
    }
    
    controller._handle_error(error)
    
    assert controller.score < 50
    assert controller.stopped is True


def test_practising_controller_no_deduction():
    """Test that practising controller does not deduct score"""
    pose_service = MagicMock()
    controller = GlobalPractisingController("test_session", pose_service)
    
    # Create a mock error
    error = {
        "type": "rhythm",
        "description": "Test error",
        "deduction": 5.0,
        "severity": 1.0
    }
    
    initial_score = controller.score
    controller._handle_error(error)
    
    # Score should not change
    assert controller.score == initial_score


def test_reset_clears_state():
    """Test that reset clears all state"""
    pose_service = MagicMock()
    controller = GlobalController("test_session", pose_service)
    
    # Add some state
    controller.motion_events = [(0.1, np.zeros((17, 3)), "step_left")]
    controller.errors = [{"type": "test"}]
    controller.score = 75.0
    controller.prev_keypoints = np.zeros((17, 3))
    
    # Reset
    controller.reset()
    
    # All state should be cleared
    assert len(controller.motion_events) == 0
    assert len(controller.errors) == 0
    assert controller.score == 100.0
    assert controller.prev_keypoints is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
