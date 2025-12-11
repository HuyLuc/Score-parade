"""
Integration tests for AIController with temporal smoothing
"""
import pytest
import numpy as np
from unittest.mock import Mock
from backend.app.controllers.ai_controller import AIController
from backend.app.config import KEYPOINT_INDICES


def create_test_keypoints(arm_angle_offset=0, scale=1.0):
    """
    Create test keypoints with known positions
    
    Args:
        arm_angle_offset: Offset for arm position (simulates different poses)
        scale: Scale factor for keypoint positions
    """
    keypoints = np.zeros((17, 3))
    keypoints[:, 2] = 0.9  # Set confidence
    
    # Shoulders
    keypoints[KEYPOINT_INDICES["left_shoulder"]] = [80*scale, 100*scale, 0.9]
    keypoints[KEYPOINT_INDICES["right_shoulder"]] = [120*scale, 100*scale, 0.9]
    
    # Elbows
    keypoints[KEYPOINT_INDICES["left_elbow"]] = [60*scale, (150+arm_angle_offset)*scale, 0.9]
    keypoints[KEYPOINT_INDICES["right_elbow"]] = [140*scale, (150+arm_angle_offset)*scale, 0.9]
    
    # Wrists
    keypoints[KEYPOINT_INDICES["left_wrist"]] = [50*scale, (200+arm_angle_offset)*scale, 0.9]
    keypoints[KEYPOINT_INDICES["right_wrist"]] = [150*scale, (200+arm_angle_offset)*scale, 0.9]
    
    # Hips
    keypoints[KEYPOINT_INDICES["left_hip"]] = [80*scale, 250*scale, 0.9]
    keypoints[KEYPOINT_INDICES["right_hip"]] = [120*scale, 250*scale, 0.9]
    
    # Knees
    keypoints[KEYPOINT_INDICES["left_knee"]] = [80*scale, 350*scale, 0.9]
    keypoints[KEYPOINT_INDICES["right_knee"]] = [120*scale, 350*scale, 0.9]
    
    # Ankles
    keypoints[KEYPOINT_INDICES["left_ankle"]] = [80*scale, 450*scale, 0.9]
    keypoints[KEYPOINT_INDICES["right_ankle"]] = [120*scale, 450*scale, 0.9]
    
    # Nose (for head angle)
    keypoints[KEYPOINT_INDICES["nose"]] = [100*scale, 50*scale, 0.9]
    
    # Eyes
    keypoints[KEYPOINT_INDICES["left_eye"]] = [95*scale, 45*scale, 0.9]
    keypoints[KEYPOINT_INDICES["right_eye"]] = [105*scale, 45*scale, 0.9]
    
    return keypoints


class TestAIControllerSmoothing:
    """Integration tests for AIController with temporal smoothing"""
    
    def test_smoothing_enabled_initialization(self):
        """Test that AIController initializes smoothers when enabled"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # Check that smoothers are initialized
        assert controller.keypoint_smoother is not None
        assert controller.metric_smoothers is not None
        assert "arm_angle_left" in controller.metric_smoothers
        assert "arm_angle_right" in controller.metric_smoothers
        assert "leg_angle_left" in controller.metric_smoothers
        assert "leg_angle_right" in controller.metric_smoothers
        assert "head_angle" in controller.metric_smoothers
    
    def test_reset_smoothers(self):
        """Test that reset_smoothers clears all buffers"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # Add some data
        kp = create_test_keypoints()
        controller.detect_posture_errors(kp, frame_number=0)
        
        # Reset
        controller.reset_smoothers()
        
        # Check that buffers are empty
        assert controller.keypoint_smoother.get_smoothed_keypoints() is None
        for smoother in controller.metric_smoothers.values():
            assert smoother.get_smoothed_value() is None
    
    def test_smoothing_reduces_noise_spikes(self):
        """Test that smoothing reduces impact of noise spikes on error detection"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # Create keypoints with a noise spike
        normal_kp = create_test_keypoints(arm_angle_offset=0)
        spike_kp = create_test_keypoints(arm_angle_offset=100)  # Large spike
        
        # Feed frames with spike in the middle
        controller.detect_posture_errors(normal_kp, frame_number=0)
        controller.detect_posture_errors(normal_kp, frame_number=1)
        controller.detect_posture_errors(spike_kp, frame_number=2)  # Spike!
        controller.detect_posture_errors(normal_kp, frame_number=3)
        errors = controller.detect_posture_errors(normal_kp, frame_number=4)
        
        # With smoothing, the spike should be dampened
        # We expect fewer or less severe errors compared to without smoothing
        # (Without golden template, this test mainly verifies no crashes)
        assert isinstance(errors, list)
    
    def test_smoothing_with_consistent_motion(self):
        """Test that smoothing works with consistent motion"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # Create sequence of keypoints with gradual change
        for i in range(10):
            kp = create_test_keypoints(arm_angle_offset=i*2)
            errors = controller.detect_posture_errors(kp, frame_number=i)
            assert isinstance(errors, list)
    
    def test_detect_posture_errors_with_smoothing(self):
        """Test basic error detection with smoothing enabled"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        kp = create_test_keypoints()
        errors = controller.detect_posture_errors(kp, frame_number=0)
        
        # Should return a list (empty or with errors)
        assert isinstance(errors, list)
        
        # All errors should have required fields
        for error in errors:
            assert "type" in error
            assert "description" in error
            assert "severity" in error
            assert "deduction" in error
            assert "body_part" in error
            assert "frame_number" in error
            assert "timestamp" in error
    
    def test_smoothing_accumulates_across_frames(self):
        """Test that smoothing accumulates data across multiple frames"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # Process multiple frames
        for i in range(5):
            kp = create_test_keypoints()
            controller.detect_posture_errors(kp, frame_number=i)
        
        # Smoothers should be ready (full window)
        assert controller.keypoint_smoother.is_ready()
        for smoother in controller.metric_smoothers.values():
            # Not all smoothers may have values if keypoints don't allow calculation
            # Just check they exist
            assert smoother is not None
    
    def test_smoothing_with_none_values(self):
        """Test that smoothing handles None values gracefully"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # Create keypoints with low confidence (may result in None angles)
        kp = create_test_keypoints()
        kp[:, 2] = 0.1  # Very low confidence
        
        # Should not crash
        errors = controller.detect_posture_errors(kp, frame_number=0)
        assert isinstance(errors, list)
    
    def test_smoothed_methods_exist(self):
        """Test that smoothed posture checking methods exist"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # Verify methods exist
        assert hasattr(controller, '_check_arm_posture_smoothed')
        assert hasattr(controller, '_check_leg_posture_smoothed')
        assert hasattr(controller, '_check_head_posture_smoothed')
        assert hasattr(controller, 'reset_smoothers')
        
        # Verify they're callable
        kp = create_test_keypoints()
        arm_errors = controller._check_arm_posture_smoothed(kp)
        leg_errors = controller._check_leg_posture_smoothed(kp)
        head_errors = controller._check_head_posture_smoothed(kp)
        
        assert isinstance(arm_errors, list)
        assert isinstance(leg_errors, list)
        assert isinstance(head_errors, list)


class TestSmoothingIntegration:
    """Higher-level integration tests"""
    
    def test_window_fills_gradually(self):
        """Test that smoothing window fills gradually"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # Initially not ready
        assert not controller.keypoint_smoother.is_ready()
        
        # Add frames one by one
        for i in range(5):
            kp = create_test_keypoints()
            controller.detect_posture_errors(kp, frame_number=i)
            
            if i < 4:
                assert not controller.keypoint_smoother.is_ready()
            else:
                assert controller.keypoint_smoother.is_ready()
    
    def test_multiple_sessions_with_reset(self):
        """Test that reset allows for clean new session"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # First session
        for i in range(5):
            kp = create_test_keypoints(arm_angle_offset=10)
            controller.detect_posture_errors(kp, frame_number=i)
        
        assert controller.keypoint_smoother.is_ready()
        
        # Reset for new session
        controller.reset_smoothers()
        assert not controller.keypoint_smoother.is_ready()
        
        # Second session with different data
        for i in range(5):
            kp = create_test_keypoints(arm_angle_offset=20)
            controller.detect_posture_errors(kp, frame_number=i)
        
        assert controller.keypoint_smoother.is_ready()
