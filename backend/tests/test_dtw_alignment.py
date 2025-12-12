"""
Tests for DTW alignment service
"""
import numpy as np
import pytest
from backend.app.services.dtw_alignment import DTWAligner


class TestDTWAligner:
    """Tests for DTWAligner class"""
    
    def create_sample_keypoints(self, base_angles: dict = None) -> np.ndarray:
        """
        Create sample keypoints with specific angles
        
        Args:
            base_angles: Dict with 'arm', 'leg', 'head' angles to simulate
            
        Returns:
            Keypoints array [17, 3]
        """
        if base_angles is None:
            base_angles = {"arm": 90, "leg": 180, "head": 0}
        
        # Create simple keypoints with reasonable positions
        keypoints = np.zeros((17, 3))
        
        # Set confidence to 1.0 for all keypoints
        keypoints[:, 2] = 1.0
        
        # Nose (0)
        keypoints[0] = [100, 50, 1.0]
        
        # Eyes (1, 2)
        keypoints[1] = [95, 48, 1.0]
        keypoints[2] = [105, 48, 1.0]
        
        # Ears (3, 4)
        keypoints[3] = [90, 50, 1.0]
        keypoints[4] = [110, 50, 1.0]
        
        # Shoulders (5, 6)
        keypoints[5] = [80, 100, 1.0]  # left shoulder
        keypoints[6] = [120, 100, 1.0]  # right shoulder
        
        # Elbows (7, 8) - positioned based on arm angle
        keypoints[7] = [60, 120, 1.0]  # left elbow
        keypoints[8] = [140, 120, 1.0]  # right elbow
        
        # Wrists (9, 10)
        keypoints[9] = [50, 140, 1.0]  # left wrist
        keypoints[10] = [150, 140, 1.0]  # right wrist
        
        # Hips (11, 12)
        keypoints[11] = [85, 200, 1.0]  # left hip
        keypoints[12] = [115, 200, 1.0]  # right hip
        
        # Knees (13, 14)
        keypoints[13] = [80, 280, 1.0]  # left knee
        keypoints[14] = [120, 280, 1.0]  # right knee
        
        # Ankles (15, 16)
        keypoints[15] = [75, 360, 1.0]  # left ankle
        keypoints[16] = [125, 360, 1.0]  # right ankle
        
        return keypoints
    
    def test_dtw_same_speed(self):
        """
        Test DTW với cùng speed (1:1 mapping)
        
        Khi test và golden có cùng số frames và cùng sequence,
        DTW nên tạo alignment path gần như 1:1
        """
        aligner = DTWAligner(window_size=50, distance_metric="euclidean")
        
        # Create identical sequences
        num_frames = 10
        test_sequence = [self.create_sample_keypoints() for _ in range(num_frames)]
        golden_sequence = [self.create_sample_keypoints() for _ in range(num_frames)]
        
        # Align sequences
        distance, path = aligner.align_sequences(test_sequence, golden_sequence)
        
        # Verify alignment
        assert distance is not None
        assert path is not None
        assert len(path) >= num_frames
        
        # Check that alignment is close to 1:1
        alignment_info = aligner.get_alignment_info()
        assert alignment_info is not None
        assert alignment_info["test_frames"] == num_frames
        assert alignment_info["golden_frames"] == num_frames
        
        # Tempo ratio should be close to 1.0
        assert 0.9 <= alignment_info["tempo_ratio"] <= 1.1
        
        # Check get_aligned_frame works
        for test_idx in range(num_frames):
            golden_idx = aligner.get_aligned_frame(test_idx)
            assert golden_idx is not None
            # For identical sequences, should map to valid golden index
            assert 0 <= golden_idx < num_frames
    
    def test_dtw_different_speeds(self):
        """
        Test DTW với different speeds (test faster/slower than golden)
        
        Test scenario: Test video có 15 frames, golden có 10 frames
        (test 1.5x faster). DTW nên align chúng đúng.
        """
        aligner = DTWAligner(window_size=50, distance_metric="euclidean")
        
        # Create test sequence (15 frames - faster)
        num_test_frames = 15
        test_sequence = []
        for i in range(num_test_frames):
            kps = self.create_sample_keypoints()
            # Add slight variation to make it more realistic
            kps[:, 0] += np.random.randn(17) * 2  # Small X noise
            kps[:, 1] += np.random.randn(17) * 2  # Small Y noise
            test_sequence.append(kps)
        
        # Create golden sequence (10 frames - normal)
        num_golden_frames = 10
        golden_sequence = []
        for i in range(num_golden_frames):
            kps = self.create_sample_keypoints()
            # Add slight variation
            kps[:, 0] += np.random.randn(17) * 2
            kps[:, 1] += np.random.randn(17) * 2
            golden_sequence.append(kps)
        
        # Align sequences
        distance, path = aligner.align_sequences(test_sequence, golden_sequence)
        
        # Verify alignment
        assert distance is not None
        assert path is not None
        assert len(path) >= max(num_test_frames, num_golden_frames)
        
        # Check alignment info
        alignment_info = aligner.get_alignment_info()
        assert alignment_info is not None
        assert alignment_info["test_frames"] == num_test_frames
        
        # Tempo ratio should reflect the speed difference (1.5x)
        # Tempo ratio = test_frames / golden_frames
        expected_ratio = num_test_frames / num_golden_frames
        assert alignment_info["tempo_ratio"] == pytest.approx(expected_ratio, abs=0.1)
        
        # Verify all test frames have a mapping
        for test_idx in range(num_test_frames):
            golden_idx = aligner.get_aligned_frame(test_idx)
            assert golden_idx is not None
            assert 0 <= golden_idx < num_golden_frames
    
    def test_extract_pose_features(self):
        """Test feature extraction from keypoints"""
        aligner = DTWAligner()
        
        keypoints = self.create_sample_keypoints()
        features = aligner.extract_pose_features(keypoints)
        
        # Features should be a 1D array
        assert features.ndim == 1
        assert len(features) > 0
        
        # Should include angles, heights, and relative positions
        # Expected: 2 arm angles + 2 leg angles + 1 head angle + 2 arm heights + 2 leg heights
        # + 4 wrist positions + 4 ankle positions = 17 features minimum
        assert len(features) >= 17
    
    def test_extract_pose_features_with_missing_keypoints(self):
        """Test feature extraction khi có keypoints bị missing (confidence = 0)"""
        aligner = DTWAligner()
        
        keypoints = self.create_sample_keypoints()
        # Set some keypoints to have 0 confidence (missing)
        keypoints[9, 2] = 0.0  # left wrist missing
        keypoints[15, 2] = 0.0  # left ankle missing
        
        features = aligner.extract_pose_features(keypoints)
        
        # Should still return features (with 0s for missing parts)
        assert features.ndim == 1
        assert len(features) > 0
        # Features should contain some zeros for missing keypoints
        assert np.any(features == 0.0)
    
    def test_different_distance_metrics(self):
        """Test DTW với các distance metrics khác nhau"""
        num_frames = 8
        test_sequence = [self.create_sample_keypoints() for _ in range(num_frames)]
        golden_sequence = [self.create_sample_keypoints() for _ in range(num_frames)]
        
        metrics = ["euclidean", "manhattan", "cosine"]
        
        for metric in metrics:
            aligner = DTWAligner(window_size=50, distance_metric=metric)
            distance, path = aligner.align_sequences(test_sequence, golden_sequence)
            
            assert distance is not None, f"Distance is None for metric {metric}"
            assert path is not None, f"Path is None for metric {metric}"
            assert len(path) >= num_frames, f"Path too short for metric {metric}"
    
    def test_get_aligned_frame_without_alignment(self):
        """Test get_aligned_frame khi chưa align"""
        aligner = DTWAligner()
        
        # Should return None khi chưa align
        result = aligner.get_aligned_frame(0)
        assert result is None
    
    def test_get_alignment_info_without_alignment(self):
        """Test get_alignment_info khi chưa align"""
        aligner = DTWAligner()
        
        # Should return None khi chưa align
        result = aligner.get_alignment_info()
        assert result is None
    
    def test_dtw_with_tempo_variation_10_percent(self):
        """
        Test DTW với tempo variation 10% (giống scenario trong problem statement)
        
        Scenario: Test video nhanh hơn 10% so với golden
        """
        # Golden: 100 frames
        num_golden_frames = 100
        golden_sequence = [self.create_sample_keypoints() for _ in range(num_golden_frames)]
        
        # Test: 110 frames (10% faster)
        num_test_frames = 110
        test_sequence = [self.create_sample_keypoints() for _ in range(num_test_frames)]
        
        aligner = DTWAligner(window_size=50, distance_metric="euclidean")
        distance, path = aligner.align_sequences(test_sequence, golden_sequence)
        
        # Verify alignment exists
        assert distance is not None
        assert path is not None
        
        # Check tempo ratio
        alignment_info = aligner.get_alignment_info()
        assert alignment_info is not None
        
        # Tempo ratio should be around 1.1 (10% faster)
        expected_ratio = num_test_frames / num_golden_frames
        assert alignment_info["tempo_ratio"] == pytest.approx(expected_ratio, abs=0.05)
        
        # All test frames should have mappings
        mapped_count = 0
        for test_idx in range(num_test_frames):
            golden_idx = aligner.get_aligned_frame(test_idx)
            if golden_idx is not None:
                mapped_count += 1
        
        # Most frames should be mapped (allow some edge cases)
        assert mapped_count >= num_test_frames * 0.95
    
    def test_dtw_with_empty_sequences(self):
        """Test DTW với empty sequences"""
        aligner = DTWAligner()
        
        # Test with empty test sequence
        test_sequence = []
        golden_sequence = [self.create_sample_keypoints() for _ in range(5)]
        
        # Should handle gracefully (fastdtw might raise error, so we expect that)
        try:
            distance, path = aligner.align_sequences(test_sequence, golden_sequence)
            # If it doesn't raise, path should be empty or minimal
            assert len(path) == 0 or len(path) <= 5
        except (ValueError, IndexError):
            # Expected for empty sequences
            pass
    
    def test_dtw_alignment_monotonicity(self):
        """
        Test that DTW alignment is monotonic
        
        DTW path should be monotonically increasing (không đi ngược thời gian)
        """
        num_frames = 20
        test_sequence = [self.create_sample_keypoints() for _ in range(num_frames)]
        golden_sequence = [self.create_sample_keypoints() for _ in range(num_frames)]
        
        aligner = DTWAligner(window_size=50, distance_metric="euclidean")
        distance, path = aligner.align_sequences(test_sequence, golden_sequence)
        
        # Check monotonicity
        for i in range(1, len(path)):
            prev_test, prev_golden = path[i-1]
            curr_test, curr_golden = path[i]
            
            # Both indices should be non-decreasing
            assert curr_test >= prev_test, "Test index decreased (non-monotonic)"
            assert curr_golden >= prev_golden, "Golden index decreased (non-monotonic)"
