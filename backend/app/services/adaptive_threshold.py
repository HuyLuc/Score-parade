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
    max_ratio: float = 2.0,
    difficulty_level: Optional[str] = None,
    torso_length: Optional[float] = None,
    reference_torso_length: float = 100.0
) -> float:
    """
    Calculate adaptive threshold based on golden template standard deviation,
    with adjustments for difficulty level and person height (torso length).
    
    Uses 3-sigma rule (99.7% confidence interval) as base, with min/max bounds
    to prevent extreme thresholds. Additionally adjusts for:
    - Difficulty level (easy/medium/hard): affects multiplier
    - Person height (torso length): scales threshold proportionally
    
    Args:
        golden_std: Standard deviation from golden template
        default_threshold: Default threshold value from ERROR_THRESHOLDS
        multiplier: N-sigma multiplier (default: 3.0 for 99.7% CI)
        min_ratio: Minimum threshold as ratio of default (default: 0.3 = 30%)
        max_ratio: Maximum threshold as ratio of default (default: 2.0 = 200%)
        difficulty_level: Difficulty level ("easy", "medium", "hard") - affects multiplier
        torso_length: Person's torso length in pixels (for height adjustment)
        reference_torso_length: Reference torso length for normalization (default: 100.0)
    
    Returns:
        Adaptive threshold value with adjustments
        
    Examples:
        >>> calculate_adaptive_threshold(5.0, 50.0, 3.0, 0.3, 2.0)
        15.0  # max(3*5, 50*0.3) = max(15, 15) = 15
        
        >>> calculate_adaptive_threshold(5.0, 50.0, 3.0, 0.3, 2.0, difficulty_level="hard")
        12.0  # hard mode: multiplier * 0.8 = 2.4, threshold = max(2.4*5, 50*0.3) = 15 → 12 (harder)
        
        >>> calculate_adaptive_threshold(5.0, 50.0, 3.0, 0.3, 2.0, torso_length=120.0)
        18.0  # taller person: scale = 120/100 = 1.2, threshold = 15 * 1.2 = 18
    """
    if golden_std is None or golden_std < 0:
        return default_threshold
    
    # Adjust multiplier based on difficulty level
    adjusted_multiplier = multiplier
    if difficulty_level == "easy":
        # Easy mode: more lenient (multiplier * 1.2)
        adjusted_multiplier = multiplier * 1.2
    elif difficulty_level == "hard":
        # Hard mode: more strict (multiplier * 0.8)
        adjusted_multiplier = multiplier * 0.8
    # medium: no adjustment (multiplier * 1.0)
    
    # Calculate threshold using N-sigma rule with adjusted multiplier
    sigma_threshold = adjusted_multiplier * golden_std
    
    # Apply min/max bounds based on default threshold
    min_threshold = default_threshold * min_ratio
    max_threshold = default_threshold * max_ratio
    
    # Use whichever is larger between sigma and minimum, then cap at maximum
    adaptive_threshold = max(sigma_threshold, min_threshold)
    adaptive_threshold = min(adaptive_threshold, max_threshold)
    
    # Adjust for person height (torso length)
    if torso_length is not None and torso_length > 0 and reference_torso_length > 0:
        # Scale threshold proportionally to torso length
        # Taller person → larger threshold (more lenient for larger movements)
        # Shorter person → smaller threshold (more strict for smaller movements)
        height_scale = torso_length / reference_torso_length
        # Clamp height scale to reasonable range (0.7 to 1.3) to avoid extreme adjustments
        height_scale = max(0.7, min(1.3, height_scale))
        adaptive_threshold = adaptive_threshold * height_scale
    
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
        default_threshold: float,
        difficulty_level: Optional[str] = None,
        torso_length: Optional[float] = None,
        reference_torso_length: float = 100.0
    ) -> float:
        """
        Get adaptive threshold for given error type and golden statistics,
        with adjustments for difficulty level and person height.
        
        Args:
            error_type: Type of error (e.g., "arm_angle", "leg_angle")
            golden_mean: Mean value from golden template (not used in current impl)
            golden_std: Standard deviation from golden template
            default_threshold: Default threshold if no golden_std available
            difficulty_level: Difficulty level ("easy", "medium", "hard") - affects multiplier
            torso_length: Person's torso length in pixels (for height adjustment)
            reference_torso_length: Reference torso length for normalization
            
        Returns:
            Adaptive threshold value with adjustments
        """
        # Check cache first (include difficulty_level and torso_length in cache key)
        cache_key = (error_type, golden_mean, golden_std, difficulty_level, torso_length)
        if self.enable_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Calculate adaptive threshold
        if golden_std is not None and golden_std >= 0:
            threshold = calculate_adaptive_threshold(
                golden_std=golden_std,
                default_threshold=default_threshold,
                multiplier=self.multiplier,
                min_ratio=self.min_ratio,
                max_ratio=self.max_ratio,
                difficulty_level=difficulty_level,
                torso_length=torso_length,
                reference_torso_length=reference_torso_length
            )
        else:
            # Fallback to default if no golden std
            # Still apply difficulty and height adjustments to default threshold
            threshold = default_threshold
            if difficulty_level == "easy":
                threshold = threshold * 1.2
            elif difficulty_level == "hard":
                threshold = threshold * 0.8
            
            if torso_length is not None and torso_length > 0 and reference_torso_length > 0:
                height_scale = max(0.7, min(1.3, torso_length / reference_torso_length))
                threshold = threshold * height_scale
        
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
