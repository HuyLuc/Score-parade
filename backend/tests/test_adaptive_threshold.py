"""
Tests for adaptive threshold service
"""
import pytest
from backend.app.services.adaptive_threshold import (
    calculate_adaptive_threshold,
    AdaptiveThresholdManager
)


class TestCalculateAdaptiveThreshold:
    """Tests for calculate_adaptive_threshold function"""
    
    def test_adaptive_threshold_with_low_std(self):
        """Test that easy templates (low std) get tight thresholds"""
        # Easy template: std=5, should use 3*5=15 (tighter than default)
        threshold = calculate_adaptive_threshold(
            golden_std=5.0,
            default_threshold=50.0,
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        # Should use max(3*5, 50*0.3) = max(15, 15) = 15
        assert threshold == 15.0
    
    def test_adaptive_threshold_with_high_std(self):
        """Test that hard templates (high std) get loose thresholds"""
        # Hard template: std=25, should use 3*25=75 (looser than default)
        threshold = calculate_adaptive_threshold(
            golden_std=25.0,
            default_threshold=50.0,
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        # Should use max(3*25, 50*0.3) = max(75, 15) = 75
        assert threshold == 75.0
    
    def test_min_ratio_bounds(self):
        """Test that minimum ratio is enforced for very low std"""
        # Very low std: should hit minimum bound
        threshold = calculate_adaptive_threshold(
            golden_std=2.0,
            default_threshold=50.0,
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        # Should use max(3*2, 50*0.3) = max(6, 15) = 15 (minimum)
        assert threshold == 15.0
    
    def test_max_ratio_bounds(self):
        """Test that maximum ratio is enforced for very high std"""
        # Very high std: should hit maximum bound
        threshold = calculate_adaptive_threshold(
            golden_std=40.0,
            default_threshold=50.0,
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        # Should use max(3*40, 50*0.3) = max(120, 15) = 120
        # But capped at 50*2.0 = 100 (maximum)
        assert threshold == 100.0
    
    def test_fallback_to_default_on_none_std(self):
        """Test fallback to default threshold when std is None"""
        threshold = calculate_adaptive_threshold(
            golden_std=None,
            default_threshold=50.0,
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        assert threshold == 50.0
    
    def test_fallback_to_default_on_negative_std(self):
        """Test fallback to default threshold when std is negative"""
        threshold = calculate_adaptive_threshold(
            golden_std=-5.0,
            default_threshold=50.0,
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        assert threshold == 50.0
    
    def test_zero_std(self):
        """Test handling of zero std (perfectly consistent template)"""
        threshold = calculate_adaptive_threshold(
            golden_std=0.0,
            default_threshold=50.0,
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        # Should use max(3*0, 50*0.3) = max(0, 15) = 15 (minimum)
        assert threshold == 15.0
    
    def test_different_multiplier(self):
        """Test with different N-sigma multiplier"""
        # Using 2-sigma instead of 3-sigma
        threshold = calculate_adaptive_threshold(
            golden_std=10.0,
            default_threshold=50.0,
            multiplier=2.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        # Should use max(2*10, 50*0.3) = max(20, 15) = 20
        assert threshold == 20.0
    
    def test_different_min_ratio(self):
        """Test with different minimum ratio"""
        threshold = calculate_adaptive_threshold(
            golden_std=2.0,
            default_threshold=50.0,
            multiplier=3.0,
            min_ratio=0.5,  # 50% instead of 30%
            max_ratio=2.0
        )
        # Should use max(3*2, 50*0.5) = max(6, 25) = 25
        assert threshold == 25.0
    
    def test_different_max_ratio(self):
        """Test with different maximum ratio"""
        threshold = calculate_adaptive_threshold(
            golden_std=50.0,
            default_threshold=50.0,
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=1.5  # 150% instead of 200%
        )
        # Should use max(3*50, 50*0.3) = max(150, 15) = 150
        # But capped at 50*1.5 = 75 (maximum)
        assert threshold == 75.0


class TestAdaptiveThresholdManager:
    """Tests for AdaptiveThresholdManager class"""
    
    def test_get_threshold_with_golden_std(self):
        """Test getting threshold with valid golden std"""
        manager = AdaptiveThresholdManager(
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        
        threshold = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=5.0,
            default_threshold=50.0
        )
        
        assert threshold == 15.0
    
    def test_get_threshold_fallback_to_default(self):
        """Test fallback to default when no golden std"""
        manager = AdaptiveThresholdManager()
        
        threshold = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=None,
            default_threshold=50.0
        )
        
        assert threshold == 50.0
    
    def test_cache_functionality(self):
        """Test that thresholds are cached correctly"""
        manager = AdaptiveThresholdManager(enable_cache=True)
        
        # First call - calculates and caches
        threshold1 = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=5.0,
            default_threshold=50.0
        )
        
        # Second call with same parameters - should return cached value
        threshold2 = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=5.0,
            default_threshold=50.0
        )
        
        assert threshold1 == threshold2 == 15.0
        
        # Check cache has the entry
        cache_key = ("arm_angle", 90.0, 5.0)
        assert cache_key in manager._cache
        assert manager._cache[cache_key] == 15.0
    
    def test_cache_different_error_types(self):
        """Test that cache distinguishes between different error types"""
        manager = AdaptiveThresholdManager(enable_cache=True)
        
        threshold_arm = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=5.0,
            default_threshold=50.0
        )
        
        threshold_leg = manager.get_threshold(
            error_type="leg_angle",
            golden_mean=90.0,
            golden_std=5.0,
            default_threshold=45.0
        )
        
        # Different error types can have different defaults
        assert threshold_arm == 15.0
        assert threshold_leg == 15.0
        
        # Should have separate cache entries
        assert ("arm_angle", 90.0, 5.0) in manager._cache
        assert ("leg_angle", 90.0, 5.0) in manager._cache
    
    def test_cache_different_std_values(self):
        """Test that cache distinguishes between different std values"""
        manager = AdaptiveThresholdManager(enable_cache=True)
        
        threshold1 = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=5.0,
            default_threshold=50.0
        )
        
        threshold2 = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=25.0,
            default_threshold=50.0
        )
        
        assert threshold1 == 15.0
        assert threshold2 == 75.0
        
        # Should have separate cache entries
        assert len(manager._cache) == 2
    
    def test_cache_disabled(self):
        """Test that cache is not used when disabled"""
        manager = AdaptiveThresholdManager(enable_cache=False)
        
        threshold1 = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=5.0,
            default_threshold=50.0
        )
        
        # Cache should be empty
        assert len(manager._cache) == 0
        assert threshold1 == 15.0
    
    def test_reset_cache(self):
        """Test cache reset functionality"""
        manager = AdaptiveThresholdManager(enable_cache=True)
        
        # Add some entries to cache
        manager.get_threshold("arm_angle", 90.0, 5.0, 50.0)
        manager.get_threshold("leg_angle", 90.0, 10.0, 45.0)
        
        assert len(manager._cache) == 2
        
        # Reset cache
        manager.reset_cache()
        
        assert len(manager._cache) == 0
    
    def test_min_max_ratio_enforcement(self):
        """Test that manager enforces min/max ratio bounds"""
        manager = AdaptiveThresholdManager(
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        
        # Very low std - should hit minimum
        threshold_low = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=1.0,
            default_threshold=50.0
        )
        assert threshold_low == 15.0  # 50 * 0.3
        
        # Very high std - should hit maximum
        threshold_high = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=50.0,
            default_threshold=50.0
        )
        assert threshold_high == 100.0  # 50 * 2.0
    
    def test_negative_std_fallback(self):
        """Test fallback when std is negative (invalid)"""
        manager = AdaptiveThresholdManager()
        
        threshold = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=-5.0,
            default_threshold=50.0
        )
        
        assert threshold == 50.0


class TestAdaptiveThresholdIntegration:
    """Integration tests for adaptive threshold behavior"""
    
    def test_easy_vs_hard_template_comparison(self):
        """Test that easy templates get stricter thresholds than hard templates"""
        manager = AdaptiveThresholdManager(
            multiplier=3.0,
            min_ratio=0.3,
            max_ratio=2.0
        )
        
        # Easy template (low std)
        easy_threshold = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=5.0,
            default_threshold=50.0
        )
        
        # Hard template (high std)
        hard_threshold = manager.get_threshold(
            error_type="arm_angle",
            golden_mean=90.0,
            golden_std=25.0,
            default_threshold=50.0
        )
        
        # Easy template should have tighter threshold
        assert easy_threshold < hard_threshold
        assert easy_threshold == 15.0
        assert hard_threshold == 75.0
    
    def test_fairness_across_templates(self):
        """Test that adaptive thresholds provide fair scoring across templates"""
        manager = AdaptiveThresholdManager()
        
        # Simulate three templates with different difficulty
        templates = [
            {"name": "easy", "std": 5.0, "expected_threshold": 15.0},
            {"name": "medium", "std": 15.0, "expected_threshold": 45.0},
            {"name": "hard", "std": 25.0, "expected_threshold": 75.0},
        ]
        
        for template in templates:
            threshold = manager.get_threshold(
                error_type="arm_angle",
                golden_mean=90.0,
                golden_std=template["std"],
                default_threshold=50.0
            )
            assert threshold == template["expected_threshold"]
    
    def test_consistent_scoring_with_cache(self):
        """Test that caching provides consistent results"""
        manager = AdaptiveThresholdManager(enable_cache=True)
        
        # Get threshold multiple times
        thresholds = []
        for _ in range(5):
            threshold = manager.get_threshold(
                error_type="arm_angle",
                golden_mean=90.0,
                golden_std=10.0,
                default_threshold=50.0
            )
            thresholds.append(threshold)
        
        # All should be the same
        assert all(t == thresholds[0] for t in thresholds)
        assert thresholds[0] == 30.0  # max(3*10, 50*0.3) = max(30, 15) = 30
