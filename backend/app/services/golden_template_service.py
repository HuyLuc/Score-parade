"""
Golden Template Service

Analyzes golden templates to determine difficulty level and statistics.
"""
import json
from pathlib import Path
from typing import Dict, Optional, Tuple


def analyze_template_difficulty(golden_profile: Dict) -> Tuple[str, float]:
    """
    Analyze golden template difficulty based on average standard deviation.
    
    Templates with low standard deviation are "easy" (consistent movements),
    while templates with high standard deviation are "hard" (variable movements).
    
    Args:
        golden_profile: Golden profile dictionary containing statistics
        
    Returns:
        Tuple of (difficulty_level, average_std) where:
        - difficulty_level: "easy", "medium", or "hard"
        - average_std: Average standard deviation across all metrics
        
    Examples:
        >>> profile = {"statistics": {"arm_angle": {"left": {"std": 5.0}, "right": {"std": 6.0}}}}
        >>> analyze_template_difficulty(profile)
        ('easy', 5.5)
        
        >>> profile = {"statistics": {"arm_angle": {"left": {"std": 15.0}, "right": {"std": 16.0}}}}
        >>> analyze_template_difficulty(profile)
        ('medium', 15.5)
        
        >>> profile = {"statistics": {"arm_angle": {"left": {"std": 25.0}, "right": {"std": 26.0}}}}
        >>> analyze_template_difficulty(profile)
        ('hard', 25.5)
    """
    if not golden_profile or "statistics" not in golden_profile:
        return "unknown", 0.0
    
    stats = golden_profile["statistics"]
    std_values = []
    
    # Collect all standard deviation values from the statistics
    for metric, value in stats.items():
        if isinstance(value, dict):
            # Check for left/right sides
            if "left" in value and isinstance(value["left"], dict):
                if "std" in value["left"] and value["left"]["std"] is not None:
                    std_values.append(value["left"]["std"])
            if "right" in value and isinstance(value["right"], dict):
                if "std" in value["right"] and value["right"]["std"] is not None:
                    std_values.append(value["right"]["std"])
            # Check for single std value
            if "std" in value and value["std"] is not None:
                std_values.append(value["std"])
    
    # Calculate average std
    if not std_values:
        return "unknown", 0.0
    
    avg_std = sum(std_values) / len(std_values)
    
    # Determine difficulty level
    if avg_std < 10:
        difficulty = "easy"
    elif avg_std < 20:
        difficulty = "medium"
    else:
        difficulty = "hard"
    
    return difficulty, avg_std


def load_and_analyze_template(template_path: Path) -> Optional[Dict]:
    """
    Load golden template and add difficulty analysis.
    
    Args:
        template_path: Path to golden profile JSON file
        
    Returns:
        Golden profile dictionary with added "difficulty" field, or None if load fails
    """
    if not template_path.exists():
        print(f"⚠️ Cảnh báo: Không tìm thấy golden profile: {template_path}")
        return None
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        
        # Add difficulty analysis
        difficulty, avg_std = analyze_template_difficulty(profile)
        profile["difficulty"] = {
            "level": difficulty,
            "average_std": avg_std
        }
        
        print(f"✅ Loaded golden template: difficulty={difficulty}, avg_std={avg_std:.2f}")
        
        return profile
    except (json.JSONDecodeError, IOError, UnicodeDecodeError, ValueError) as e:
        print(f"⚠️ Cảnh báo: Không thể load golden profile: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Cảnh báo: Lỗi không mong đợi khi load golden profile: {type(e).__name__}: {e}")
        return None
