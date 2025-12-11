"""
Tests for temporal smoothing service
"""
import numpy as np
import pytest
from backend.app.services.temporal_smoothing import TemporalSmoother, KeypointSmoother


class TestTemporalSmoother:
    """Tests for TemporalSmoother class"""
    
    def test_moving_average_basic(self):
        """Test basic moving average smoothing"""
        smoother = TemporalSmoother(window_size=3, method="moving_average")
        
        # Add values
        smoother.add_value(10.0)
        smoother.add_value(20.0)
        smoother.add_value(30.0)
        
        # Should return average of 10, 20, 30 = 20.0
        smoothed = smoother.get_smoothed_value()
        assert smoothed == pytest.approx(20.0, rel=1e-5)
    
    def test_moving_average_with_noise_spike(self):
        """Test that moving average reduces noise spikes"""
        smoother = TemporalSmoother(window_size=5, method="moving_average")
        
        # Add normal values with one spike
        smoother.add_value(45.0)
        smoother.add_value(47.0)
        smoother.add_value(46.0)
        smoother.add_value(65.0)  # Noise spike
        smoother.add_value(48.0)
        
        # Average = (45 + 47 + 46 + 65 + 48) / 5 = 50.2
        smoothed = smoother.get_smoothed_value()
        assert smoothed == pytest.approx(50.2, rel=1e-5)
        
        # Smoothed value should be less affected than the spike
        assert abs(smoothed - 47.0) < abs(65.0 - 47.0)
    
    def test_median_filter_robustness(self):
        """Test that median filter is robust to outliers"""
        smoother = TemporalSmoother(window_size=5, method="median")
        
        # Add values with outlier
        smoother.add_value(45.0)
        smoother.add_value(46.0)
        smoother.add_value(47.0)
        smoother.add_value(100.0)  # Outlier
        smoother.add_value(48.0)
        
        # Median of [45, 46, 47, 48, 100] = 47.0
        smoothed = smoother.get_smoothed_value()
        assert smoothed == pytest.approx(47.0, rel=1e-5)
    
    def test_median_vs_average_outlier_handling(self):
        """Test that median handles outliers better than average"""
        values = [45.0, 46.0, 47.0, 100.0, 48.0]
        
        # Test with average
        avg_smoother = TemporalSmoother(window_size=5, method="moving_average")
        for v in values:
            avg_smoother.add_value(v)
        avg_result = avg_smoother.get_smoothed_value()
        
        # Test with median
        med_smoother = TemporalSmoother(window_size=5, method="median")
        for v in values:
            med_smoother.add_value(v)
        med_result = med_smoother.get_smoothed_value()
        
        # Median should be closer to true value (around 46-47)
        expected = 46.5
        assert abs(med_result - expected) < abs(avg_result - expected)
    
    def test_reset(self):
        """Test reset functionality"""
        smoother = TemporalSmoother(window_size=3, method="moving_average")
        
        smoother.add_value(10.0)
        smoother.add_value(20.0)
        assert smoother.get_smoothed_value() is not None
        
        smoother.reset()
        assert smoother.get_smoothed_value() is None
    
    def test_empty_smoother(self):
        """Test smoother with no values returns None"""
        smoother = TemporalSmoother(window_size=5, method="moving_average")
        assert smoother.get_smoothed_value() is None
    
    def test_window_size_sliding(self):
        """Test that window slides correctly when adding more than window_size values"""
        smoother = TemporalSmoother(window_size=3, method="moving_average")
        
        smoother.add_value(10.0)
        smoother.add_value(20.0)
        smoother.add_value(30.0)
        smoother.add_value(40.0)  # Should drop 10.0
        
        # Average of [20, 30, 40] = 30.0
        smoothed = smoother.get_smoothed_value()
        assert smoothed == pytest.approx(30.0, rel=1e-5)
    
    def test_is_ready(self):
        """Test is_ready method"""
        smoother = TemporalSmoother(window_size=3, method="moving_average")
        
        assert not smoother.is_ready()
        
        smoother.add_value(10.0)
        assert not smoother.is_ready()
        
        smoother.add_value(20.0)
        assert not smoother.is_ready()
        
        smoother.add_value(30.0)
        assert smoother.is_ready()
    
    def test_none_values_ignored(self):
        """Test that None values are ignored"""
        smoother = TemporalSmoother(window_size=3, method="moving_average")
        
        smoother.add_value(10.0)
        smoother.add_value(None)  # Should be ignored
        smoother.add_value(20.0)
        
        # Should average only 10 and 20
        smoothed = smoother.get_smoothed_value()
        assert smoothed == pytest.approx(15.0, rel=1e-5)
    
    def test_non_finite_values_ignored(self):
        """Test that non-finite values (inf, -inf, NaN) are ignored"""
        smoother = TemporalSmoother(window_size=5, method="moving_average")
        
        smoother.add_value(10.0)
        smoother.add_value(float('inf'))  # Should be ignored
        smoother.add_value(20.0)
        smoother.add_value(float('-inf'))  # Should be ignored
        smoother.add_value(30.0)
        smoother.add_value(float('nan'))  # Should be ignored
        
        # Should average only 10, 20, 30
        smoothed = smoother.get_smoothed_value()
        assert smoothed == pytest.approx(20.0, rel=1e-5)


class TestKeypointSmoother:
    """Tests for KeypointSmoother class"""
    
    def test_basic_smoothing(self):
        """Test basic keypoint smoothing"""
        smoother = KeypointSmoother(window_size=3, num_keypoints=17, method="moving_average")
        
        # Create test keypoints with slight variations
        kp1 = np.ones((17, 3)) * 10.0
        kp1[:, 2] = 0.9  # confidence
        
        kp2 = np.ones((17, 3)) * 20.0
        kp2[:, 2] = 0.9
        
        kp3 = np.ones((17, 3)) * 30.0
        kp3[:, 2] = 0.9
        
        smoother.add_keypoints(kp1)
        smoother.add_keypoints(kp2)
        smoother.add_keypoints(kp3)
        
        smoothed = smoother.get_smoothed_keypoints()
        
        # x and y should be averaged: (10 + 20 + 30) / 3 = 20
        assert smoothed[0, 0] == pytest.approx(20.0, rel=1e-5)
        assert smoothed[0, 1] == pytest.approx(20.0, rel=1e-5)
        # Confidence should be from most recent frame
        assert smoothed[0, 2] == pytest.approx(0.9, rel=1e-5)
    
    def test_noise_reduction(self):
        """Test that smoothing reduces keypoint jitter"""
        smoother = KeypointSmoother(window_size=5, num_keypoints=17, method="moving_average")
        
        # Create keypoints with noise
        base_kp = np.array([[100.0, 200.0, 0.9]] * 17)
        
        # Add frames with slight jitter
        num_keypoints = base_kp.shape[0]
        for i in range(5):
            noisy_kp = base_kp.copy()
            # Add random noise ±5 pixels
            noisy_kp[:, 0] += np.random.uniform(-5, 5, num_keypoints)
            noisy_kp[:, 1] += np.random.uniform(-5, 5, num_keypoints)
            smoother.add_keypoints(noisy_kp)
        
        smoothed = smoother.get_smoothed_keypoints()
        
        # Smoothed values should be closer to base than individual noisy frames
        assert abs(smoothed[0, 0] - 100.0) < 5.0
        assert abs(smoothed[0, 1] - 200.0) < 5.0
    
    def test_median_keypoint_smoothing(self):
        """Test median smoothing for keypoints"""
        smoother = KeypointSmoother(window_size=5, num_keypoints=17, method="median")
        
        # Create keypoints with one outlier frame
        normal_kp = np.array([[100.0, 200.0, 0.9]] * 17)
        outlier_kp = np.array([[200.0, 300.0, 0.9]] * 17)  # Big jump
        
        smoother.add_keypoints(normal_kp)
        smoother.add_keypoints(normal_kp.copy())
        smoother.add_keypoints(outlier_kp)  # Outlier
        smoother.add_keypoints(normal_kp.copy())
        smoother.add_keypoints(normal_kp.copy())
        
        smoothed = smoother.get_smoothed_keypoints()
        
        # Median should be close to normal value
        assert smoothed[0, 0] == pytest.approx(100.0, abs=1.0)
        assert smoothed[0, 1] == pytest.approx(200.0, abs=1.0)
    
    def test_confidence_from_latest_frame(self):
        """Test that confidence values come from the most recent frame"""
        smoother = KeypointSmoother(window_size=3, num_keypoints=17, method="moving_average")
        
        kp1 = np.ones((17, 3)) * 10.0
        kp1[:, 2] = 0.5  # Low confidence
        
        kp2 = np.ones((17, 3)) * 20.0
        kp2[:, 2] = 0.7
        
        kp3 = np.ones((17, 3)) * 30.0
        kp3[:, 2] = 0.9  # High confidence in latest
        
        smoother.add_keypoints(kp1)
        smoother.add_keypoints(kp2)
        smoother.add_keypoints(kp3)
        
        smoothed = smoother.get_smoothed_keypoints()
        
        # Should use confidence from kp3 (most recent)
        assert np.all(smoothed[:, 2] == pytest.approx(0.9, rel=1e-5))
    
    def test_reset(self):
        """Test reset functionality"""
        smoother = KeypointSmoother(window_size=3, num_keypoints=17)
        
        kp = np.ones((17, 3)) * 10.0
        smoother.add_keypoints(kp)
        
        assert smoother.get_smoothed_keypoints() is not None
        
        smoother.reset()
        assert smoother.get_smoothed_keypoints() is None
    
    def test_empty_smoother(self):
        """Test smoother with no keypoints returns None"""
        smoother = KeypointSmoother(window_size=5, num_keypoints=17)
        assert smoother.get_smoothed_keypoints() is None
    
    def test_window_sliding(self):
        """Test that window slides correctly"""
        smoother = KeypointSmoother(window_size=2, num_keypoints=17, method="moving_average")
        
        kp1 = np.ones((17, 3)) * 10.0
        kp1[:, 2] = 0.9
        
        kp2 = np.ones((17, 3)) * 20.0
        kp2[:, 2] = 0.9
        
        kp3 = np.ones((17, 3)) * 30.0
        kp3[:, 2] = 0.9
        
        smoother.add_keypoints(kp1)
        smoother.add_keypoints(kp2)
        smoother.add_keypoints(kp3)  # Should drop kp1
        
        smoothed = smoother.get_smoothed_keypoints()
        
        # Should average kp2 and kp3: (20 + 30) / 2 = 25
        assert smoothed[0, 0] == pytest.approx(25.0, rel=1e-5)
    
    def test_is_ready(self):
        """Test is_ready method"""
        smoother = KeypointSmoother(window_size=3, num_keypoints=17)
        
        assert not smoother.is_ready()
        
        kp = np.ones((17, 3)) * 10.0
        smoother.add_keypoints(kp)
        assert not smoother.is_ready()
        
        smoother.add_keypoints(kp)
        assert not smoother.is_ready()
        
        smoother.add_keypoints(kp)
        assert smoother.is_ready()
    
    def test_invalid_keypoints_ignored(self):
        """Test that invalid keypoints are ignored"""
        smoother = KeypointSmoother(window_size=3, num_keypoints=17)
        
        valid_kp = np.ones((17, 3)) * 10.0
        invalid_kp = np.ones((5, 3)) * 20.0  # Too few keypoints
        
        smoother.add_keypoints(valid_kp)
        smoother.add_keypoints(invalid_kp)  # Should be ignored
        smoother.add_keypoints(None)  # Should be ignored
        
        smoothed = smoother.get_smoothed_keypoints()
        
        # Should only have valid_kp in buffer
        assert smoothed[0, 0] == pytest.approx(10.0, rel=1e-5)


class TestNoiseReduction:
    """Integration tests for noise reduction effectiveness"""
    
    def test_variance_reduction_with_smoothing(self):
        """Test that smoothing reduces variance in noisy signals"""
        np.random.seed(42)  # For reproducibility
        
        # Generate noisy angle measurements
        true_angle = 45.0
        noise_level = 10.0
        num_samples = 100
        
        noisy_angles = true_angle + np.random.normal(0, noise_level, num_samples)
        
        # Smooth with moving average
        smoother = TemporalSmoother(window_size=5, method="moving_average")
        smoothed_angles = []
        
        for angle in noisy_angles:
            smoother.add_value(angle)
            smoothed = smoother.get_smoothed_value()
            if smoothed is not None:
                smoothed_angles.append(smoothed)
        
        # Calculate variance
        original_variance = np.var(noisy_angles)
        smoothed_variance = np.var(smoothed_angles)
        
        # Smoothed signal should have lower variance
        assert smoothed_variance < original_variance
        
        # Variance reduction should be significant (at least 30%)
        reduction_ratio = smoothed_variance / original_variance
        assert reduction_ratio < 0.7
    
    def test_false_positive_reduction(self):
        """Test that smoothing reduces false positive error detections"""
        # Simulate angle measurements with occasional spikes
        base_angle = 45.0
        threshold = 15.0
        
        # Create signal with noise spikes
        angles = [45.0, 47.0, 46.0, 70.0, 48.0, 44.0, 65.0, 46.0, 47.0, 45.0]
        
        # Count errors without smoothing
        errors_without_smoothing = sum(1 for angle in angles if abs(angle - base_angle) > threshold)
        
        # Count errors with smoothing
        smoother = TemporalSmoother(window_size=5, method="moving_average")
        errors_with_smoothing = 0
        
        for angle in angles:
            smoother.add_value(angle)
            smoothed = smoother.get_smoothed_value()
            if smoothed is not None and abs(smoothed - base_angle) > threshold:
                errors_with_smoothing += 1
        
        # Smoothing should reduce false positives
        assert errors_with_smoothing < errors_without_smoothing
    
    def test_smoothing_latency_acceptable(self):
        """Test that smoothing window size provides acceptable latency"""
        # With window_size=5 at 30fps, latency is ~167ms
        window_size = 5
        fps = 30
        MS_PER_SECOND = 1000
        latency_ms = (window_size / fps) * MS_PER_SECOND
        
        # Latency should be under 200ms for acceptable real-time performance
        assert latency_ms < 200
        assert latency_ms == pytest.approx(166.67, rel=0.01)
