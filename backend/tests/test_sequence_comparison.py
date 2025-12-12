"""
Tests for sequence-based error detection
"""
import pytest
import numpy as np
from unittest.mock import Mock
from backend.app.services.sequence_comparison import SequenceComparator
from backend.app.controllers.ai_controller import AIController


class TestSequenceComparator:
    """Test SequenceComparator class"""
    
    def test_initialization(self):
        """Test that SequenceComparator initializes with correct parameters"""
        comparator = SequenceComparator(min_sequence_length=5, severity_aggregation="max")
        assert comparator.min_sequence_length == 5
        assert comparator.severity_aggregation == "max"
    
    def test_default_initialization(self):
        """Test default initialization values"""
        comparator = SequenceComparator()
        assert comparator.min_sequence_length == 3
        assert comparator.severity_aggregation == "mean"
    
    def test_group_consecutive_errors(self):
        """Test grouping consecutive errors into sequences"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        # Create 10 consecutive errors of same type
        errors = []
        for i in range(10):
            errors.append({
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        sequences = comparator.group_errors_into_sequences(errors)
        
        # Should have exactly 1 sequence
        assert len(sequences) == 1
        
        # Check sequence properties
        seq = sequences[0]
        assert seq["type"] == "arm_angle"
        assert seq["body_part"] == "arm"
        assert seq["side"] == "left"
        assert seq["start_frame"] == 0
        assert seq["end_frame"] == 9
        assert seq["frame_count"] == 10
        assert seq["is_sequence"] is True
    
    def test_sequence_aggregation_mean(self):
        """Test severity aggregation using mean"""
        comparator = SequenceComparator(min_sequence_length=3, severity_aggregation="mean")
        
        # Create errors with varying severities
        errors = [
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 1.0,
                "deduction": 1.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            }
            for i in range(5)
        ]
        # Set different severities: 1.0, 2.0, 3.0, 4.0, 5.0
        for i, error in enumerate(errors):
            error["severity"] = float(i + 1)
            error["deduction"] = float(i + 1)
        
        sequences = comparator.group_errors_into_sequences(errors)
        
        # Mean severity should be (1+2+3+4+5)/5 = 3.0
        assert len(sequences) == 1
        assert sequences[0]["severity"] == 3.0
    
    def test_sequence_aggregation_max(self):
        """Test severity aggregation using max"""
        comparator = SequenceComparator(min_sequence_length=3, severity_aggregation="max")
        
        # Create errors with varying severities
        errors = [
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": float(i + 1),
                "deduction": float(i + 1),
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            }
            for i in range(5)
        ]
        
        sequences = comparator.group_errors_into_sequences(errors)
        
        # Max severity should be 5.0
        assert len(sequences) == 1
        assert sequences[0]["severity"] == 5.0
    
    def test_sequence_aggregation_median(self):
        """Test severity aggregation using median"""
        comparator = SequenceComparator(min_sequence_length=3, severity_aggregation="median")
        
        # Create errors with varying severities: 1, 2, 3, 4, 5
        errors = [
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": float(i + 1),
                "deduction": float(i + 1),
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            }
            for i in range(5)
        ]
        
        sequences = comparator.group_errors_into_sequences(errors)
        
        # Median severity should be 3.0
        assert len(sequences) == 1
        assert sequences[0]["severity"] == 3.0
    
    def test_isolated_errors_not_grouped(self):
        """Test that isolated errors (< min_sequence_length) are not grouped"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        # Create only 2 consecutive errors (below min_sequence_length of 3)
        errors = [
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": 0,
                "timestamp": 0.0
            },
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": 1,
                "timestamp": 0.033
            }
        ]
        
        sequences = comparator.group_errors_into_sequences(errors)
        
        # Should have 2 individual errors (not grouped into sequence)
        assert len(sequences) == 2
        assert sequences[0]["frame_count"] == 1
        assert sequences[1]["frame_count"] == 1
        assert sequences[0]["is_sequence"] is False
        assert sequences[1]["is_sequence"] is False
    
    def test_multiple_sequences_same_type(self):
        """Test handling multiple sequences of same error type separated by gaps"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        errors = []
        # First sequence: frames 0-4
        for i in range(5):
            errors.append({
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        # Gap: frames 5-9 (no errors)
        
        # Second sequence: frames 10-14
        for i in range(10, 15):
            errors.append({
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        sequences = comparator.group_errors_into_sequences(errors)
        
        # Should have 2 separate sequences
        assert len(sequences) == 2
        assert sequences[0]["start_frame"] == 0
        assert sequences[0]["end_frame"] == 4
        assert sequences[1]["start_frame"] == 10
        assert sequences[1]["end_frame"] == 14
    
    def test_different_error_types_separate_sequences(self):
        """Test that different error types are grouped separately"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        errors = []
        # Arm errors: frames 0-4
        for i in range(5):
            errors.append({
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        # Leg errors: frames 0-4 (same frames but different type)
        for i in range(5):
            errors.append({
                "type": "leg_angle",
                "description": "Chân phải quá thấp",
                "severity": 1.5,
                "deduction": 1.5,
                "body_part": "leg",
                "side": "right",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        sequences = comparator.group_errors_into_sequences(errors)
        
        # Should have 2 separate sequences (one for arm, one for leg)
        assert len(sequences) == 2
        types = {seq["type"] for seq in sequences}
        assert "arm_angle" in types
        assert "leg_angle" in types
    
    def test_different_sides_separate_sequences(self):
        """Test that errors on different sides (left/right) are grouped separately"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        errors = []
        # Left arm errors: frames 0-4
        for i in range(5):
            errors.append({
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        # Right arm errors: frames 0-4 (same frames but different side)
        for i in range(5):
            errors.append({
                "type": "arm_angle",
                "description": "Tay phải quá cao",
                "severity": 1.5,
                "deduction": 1.5,
                "body_part": "arm",
                "side": "right",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        sequences = comparator.group_errors_into_sequences(errors)
        
        # Should have 2 separate sequences (one for left, one for right)
        assert len(sequences) == 2
        sides = {seq["side"] for seq in sequences}
        assert "left" in sides
        assert "right" in sides
    
    def test_empty_errors_list(self):
        """Test handling empty errors list"""
        comparator = SequenceComparator()
        sequences = comparator.group_errors_into_sequences([])
        assert sequences == []
    
    def test_single_error(self):
        """Test handling single error"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        errors = [{
            "type": "arm_angle",
            "description": "Tay trái quá cao",
            "severity": 2.0,
            "deduction": 2.0,
            "body_part": "arm",
            "side": "left",
            "frame_number": 0,
            "timestamp": 0.0
        }]
        
        sequences = comparator.group_errors_into_sequences(errors)
        
        # Single error should remain as individual error
        assert len(sequences) == 1
        assert sequences[0]["frame_count"] == 1
        assert sequences[0]["is_sequence"] is False
    
    def test_unsorted_errors_are_sorted(self):
        """Test that unsorted errors are properly sorted before grouping"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        # Create errors in random order
        errors = [
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": 4,
                "timestamp": 4 * 0.033
            },
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": 0,
                "timestamp": 0.0
            },
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": 2,
                "timestamp": 2 * 0.033
            },
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": 1,
                "timestamp": 1 * 0.033
            },
            {
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 2.0,
                "body_part": "arm",
                "side": "left",
                "frame_number": 3,
                "timestamp": 3 * 0.033
            }
        ]
        
        sequences = comparator.group_errors_into_sequences(errors)
        
        # Should form one sequence despite unsorted input
        assert len(sequences) == 1
        assert sequences[0]["start_frame"] == 0
        assert sequences[0]["end_frame"] == 4
        assert sequences[0]["frame_count"] == 5


class TestAIControllerSequenceProcessing:
    """Test AIController integration with sequence comparison"""
    
    def test_process_video_sequence_basic(self):
        """Test basic video sequence processing"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # Create 600 consecutive errors (simulating persistent error)
        frame_errors = []
        for i in range(600):
            frame_errors.append({
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 0.5,  # 0.5 points per frame
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        result = controller.process_video_sequence(frame_errors)
        
        # Should group into 1 sequence
        assert result["sequence_count"] == 1
        assert result["original_error_count"] == 600
        
        # Total deduction should be much less than 600 * 0.5 = 300
        assert result["total_deduction"] < 300
        # With mean aggregation, severity stays ~2.0, so deduction should be ~0.5 * weight
        assert result["total_deduction"] < 10  # Much better than 300!
    
    def test_process_video_sequence_multiple_types(self):
        """Test sequence processing with multiple error types"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        frame_errors = []
        # Arm errors: frames 0-99
        for i in range(100):
            frame_errors.append({
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 0.5,
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        # Leg errors: frames 50-149 (overlapping)
        for i in range(50, 150):
            frame_errors.append({
                "type": "leg_angle",
                "description": "Chân phải quá thấp",
                "severity": 1.5,
                "deduction": 0.4,
                "body_part": "leg",
                "side": "right",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        result = controller.process_video_sequence(frame_errors)
        
        # Should have 2 sequences (one for arm, one for leg)
        assert result["sequence_count"] == 2
        assert result["original_error_count"] == 200  # 100 arm + 100 leg
        
        # Total deduction should be much less than individual frame penalties
        assert result["total_deduction"] < 200 * 0.5  # Much better!
    
    def test_process_video_sequence_with_gaps(self):
        """Test sequence processing with gaps between errors"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        frame_errors = []
        # First sequence: frames 0-9
        for i in range(10):
            frame_errors.append({
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 0.5,
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        # Gap: frames 10-19
        
        # Second sequence: frames 20-29
        for i in range(20, 30):
            frame_errors.append({
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 0.5,
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        result = controller.process_video_sequence(frame_errors)
        
        # Should have 2 sequences (separated by gap)
        assert result["sequence_count"] == 2
        assert result["original_error_count"] == 20
    
    def test_process_video_sequence_disabled(self):
        """Test that sequence processing can be disabled via config"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        # Temporarily disable sequence comparison
        from backend.app import config
        original_config = config.SEQUENCE_COMPARISON_CONFIG.copy()
        config.SEQUENCE_COMPARISON_CONFIG["enabled"] = False
        
        try:
            frame_errors = []
            for i in range(10):
                frame_errors.append({
                    "type": "arm_angle",
                    "description": "Tay trái quá cao",
                    "severity": 2.0,
                    "deduction": 0.5,
                    "body_part": "arm",
                    "side": "left",
                    "frame_number": i,
                    "timestamp": i * 0.033
                })
            
            result = controller.process_video_sequence(frame_errors)
            
            # When disabled, should return all errors without grouping
            assert result["sequence_count"] == 10
            assert result["original_error_count"] == 10
        finally:
            # Restore original config
            config.SEQUENCE_COMPARISON_CONFIG.update(original_config)
    
    def test_process_video_sequence_empty(self):
        """Test handling empty frame errors"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        result = controller.process_video_sequence([])
        
        assert result["sequence_count"] == 0
        assert result["original_error_count"] == 0
        assert result["total_deduction"] == 0.0
    
    def test_process_video_sequence_returns_sequences(self):
        """Test that process_video_sequence returns proper sequence objects"""
        mock_pose_service = Mock()
        controller = AIController(mock_pose_service)
        
        frame_errors = []
        for i in range(5):
            frame_errors.append({
                "type": "arm_angle",
                "description": "Tay trái quá cao",
                "severity": 2.0,
                "deduction": 0.5,
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "timestamp": i * 0.033
            })
        
        result = controller.process_video_sequence(frame_errors)
        
        # Check that sequences are returned
        assert "sequences" in result
        assert isinstance(result["sequences"], list)
        assert len(result["sequences"]) == 1
        
        # Check sequence structure
        seq = result["sequences"][0]
        assert "type" in seq
        assert "severity" in seq
        assert "deduction" in seq
        assert "start_frame" in seq
        assert "end_frame" in seq
        assert "frame_count" in seq
