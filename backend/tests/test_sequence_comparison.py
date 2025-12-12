"""
Tests for sequence comparison service
"""
import pytest
from backend.app.services.sequence_comparison import SequenceComparator


class TestSequenceComparator:
    """Test SequenceComparator class"""
    
    def test_init_default_params(self):
        """Test initialization with default parameters"""
        comparator = SequenceComparator()
        assert comparator.min_sequence_length == 3
        assert comparator.severity_aggregation == "mean"
        assert comparator.enabled is True
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        comparator = SequenceComparator(
            min_sequence_length=5,
            severity_aggregation="max",
            enabled=False
        )
        assert comparator.min_sequence_length == 5
        assert comparator.severity_aggregation == "max"
        assert comparator.enabled is False
    
    def test_init_invalid_aggregation_method(self):
        """Test that invalid aggregation method raises ValueError"""
        with pytest.raises(ValueError, match="Invalid severity_aggregation"):
            SequenceComparator(severity_aggregation="invalid")
    
    def test_group_consecutive_errors(self):
        """Test grouping consecutive errors of the same type"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        # Create 5 consecutive arm_angle errors (left side)
        frame_errors = []
        for i in range(5):
            frame_errors.append({
                "type": "arm_angle",
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "severity": 2.0,
                "deduction": 2.0,
                "description": f"Arm angle error at frame {i}"
            })
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        # Should group into 1 sequence (5 frames >= min 3)
        assert len(sequences) == 1
        assert sequences[0]["is_sequence"] is True
        assert sequences[0]["start_frame"] == 0
        assert sequences[0]["end_frame"] == 4
        assert sequences[0]["sequence_length"] == 5
        assert sequences[0]["type"] == "arm_angle"
        assert sequences[0]["body_part"] == "arm"
        assert sequences[0]["side"] == "left"
    
    def test_sequence_breaks_on_different_type(self):
        """Test that sequences break when error type changes"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        frame_errors = [
            # First sequence: arm_angle (frames 0-2)
            {"type": "arm_angle", "body_part": "arm", "side": "left", 
             "frame_number": 0, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 1, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 2, "severity": 2.0, "deduction": 2.0},
            # Second sequence: leg_angle (frames 3-5) - different type breaks sequence
            {"type": "leg_angle", "body_part": "leg", "side": "right",
             "frame_number": 3, "severity": 1.5, "deduction": 1.5},
            {"type": "leg_angle", "body_part": "leg", "side": "right",
             "frame_number": 4, "severity": 1.5, "deduction": 1.5},
            {"type": "leg_angle", "body_part": "leg", "side": "right",
             "frame_number": 5, "severity": 1.5, "deduction": 1.5},
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        # Should create 2 sequences
        assert len(sequences) == 2
        
        # First sequence
        assert sequences[0]["type"] == "arm_angle"
        assert sequences[0]["start_frame"] == 0
        assert sequences[0]["end_frame"] == 2
        
        # Second sequence
        assert sequences[1]["type"] == "leg_angle"
        assert sequences[1]["start_frame"] == 3
        assert sequences[1]["end_frame"] == 5
    
    def test_sequence_breaks_on_different_side(self):
        """Test that sequences break when side changes"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        frame_errors = [
            # Left arm errors (frames 0-2)
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 0, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 1, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 2, "severity": 2.0, "deduction": 2.0},
            # Right arm errors (frames 3-5) - different side breaks sequence
            {"type": "arm_angle", "body_part": "arm", "side": "right",
             "frame_number": 3, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "right",
             "frame_number": 4, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "right",
             "frame_number": 5, "severity": 2.0, "deduction": 2.0},
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        # Should create 2 sequences (different sides)
        assert len(sequences) == 2
        assert sequences[0]["side"] == "left"
        assert sequences[1]["side"] == "right"
    
    def test_sequence_breaks_on_gap(self):
        """Test that sequences break when frames are not consecutive"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        frame_errors = [
            # First group (frames 0-2)
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 0, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 1, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 2, "severity": 2.0, "deduction": 2.0},
            # Gap! Frame 3 missing
            # Second group (frames 4-6)
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 4, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 5, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 6, "severity": 2.0, "deduction": 2.0},
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        # Should create 2 sequences due to gap
        assert len(sequences) == 2
        assert sequences[0]["end_frame"] == 2
        assert sequences[1]["start_frame"] == 4
    
    def test_isolated_errors_not_grouped(self):
        """Test that isolated errors (< min_sequence_length) are not grouped"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        frame_errors = [
            # Only 2 consecutive errors (< min 3)
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 0, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 1, "severity": 2.0, "deduction": 2.0},
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        # Should return original errors (not grouped)
        assert len(sequences) == 2
        assert "is_sequence" not in sequences[0]
        assert "is_sequence" not in sequences[1]
    
    def test_severity_aggregation_mean(self):
        """Test mean aggregation of severity"""
        comparator = SequenceComparator(
            min_sequence_length=3,
            severity_aggregation="mean"
        )
        
        frame_errors = [
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 0, "severity": 1.0, "deduction": 1.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 1, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 2, "severity": 3.0, "deduction": 3.0},
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        assert len(sequences) == 1
        # Mean of [1.0, 2.0, 3.0] = 2.0
        assert sequences[0]["severity"] == 2.0
        assert sequences[0]["deduction"] == 2.0
    
    def test_severity_aggregation_max(self):
        """Test max aggregation of severity"""
        comparator = SequenceComparator(
            min_sequence_length=3,
            severity_aggregation="max"
        )
        
        frame_errors = [
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 0, "severity": 1.0, "deduction": 1.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 1, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 2, "severity": 3.0, "deduction": 3.0},
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        assert len(sequences) == 1
        # Max of [1.0, 2.0, 3.0] = 3.0
        assert sequences[0]["severity"] == 3.0
        assert sequences[0]["deduction"] == 3.0
    
    def test_severity_aggregation_median(self):
        """Test median aggregation of severity"""
        comparator = SequenceComparator(
            min_sequence_length=3,
            severity_aggregation="median"
        )
        
        frame_errors = [
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 0, "severity": 1.0, "deduction": 1.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 1, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 2, "severity": 3.0, "deduction": 3.0},
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        assert len(sequences) == 1
        # Median of [1.0, 2.0, 3.0] = 2.0
        assert sequences[0]["severity"] == 2.0
        assert sequences[0]["deduction"] == 2.0
    
    def test_calculate_sequence_score(self):
        """Test score calculation with sequence grouping"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        # Create 10 consecutive errors with 2.0 deduction each
        frame_errors = []
        for i in range(10):
            frame_errors.append({
                "type": "arm_angle",
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "severity": 2.0,
                "deduction": 2.0
            })
        
        initial_score = 100.0
        final_score, sequences = comparator.calculate_sequence_score(
            frame_errors,
            initial_score
        )
        
        # Without sequence grouping: 10 errors × 2.0 = 20.0 deduction → 80.0 score
        # With sequence grouping: 1 sequence × 2.0 = 2.0 deduction → 98.0 score
        assert len(sequences) == 1
        assert final_score == 98.0
    
    def test_calculate_sequence_score_multiple_sequences(self):
        """Test score calculation with multiple sequences"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        frame_errors = [
            # Sequence 1: arm_angle left (frames 0-4) - 5 frames
            *[{"type": "arm_angle", "body_part": "arm", "side": "left",
               "frame_number": i, "severity": 2.0, "deduction": 2.0}
              for i in range(5)],
            # Sequence 2: leg_angle right (frames 5-9) - 5 frames
            *[{"type": "leg_angle", "body_part": "leg", "side": "right",
               "frame_number": i, "severity": 1.5, "deduction": 1.5}
              for i in range(5, 10)],
        ]
        
        initial_score = 100.0
        final_score, sequences = comparator.calculate_sequence_score(
            frame_errors,
            initial_score
        )
        
        # 2 sequences: 2.0 + 1.5 = 3.5 deduction
        assert len(sequences) == 2
        assert final_score == 96.5
    
    def test_disabled_sequence_comparison(self):
        """Test that disabled sequence comparison returns original errors"""
        comparator = SequenceComparator(enabled=False)
        
        frame_errors = [
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": i, "severity": 2.0, "deduction": 2.0}
            for i in range(5)
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        # Should return original errors unchanged
        assert len(sequences) == 5
        assert sequences == frame_errors
    
    def test_empty_frame_errors(self):
        """Test handling of empty frame errors list"""
        comparator = SequenceComparator()
        
        sequences = comparator.group_errors_into_sequences([])
        
        assert sequences == []
    
    def test_unordered_frame_errors(self):
        """Test that unordered frame errors are sorted and grouped correctly"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        # Provide errors out of order
        frame_errors = [
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 2, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 0, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 1, "severity": 2.0, "deduction": 2.0},
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        # Should sort and group into 1 sequence
        assert len(sequences) == 1
        assert sequences[0]["start_frame"] == 0
        assert sequences[0]["end_frame"] == 2
    
    def test_mixed_errors_with_and_without_sequences(self):
        """Test handling mix of errors that form sequences and isolated errors"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        frame_errors = [
            # Sequence: 3 consecutive arm errors (frames 0-2)
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 0, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 1, "severity": 2.0, "deduction": 2.0},
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": 2, "severity": 2.0, "deduction": 2.0},
            # Isolated: only 1 leg error (frame 5)
            {"type": "leg_angle", "body_part": "leg", "side": "right",
             "frame_number": 5, "severity": 1.5, "deduction": 1.5},
            # Isolated: only 2 head errors (frames 7-8)
            {"type": "head_angle", "body_part": "nose", "side": None,
             "frame_number": 7, "severity": 1.0, "deduction": 1.0},
            {"type": "head_angle", "body_part": "nose", "side": None,
             "frame_number": 8, "severity": 1.0, "deduction": 1.0},
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        # Should have 1 sequence + 3 isolated errors
        assert len(sequences) == 4
        
        # First should be a sequence
        assert sequences[0]["is_sequence"] is True
        assert sequences[0]["sequence_length"] == 3
        
        # Others should be isolated errors
        assert "is_sequence" not in sequences[1]
        assert "is_sequence" not in sequences[2]
        assert "is_sequence" not in sequences[3]
    
    def test_large_sequence_reduction(self):
        """Test the main use case: 600 frame errors → 1 sequence"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        # Create 600 consecutive errors (the problem from requirements)
        frame_errors = []
        for i in range(600):
            frame_errors.append({
                "type": "arm_angle",
                "body_part": "arm",
                "side": "left",
                "frame_number": i,
                "severity": 0.5,  # Small error (2°)
                "deduction": 0.5
            })
        
        initial_score = 100.0
        final_score, sequences = comparator.calculate_sequence_score(
            frame_errors,
            initial_score
        )
        
        # Before: 600 errors × 0.5 = 300 deduction → -200 score
        # After: 1 sequence × 0.5 = 0.5 deduction → 99.5 score
        assert len(sequences) == 1
        assert sequences[0]["sequence_length"] == 600
        assert final_score == 99.5
        
        # Verify reduction
        without_sequence_score = initial_score - (600 * 0.5)
        assert without_sequence_score == -200.0
        
        improvement = final_score - without_sequence_score
        assert improvement == 299.5
    
    def test_errors_without_side(self):
        """Test errors that don't have a 'side' field (e.g., head_angle)"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        frame_errors = [
            {"type": "head_angle", "body_part": "nose",
             "frame_number": 0, "severity": 1.0, "deduction": 1.0},
            {"type": "head_angle", "body_part": "nose",
             "frame_number": 1, "severity": 1.0, "deduction": 1.0},
            {"type": "head_angle", "body_part": "nose",
             "frame_number": 2, "severity": 1.0, "deduction": 1.0},
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        # Should group into 1 sequence
        assert len(sequences) == 1
        assert sequences[0]["type"] == "head_angle"
        assert "side" not in sequences[0]
    
    def test_min_sequence_length_boundary(self):
        """Test behavior at min_sequence_length boundary"""
        comparator = SequenceComparator(min_sequence_length=3)
        
        # Exactly 3 errors (boundary case)
        frame_errors_exact = [
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": i, "severity": 2.0, "deduction": 2.0}
            for i in range(3)
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors_exact)
        assert len(sequences) == 1
        assert sequences[0]["is_sequence"] is True
        
        # One less than min (should not group)
        frame_errors_under = [
            {"type": "arm_angle", "body_part": "arm", "side": "left",
             "frame_number": i, "severity": 2.0, "deduction": 2.0}
            for i in range(2)
        ]
        
        sequences = comparator.group_errors_into_sequences(frame_errors_under)
        assert len(sequences) == 2
        assert "is_sequence" not in sequences[0]
