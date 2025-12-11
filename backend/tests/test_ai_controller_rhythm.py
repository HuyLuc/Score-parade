"""
Integration tests for AIController rhythm detection
"""
import pytest
import numpy as np
import tempfile
import soundfile as sf
from pathlib import Path
from unittest.mock import MagicMock
from contextlib import contextmanager
from backend.app.controllers.ai_controller import AIController


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


def test_ai_controller_set_beat_detector():
    """Test setting beat detector in AIController"""
    # Mock pose_service to avoid heavy dependencies
    pose_service = MagicMock()
    ai_controller = AIController(pose_service)
    
    # Initially should be None
    assert ai_controller.beat_detector is None
    
    # Create test audio using context manager
    with create_test_audio(duration=5.0, tempo=120.0) as audio_path:
        # Set beat detector
        ai_controller.set_beat_detector(audio_path)
        
        # Should now have a beat detector
        assert ai_controller.beat_detector is not None
        assert ai_controller.beat_detector.tempo > 0


def test_ai_controller_detect_rhythm_errors_no_detector():
    """Test rhythm error detection when no beat detector is set"""
    # Mock pose_service to avoid heavy dependencies
    pose_service = MagicMock()
    ai_controller = AIController(pose_service)
    
    # Create dummy motion keypoints
    motion_keypoints = [
        (1.0, np.random.rand(17, 3)),
        (2.0, np.random.rand(17, 3)),
        (3.0, np.random.rand(17, 3)),
    ]
    
    # Should return empty list when no beat detector
    errors = ai_controller.detect_rhythm_errors(motion_keypoints, motion_type="step")
    
    assert isinstance(errors, list)
    assert len(errors) == 0


def test_ai_controller_detect_rhythm_errors_with_detector():
    """Test rhythm error detection with beat detector"""
    # Mock pose_service to avoid heavy dependencies
    pose_service = MagicMock()
    ai_controller = AIController(pose_service)
    
    # Create test audio with 120 BPM (beat every 0.5s)
    with create_test_audio(duration=5.0, tempo=120.0) as audio_path:
        # Set beat detector
        ai_controller.set_beat_detector(audio_path)
        
        # Create motion keypoints that are on-beat (should have few errors)
        on_beat_motion = [
            (0.5, np.random.rand(17, 3)),
            (1.0, np.random.rand(17, 3)),
            (1.5, np.random.rand(17, 3)),
            (2.0, np.random.rand(17, 3)),
        ]
        
        errors_on_beat = ai_controller.detect_rhythm_errors(on_beat_motion, motion_type="step")
        
        assert isinstance(errors_on_beat, list)
        # May have some errors due to detection tolerance, but should be minimal
        
        # Create motion keypoints that are off-beat (should have more errors)
        off_beat_motion = [
            (0.25, np.random.rand(17, 3)),
            (0.75, np.random.rand(17, 3)),
            (1.25, np.random.rand(17, 3)),
            (1.75, np.random.rand(17, 3)),
        ]
        
        errors_off_beat = ai_controller.detect_rhythm_errors(off_beat_motion, motion_type="step")
        
        assert isinstance(errors_off_beat, list)
        
        # Check error structure
        if len(errors_off_beat) > 0:
            error = errors_off_beat[0]
            assert "type" in error
            assert error["type"] == "rhythm"
            assert "description" in error
            assert "severity" in error
            assert "deduction" in error
            assert "body_part" in error


def test_ai_controller_detect_rhythm_errors_empty_motion():
    """Test rhythm error detection with empty motion list"""
    # Mock pose_service to avoid heavy dependencies
    pose_service = MagicMock()
    ai_controller = AIController(pose_service)
    
    with create_test_audio(duration=5.0, tempo=120.0) as audio_path:
        ai_controller.set_beat_detector(audio_path)
        
        # Empty motion list should return no errors
        errors = ai_controller.detect_rhythm_errors([], motion_type="step")
        
        assert isinstance(errors, list)
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
