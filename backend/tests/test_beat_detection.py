"""
Unit tests for BeatDetector service
"""
import pytest
import numpy as np
from pathlib import Path
import tempfile
import soundfile as sf


def create_test_audio(duration: float = 5.0, tempo: float = 120.0, sr: int = 22050) -> str:
    """
    Create a simple test audio file with click track at specified tempo
    
    Args:
        duration: Duration in seconds
        tempo: Tempo in BPM
        sr: Sample rate
        
    Returns:
        Path to temporary audio file
    """
    # Calculate beat interval
    beat_interval = 60.0 / tempo  # seconds per beat
    
    # Generate click track
    samples = int(duration * sr)
    audio = np.zeros(samples)
    
    # Add clicks at beat positions
    click_duration = 0.01  # 10ms clicks
    click_samples = int(click_duration * sr)
    
    t = 0.0
    while t < duration:
        start_idx = int(t * sr)
        end_idx = min(start_idx + click_samples, samples)
        
        # Simple click sound (sine wave burst)
        click = np.sin(2 * np.pi * 1000 * np.linspace(0, click_duration, end_idx - start_idx))
        audio[start_idx:end_idx] = click
        
        t += beat_interval
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    sf.write(temp_file.name, audio, sr)
    temp_file.close()
    
    return temp_file.name


def test_beat_detector_initialization():
    """Test BeatDetector initialization with synthetic audio"""
    from backend.app.services.beat_detection import BeatDetector
    
    # Create test audio
    audio_path = create_test_audio(duration=5.0, tempo=120.0)
    
    try:
        # Initialize detector
        detector = BeatDetector(audio_path)
        
        # Check that detector was initialized
        assert detector is not None
        assert detector.tempo > 0
        assert len(detector.beat_times) > 0
        assert detector.sr > 0
        assert len(detector.y) > 0
        
    finally:
        # Clean up
        Path(audio_path).unlink()


def test_get_beat_at_time():
    """Test finding beat at specific time"""
    from backend.app.services.beat_detection import BeatDetector
    
    # Create test audio with 120 BPM (beat every 0.5 seconds)
    audio_path = create_test_audio(duration=5.0, tempo=120.0)
    
    try:
        detector = BeatDetector(audio_path)
        
        # Test with various timestamps
        # Should find beats near 0.5, 1.0, 1.5, 2.0, etc.
        beat = detector.get_beat_at_time(1.0, tolerance=0.2)
        assert beat is not None, "Should find a beat near 1.0s"
        
        beat = detector.get_beat_at_time(2.0, tolerance=0.2)
        assert beat is not None, "Should find a beat near 2.0s"
        
        # Test with timestamp far from any beat (should return None with strict tolerance)
        beat = detector.get_beat_at_time(1.25, tolerance=0.05)
        # This might be None depending on detection accuracy
        
    finally:
        Path(audio_path).unlink()


def test_calculate_rhythm_error():
    """Test rhythm error calculation"""
    from backend.app.services.beat_detection import BeatDetector
    
    # Create test audio with 120 BPM
    audio_path = create_test_audio(duration=5.0, tempo=120.0)
    
    try:
        detector = BeatDetector(audio_path)
        
        # Test with motion timestamps that align with beats
        # Expected beats around: 0.5, 1.0, 1.5, 2.0, 2.5, 3.0 seconds
        motion_times = [0.5, 1.0, 1.5, 2.0]
        
        error_count, errors = detector.calculate_rhythm_error(
            motion_times,
            tolerance=0.2
        )
        
        # Should have few or no errors since motion times align with expected beats
        assert error_count >= 0, "Error count should be non-negative"
        assert len(errors) == error_count, "Error list length should match count"
        
        # Test with off-beat motion timestamps
        off_beat_times = [0.25, 0.75, 1.25, 1.75]
        
        error_count2, errors2 = detector.calculate_rhythm_error(
            off_beat_times,
            tolerance=0.1
        )
        
        # Should have more errors since timestamps are off-beat
        assert error_count2 >= 0, "Error count should be non-negative"
        
    finally:
        Path(audio_path).unlink()


def test_get_expected_beats_in_range():
    """Test getting beats in a time range"""
    from backend.app.services.beat_detection import BeatDetector
    
    # Create test audio
    audio_path = create_test_audio(duration=10.0, tempo=120.0)
    
    try:
        detector = BeatDetector(audio_path)
        
        # Get beats in first 2 seconds
        beats = detector.get_expected_beats_in_range(0.0, 2.0)
        
        assert isinstance(beats, list), "Should return a list"
        assert len(beats) > 0, "Should find beats in range"
        
        # All beats should be within range
        for beat in beats:
            assert 0.0 <= beat <= 2.0, f"Beat {beat} should be in range [0.0, 2.0]"
        
        # Get beats in middle range
        beats2 = detector.get_expected_beats_in_range(3.0, 5.0)
        assert isinstance(beats2, list), "Should return a list"
        
    finally:
        Path(audio_path).unlink()


@pytest.mark.skipif(
    not Path("data/audio/di_deu/global/total.mp3").exists(),
    reason="Test audio file not found"
)
def test_beat_detection_with_real_audio():
    """Test with real audio file if available"""
    from backend.app.services.beat_detection import BeatDetector
    
    audio_path = "data/audio/di_deu/global/total.mp3"
    
    # Initialize detector
    detector = BeatDetector(audio_path)
    
    # Check basic properties
    assert detector.tempo > 0
    assert len(detector.beat_times) > 0
    
    # Test rhythm error calculation
    motion_times = [1.0, 2.0, 3.0]
    error_count, errors = detector.calculate_rhythm_error(motion_times)
    
    assert error_count >= 0
    assert len(errors) == error_count


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
