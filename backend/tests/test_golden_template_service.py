"""
Tests for golden template service
"""
import json
import pytest
from pathlib import Path
from backend.app.services.golden_template_service import (
    analyze_template_difficulty,
    load_and_analyze_template
)


class TestAnalyzeTemplateDifficulty:
    """Tests for analyze_template_difficulty function"""
    
    def test_easy_template(self):
        """Test classification of easy template (low std)"""
        profile = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 5.0},
                    "right": {"mean": 90.0, "std": 6.0}
                },
                "leg_angle": {
                    "left": {"mean": 45.0, "std": 4.0},
                    "right": {"mean": 45.0, "std": 5.0}
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        assert difficulty == "easy"
        assert avg_std == 5.0  # (5+6+4+5)/4
    
    def test_medium_template(self):
        """Test classification of medium template (moderate std)"""
        profile = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 15.0},
                    "right": {"mean": 90.0, "std": 16.0}
                },
                "leg_angle": {
                    "left": {"mean": 45.0, "std": 12.0},
                    "right": {"mean": 45.0, "std": 13.0}
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        assert difficulty == "medium"
        assert avg_std == 14.0  # (15+16+12+13)/4
    
    def test_hard_template(self):
        """Test classification of hard template (high std)"""
        profile = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 25.0},
                    "right": {"mean": 90.0, "std": 26.0}
                },
                "leg_angle": {
                    "left": {"mean": 45.0, "std": 22.0},
                    "right": {"mean": 45.0, "std": 23.0}
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        assert difficulty == "hard"
        assert avg_std == 24.0  # (25+26+22+23)/4
    
    def test_boundary_easy_medium(self):
        """Test boundary between easy and medium (std=10)"""
        profile = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 9.9},
                    "right": {"mean": 90.0, "std": 10.1}
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        # Average is 10.0, which should be classified as medium (>= 10)
        assert difficulty == "medium"
        assert avg_std == 10.0
    
    def test_boundary_medium_hard(self):
        """Test boundary between medium and hard (std=20)"""
        profile = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 19.9},
                    "right": {"mean": 90.0, "std": 20.1}
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        # Average is 20.0, which should be classified as hard (>= 20)
        assert difficulty == "hard"
        assert avg_std == 20.0
    
    def test_single_metric_with_std(self):
        """Test template with single metric (not left/right split)"""
        profile = {
            "statistics": {
                "head_angle": {
                    "mean": 0.0,
                    "std": 8.0
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        assert difficulty == "easy"
        assert avg_std == 8.0
    
    def test_mixed_single_and_split_metrics(self):
        """Test template with mix of single and left/right metrics"""
        profile = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 10.0},
                    "right": {"mean": 90.0, "std": 12.0}
                },
                "head_angle": {
                    "mean": 0.0,
                    "std": 8.0
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        # Average: (10+12+8)/3 = 10.0
        assert difficulty == "medium"
        assert avg_std == 10.0
    
    def test_empty_profile(self):
        """Test handling of empty profile"""
        profile = {}
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        assert difficulty == "unknown"
        assert avg_std == 0.0
    
    def test_no_statistics(self):
        """Test handling of profile without statistics"""
        profile = {"some_other_field": "value"}
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        assert difficulty == "unknown"
        assert avg_std == 0.0
    
    def test_none_std_values_ignored(self):
        """Test that None std values are ignored"""
        profile = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 10.0},
                    "right": {"mean": 90.0, "std": None}  # None should be ignored
                },
                "leg_angle": {
                    "left": {"mean": 45.0, "std": 12.0}
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        # Average: (10+12)/2 = 11.0 (ignoring None)
        assert difficulty == "medium"
        assert avg_std == 11.0
    
    def test_missing_std_fields_ignored(self):
        """Test that metrics without std field are ignored"""
        profile = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 10.0},
                    "right": {"mean": 90.0}  # No std field
                },
                "leg_angle": {
                    "left": {"mean": 45.0, "std": 8.0}
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        # Average: (10+8)/2 = 9.0 (ignoring missing std)
        assert difficulty == "easy"
        assert avg_std == 9.0
    
    def test_all_std_none_or_missing(self):
        """Test template where all std values are None or missing"""
        profile = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": None},
                    "right": {"mean": 90.0}
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        assert difficulty == "unknown"
        assert avg_std == 0.0
    
    def test_zero_std(self):
        """Test template with zero std (perfectly consistent)"""
        profile = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 0.0},
                    "right": {"mean": 90.0, "std": 0.0}
                }
            }
        }
        
        difficulty, avg_std = analyze_template_difficulty(profile)
        
        assert difficulty == "easy"
        assert avg_std == 0.0


class TestLoadAndAnalyzeTemplate:
    """Tests for load_and_analyze_template function"""
    
    def test_load_valid_template(self, tmp_path):
        """Test loading a valid golden template"""
        # Create a temporary golden profile
        profile_data = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 5.0},
                    "right": {"mean": 90.0, "std": 6.0}
                }
            }
        }
        
        profile_path = tmp_path / "golden_profile.json"
        with open(profile_path, 'w') as f:
            json.dump(profile_data, f)
        
        result = load_and_analyze_template(profile_path)
        
        assert result is not None
        assert "statistics" in result
        assert "difficulty" in result
        assert result["difficulty"]["level"] == "easy"
        assert result["difficulty"]["average_std"] == 5.5
    
    def test_load_nonexistent_template(self, tmp_path):
        """Test loading a nonexistent template"""
        profile_path = tmp_path / "nonexistent.json"
        
        result = load_and_analyze_template(profile_path)
        
        assert result is None
    
    def test_load_invalid_json(self, tmp_path):
        """Test loading a file with invalid JSON"""
        profile_path = tmp_path / "invalid.json"
        with open(profile_path, 'w') as f:
            f.write("not valid json {[")
        
        result = load_and_analyze_template(profile_path)
        
        assert result is None
    
    def test_load_template_adds_difficulty(self, tmp_path):
        """Test that loading adds difficulty analysis to profile"""
        profile_data = {
            "statistics": {
                "arm_angle": {
                    "left": {"mean": 90.0, "std": 25.0},
                    "right": {"mean": 90.0, "std": 26.0}
                }
            }
        }
        
        profile_path = tmp_path / "golden_profile.json"
        with open(profile_path, 'w') as f:
            json.dump(profile_data, f)
        
        result = load_and_analyze_template(profile_path)
        
        assert result is not None
        assert "difficulty" in result
        assert result["difficulty"]["level"] == "hard"
        assert result["difficulty"]["average_std"] == 25.5
    
    def test_load_empty_file(self, tmp_path):
        """Test loading an empty file"""
        profile_path = tmp_path / "empty.json"
        with open(profile_path, 'w') as f:
            f.write("")
        
        result = load_and_analyze_template(profile_path)
        
        assert result is None
