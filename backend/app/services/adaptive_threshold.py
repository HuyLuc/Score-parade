"""
Adaptive Threshold Service

Calculates dynamic thresholds based on golden template statistics
to ensure fair scoring across templates with varying difficulty levels.
"""
from typing import Dict, Optional, Tuple


def calculate_adaptive_threshold(
    golden_std: float,
    default_threshold: float,
    multiplier: float = 3.0,
    min_ratio: float = 0.3,
    max_ratio: float = 2.0
) -> float:
    """
    Calculate adaptive threshold based on golden template standard deviation.
    
    Uses 3-sigma rule (99.7% confidence interval) as base, with min/max bounds
    to prevent extreme thresholds.
    
    Args:
        golden_std: Standard deviation from golden template
        default_threshold: Default threshold value from ERROR_THRESHOLDS
        multiplier: N-sigma multiplier (default: 3.0 for 99.7% CI)
        min_ratio: Minimum threshold as ratio of default (default: 0.3 = 30%)
        max_ratio: Maximum threshold as ratio of default (default: 2.0 = 200%)
    
    Returns:
        Adaptive threshold value
        
    Examples:
        >>> calculate_adaptive_threshold(5.0, 50.0, 3.0, 0.3, 2.0)
        15.0  # max(3*5, 50*0.3) = max(15, 15) = 15
        
        >>> calculate_adaptive_threshold(25.0, 50.0, 3.0, 0.3, 2.0)
        75.0  # max(3*25, 50*0.3) = max(75, 15) = 75
        
        >>> calculate_adaptive_threshold(2.0, 50.0, 3.0, 0.3, 2.0)
        15.0  # max(3*2, 50*0.3) = max(6, 15) = 15 (enforces minimum)
        
        >>> calculate_adaptive_threshold(40.0, 50.0, 3.0, 0.3, 2.0)
        100.0  # max(3*40, 50*0.3) = max(120, 15) = 120 → capped at 100 (max_ratio)
    """
    if golden_std is None or golden_std < 0:
        return default_threshold
    
    # Calculate threshold using N-sigma rule
    sigma_threshold = multiplier * golden_std
    
    # Apply min/max bounds based on default threshold
    min_threshold = default_threshold * min_ratio
    max_threshold = default_threshold * max_ratio
    
    # Use whichever is larger between sigma and minimum, then cap at maximum
    adaptive_threshold = max(sigma_threshold, min_threshold)
    adaptive_threshold = min(adaptive_threshold, max_threshold)
    
    return adaptive_threshold


class AdaptiveThresholdManager:
    """
    Manages adaptive thresholds for all error types with caching.
    
    Caches computed thresholds per (error_type, golden_mean, golden_std) tuple
    to avoid redundant calculations during a session.
    """
    
    def __init__(
        self,
        multiplier: float = 3.0,
        min_ratio: float = 0.3,
        max_ratio: float = 2.0,
        enable_cache: bool = True
    ):
        """
        Initialize adaptive threshold manager.
        
        Args:
            multiplier: N-sigma multiplier for threshold calculation
            min_ratio: Minimum threshold ratio relative to default
            max_ratio: Maximum threshold ratio relative to default
            enable_cache: Whether to cache computed thresholds
        """
        self.multiplier = multiplier
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.enable_cache = enable_cache
        
        # Cache: {(error_type, golden_mean, golden_std): threshold}
        self._cache: Dict[Tuple[str, Optional[float], Optional[float]], float] = {}
    
    def get_threshold(
        self,
        error_type: str,
        golden_mean: Optional[float],
        golden_std: Optional[float],
        default_threshold: float
    ) -> float:
        """
        Get adaptive threshold for given error type and golden statistics.
        
        Args:
            error_type: Type of error (e.g., "arm_angle", "leg_angle")
            golden_mean: Mean value from golden template (not used in current impl)
            golden_std: Standard deviation from golden template
            default_threshold: Default threshold if no golden_std available
            
        Returns:
            Adaptive threshold value
        """
        # Check cache first
        cache_key = (error_type, golden_mean, golden_std)
        if self.enable_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Calculate adaptive threshold
        if golden_std is not None and golden_std >= 0:
            threshold = calculate_adaptive_threshold(
                golden_std=golden_std,
                default_threshold=default_threshold,
                multiplier=self.multiplier,
                min_ratio=self.min_ratio,
                max_ratio=self.max_ratio
            )
        else:
            # Fallback to default if no golden std
            threshold = default_threshold
        
        # Store in cache
        if self.enable_cache:
            self._cache[cache_key] = threshold
        
        return threshold
    
    def reset_cache(self) -> None:
        """
        Reset the threshold cache.
        
        Should be called when loading a new golden template or starting
        a new session to ensure fresh threshold calculations.
        """
        self._cache.clear()
