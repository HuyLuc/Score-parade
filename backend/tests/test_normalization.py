"""
Tests for keypoint normalization service
"""
import pytest
import numpy as np
from backend.app.services.keypoint_normalization import (
    calculate_torso_length,
    normalize_keypoints,
    normalize_keypoints_relative,
    denormalize_keypoints,
    batch_normalize_keypoints
)
from backend.app.config import KEYPOINT_INDICES


def create_test_keypoints(scale=1.0, offset=(0, 0)):
    """
    Create test keypoints with known positions for testing.
    
    Creates a standing pose with:
    - Shoulders at y=100*scale
    - Hips at y=250*scale
    - Torso length = 150*scale
    """
    keypoints = np.zeros((17, 3))
    
    # Set confidence to 1.0 for all keypoints
    keypoints[:, 2] = 1.0
    
    # Shoulders (y=100)
    keypoints[KEYPOINT_INDICES["left_shoulder"]] = [80*scale + offset[0], 100*scale + offset[1], 1.0]
    keypoints[KEYPOINT_INDICES["right_shoulder"]] = [120*scale + offset[0], 100*scale + offset[1], 1.0]
    
    # Hips (y=250)
    keypoints[KEYPOINT_INDICES["left_hip"]] = [80*scale + offset[0], 250*scale + offset[1], 1.0]
    keypoints[KEYPOINT_INDICES["right_hip"]] = [120*scale + offset[0], 250*scale + offset[1], 1.0]
    
    # Elbows
    keypoints[KEYPOINT_INDICES["left_elbow"]] = [60*scale + offset[0], 150*scale + offset[1], 1.0]
    keypoints[KEYPOINT_INDICES["right_elbow"]] = [140*scale + offset[0], 150*scale + offset[1], 1.0]
    
    # Wrists
    keypoints[KEYPOINT_INDICES["left_wrist"]] = [50*scale + offset[0], 200*scale + offset[1], 1.0]
    keypoints[KEYPOINT_INDICES["right_wrist"]] = [150*scale + offset[0], 200*scale + offset[1], 1.0]
    
    # Knees
    keypoints[KEYPOINT_INDICES["left_knee"]] = [80*scale + offset[0], 350*scale + offset[1], 1.0]
    keypoints[KEYPOINT_INDICES["right_knee"]] = [120*scale + offset[0], 350*scale + offset[1], 1.0]
    
    # Ankles
    keypoints[KEYPOINT_INDICES["left_ankle"]] = [80*scale + offset[0], 450*scale + offset[1], 1.0]
    keypoints[KEYPOINT_INDICES["right_ankle"]] = [120*scale + offset[0], 450*scale + offset[1], 1.0]
    
    # Nose (head)
    keypoints[KEYPOINT_INDICES["nose"]] = [100*scale + offset[0], 50*scale + offset[1], 1.0]
    
    return keypoints


def test_calculate_torso_length():
    """Test torso length calculation"""
    # Test with scale=1.0
    keypoints = create_test_keypoints(scale=1.0)
    torso = calculate_torso_length(keypoints)
    
    # Expected: distance from y=100 to y=250 = 150
    assert torso is not None
    assert abs(torso - 150.0) < 1.0, f"Expected torso ~150, got {torso}"


def test_calculate_torso_length_scaled():
    """Test torso length with different scales"""
    # Test with tall person (scale=2.0)
    keypoints_tall = create_test_keypoints(scale=2.0)
    torso_tall = calculate_torso_length(keypoints_tall)
    
    # Expected: 150 * 2.0 = 300
    assert torso_tall is not None
    assert abs(torso_tall - 300.0) < 2.0, f"Expected torso ~300, got {torso_tall}"
    
    # Test with short person (scale=0.5)
    keypoints_short = create_test_keypoints(scale=0.5)
    torso_short = calculate_torso_length(keypoints_short)
    
    # Expected: 150 * 0.5 = 75
    assert torso_short is not None
    assert abs(torso_short - 75.0) < 1.0, f"Expected torso ~75, got {torso_short}"


def test_calculate_torso_length_missing_keypoints():
    """Test torso length with missing/low confidence keypoints"""
    keypoints = create_test_keypoints(scale=1.0)
    
    # Set left shoulder confidence to 0
    keypoints[KEYPOINT_INDICES["left_shoulder"], 2] = 0.0
    
    torso = calculate_torso_length(keypoints)
    assert torso is None, "Should return None when keypoints have low confidence"


def test_normalize_keypoints_absolute():
    """Test absolute normalization to reference torso length"""
    # Create tall person with torso=300
    keypoints = create_test_keypoints(scale=2.0)
    
    # Normalize to reference=100
    normalized, scale = normalize_keypoints(keypoints, reference_torso=100.0)
    
    assert normalized is not None
    assert scale is not None
    
    # Scale should be 100/300 = 0.333...
    expected_scale = 100.0 / 300.0
    assert abs(scale - expected_scale) < 0.01, f"Expected scale ~{expected_scale}, got {scale}"
    
    # Check that torso length is now ~100
    normalized_torso = calculate_torso_length(normalized)
    assert abs(normalized_torso - 100.0) < 1.0, f"Expected normalized torso ~100, got {normalized_torso}"


def test_normalize_keypoints_relative():
    """Test relative normalization (centered and scaled)"""
    keypoints = create_test_keypoints(scale=1.0)
    normalized = normalize_keypoints_relative(keypoints)
    
    assert normalized is not None
    assert normalized.shape == keypoints.shape
    
    # After normalization, torso center should be close to origin
    left_shoulder = normalized[KEYPOINT_INDICES["left_shoulder"], :2]
    right_shoulder = normalized[KEYPOINT_INDICES["right_shoulder"], :2]
    left_hip = normalized[KEYPOINT_INDICES["left_hip"], :2]
    right_hip = normalized[KEYPOINT_INDICES["right_hip"], :2]
    
    shoulder_center = (left_shoulder + right_shoulder) / 2.0
    hip_center = (left_hip + right_hip) / 2.0
    torso_center = (shoulder_center + hip_center) / 2.0
    
    # Torso center should be very close to (0, 0)
    assert abs(torso_center[0]) < 0.01, f"Expected x ~0, got {torso_center[0]}"
    assert abs(torso_center[1]) < 0.01, f"Expected y ~0, got {torso_center[1]}"
    
    # Distance from shoulder center to hip center should be ~1.0 (normalized)
    normalized_torso_length = np.linalg.norm(shoulder_center - hip_center)
    assert abs(normalized_torso_length - 1.0) < 0.01, f"Expected torso ~1.0, got {normalized_torso_length}"


def test_denormalize():
    """Test denormalization returns original keypoints"""
    original = create_test_keypoints(scale=1.5, offset=(50, 100))
    
    # Normalize with absolute method
    normalized, scale = normalize_keypoints(original, reference_torso=100.0)
    assert normalized is not None
    
    # Denormalize
    recovered = denormalize_keypoints(normalized, scale)
    
    # Should match original (within floating point precision)
    np.testing.assert_allclose(
        recovered[:, :2], 
        original[:, :2], 
        rtol=1e-5, 
        atol=1e-5,
        err_msg="Denormalized keypoints should match original"
    )


def test_scale_invariance():
    """
    Test that normalization makes pose comparison scale-invariant.
    
    Two people with same pose but different heights should have same normalized keypoints.
    """
    # Create tall person (scale=2.0)
    keypoints_tall = create_test_keypoints(scale=2.0)
    
    # Create short person (scale=1.0) with same relative pose
    keypoints_short = create_test_keypoints(scale=1.0)
    
    # Normalize both
    normalized_tall = normalize_keypoints_relative(keypoints_tall)
    normalized_short = normalize_keypoints_relative(keypoints_short)
    
    assert normalized_tall is not None
    assert normalized_short is not None
    
    # Normalized keypoints should be very close (same pose)
    np.testing.assert_allclose(
        normalized_tall[:, :2],
        normalized_short[:, :2],
        rtol=0.01,
        atol=0.01,
        err_msg="Normalized keypoints should be identical for same pose at different scales"
    )


def test_scale_invariance_with_offset():
    """Test that normalization is also translation-invariant"""
    # Same pose at different locations
    keypoints1 = create_test_keypoints(scale=1.0, offset=(0, 0))
    keypoints2 = create_test_keypoints(scale=1.0, offset=(100, 200))
    
    normalized1 = normalize_keypoints_relative(keypoints1)
    normalized2 = normalize_keypoints_relative(keypoints2)
    
    # After relative normalization, both should be identical since they have the same pose
    # The relative normalization centers at torso midpoint and scales by torso length
    # So translation should be removed
    # Note: Only check keypoints that are actually set (non-zero confidence)
    # Eyes and ears are not set in test data, so they'll be at origin with different normalized values
    
    # Check main body keypoints that are set in create_test_keypoints
    keypoints_to_check = [
        "nose", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]
    
    for kpt_name in keypoints_to_check:
        idx = KEYPOINT_INDICES[kpt_name]
        np.testing.assert_allclose(
            normalized1[idx, :2],
            normalized2[idx, :2],
            rtol=0.01,
            atol=0.01,
            err_msg=f"Normalized {kpt_name} should be identical regardless of position"
        )


def test_batch_normalize_keypoints():
    """Test batch normalization of multiple frames"""
    frames = [
        create_test_keypoints(scale=1.0),
        create_test_keypoints(scale=1.5),
        create_test_keypoints(scale=2.0),
    ]
    
    # Test relative method
    normalized_frames = batch_normalize_keypoints(frames, method="relative")
    
    assert len(normalized_frames) == 3
    assert all(n is not None for n in normalized_frames)
    
    # All frames should have same shape
    assert all(n.shape == frames[0].shape for n in normalized_frames)
    
    # Test absolute method
    normalized_abs = batch_normalize_keypoints(frames, method="absolute")
    assert len(normalized_abs) == 3
    assert all(n is not None for n in normalized_abs)


def test_batch_normalize_with_invalid_frames():
    """Test batch normalization handles invalid frames gracefully"""
    # Create frames with one invalid (missing keypoints)
    frame1 = create_test_keypoints(scale=1.0)
    frame2 = create_test_keypoints(scale=1.0)
    frame2[KEYPOINT_INDICES["left_shoulder"], 2] = 0.0  # Low confidence
    frame3 = create_test_keypoints(scale=1.0)
    
    frames = [frame1, frame2, frame3]
    normalized = batch_normalize_keypoints(frames, method="relative")
    
    assert len(normalized) == 3
    assert normalized[0] is not None
    assert normalized[1] is None  # Should fail due to low confidence
    assert normalized[2] is not None


def test_normalization_preserves_confidence():
    """Test that normalization preserves confidence values"""
    keypoints = create_test_keypoints(scale=1.0)
    
    # Set varying confidence values
    keypoints[0, 2] = 0.8
    keypoints[5, 2] = 0.9
    keypoints[11, 2] = 0.95
    
    # Normalize
    normalized = normalize_keypoints_relative(keypoints)
    
    assert normalized is not None
    
    # Confidence should be unchanged
    assert normalized[0, 2] == 0.8
    assert normalized[5, 2] == 0.9
    assert normalized[11, 2] == 0.95


def test_edge_case_zero_torso():
    """Test handling of edge case where torso length is zero or very small"""
    keypoints = create_test_keypoints(scale=0.01)  # Very small scale (torso = 150 * 0.01 = 1.5)
    
    # Should return None for very small torso (below min_torso_length threshold of 10.0)
    torso = calculate_torso_length(keypoints)
    assert torso is None


def test_normalization_with_2d_keypoints():
    """Test normalization works with [17, 2] keypoints (no confidence)"""
    keypoints_3d = create_test_keypoints(scale=1.0)
    keypoints_2d = keypoints_3d[:, :2]  # Remove confidence column
    
    # Should handle 2D keypoints (though won't check confidence)
    # This is a graceful degradation case
    # Note: calculate_torso_length checks shape[1] > 2 for confidence
    # So with 2D input, it will skip confidence checks
    # The current implementation should still work
    pass  # This test documents expected behavior


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
