"""
Configuration API endpoints
Handles getting and updating scoring configuration
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.config import SCORING_CONFIG, ERROR_THRESHOLDS, ERROR_GROUPING_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


class ScoringConfigResponse(BaseModel):
    """Response model for scoring configuration"""
    error_weights: Dict[str, float]
    initial_score: float
    fail_threshold: float
    multi_person_enabled: bool
    error_thresholds: Dict[str, float]
    error_grouping: Dict[str, Any]
    difficulty_level: str  # 'easy', 'medium', 'hard'
    scoring_criterion: str  # 'di_deu' hoặc 'di_nghiem'
    app_mode: str  # 'dev' hoặc 'release'


class ScoringConfigUpdate(BaseModel):
    """Request model for updating scoring configuration"""
    error_weights: Dict[str, float] = None
    initial_score: float = None
    fail_threshold: float = None  # Giữ để tương thích, sẽ map sang fail_thresholds["testing"]
    multi_person_enabled: bool = None
    error_thresholds: Dict[str, float] = None
    error_grouping: Dict[str, Any] = None
    difficulty_level: str = None  # 'easy', 'medium', 'hard'
    scoring_criterion: str = None  # 'di_deu' hoặc 'di_nghiem'
    app_mode: str = None  # 'dev' hoặc 'release'


@router.get("/scoring", response_model=ScoringConfigResponse)
async def get_scoring_config():
    """
    Get current scoring configuration
    
    Returns:
        Current scoring configuration including error weights, thresholds, etc.
    """
    try:
        return ScoringConfigResponse(
            error_weights=SCORING_CONFIG.get("error_weights", {}),
            initial_score=SCORING_CONFIG.get("initial_score", 100.0),
            fail_threshold=SCORING_CONFIG.get("fail_thresholds", {}).get("testing", 50.0),
            multi_person_enabled=SCORING_CONFIG.get("multi_person_enabled", False),
            error_thresholds=ERROR_THRESHOLDS,
            error_grouping=ERROR_GROUPING_CONFIG,
            difficulty_level=SCORING_CONFIG.get("difficulty_level", "medium"),
            scoring_criterion=SCORING_CONFIG.get("scoring_criterion", "di_deu"),
            app_mode=SCORING_CONFIG.get("app_mode", "release")
        )
    except Exception as e:
        logger.error(f"Error getting scoring config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy cấu hình: {str(e)}"
        )


@router.put("/scoring")
async def update_scoring_config(config: ScoringConfigUpdate):
    """
    Update scoring configuration
    
    Args:
        config: Configuration updates
        
    Returns:
        Updated configuration
    """
    try:
        # Update SCORING_CONFIG
        if config.error_weights is not None:
            SCORING_CONFIG["error_weights"].update(config.error_weights)
        
        if config.initial_score is not None:
            SCORING_CONFIG["initial_score"] = config.initial_score
        
        if config.fail_threshold is not None:
            # Map fail_threshold cũ sang ngưỡng cho chế độ testing
            thresholds = SCORING_CONFIG.setdefault("fail_thresholds", {})
            thresholds["testing"] = config.fail_threshold
        if config.multi_person_enabled is not None:
            SCORING_CONFIG["multi_person_enabled"] = config.multi_person_enabled
            # Đồng bộ sang MULTI_PERSON_CONFIG để áp dụng pipeline
            try:
                from backend.app.config import MULTI_PERSON_CONFIG
                MULTI_PERSON_CONFIG["enabled"] = bool(config.multi_person_enabled)
            except Exception:
                pass
        
        # Update ERROR_THRESHOLDS
        if config.error_thresholds is not None:
            ERROR_THRESHOLDS.update(config.error_thresholds)
        
        # Update ERROR_GROUPING_CONFIG
        if config.error_grouping is not None:
            ERROR_GROUPING_CONFIG.update(config.error_grouping)
        
        # Update difficulty_level
        if config.difficulty_level is not None:
            if config.difficulty_level not in ["easy", "medium", "hard"]:
                raise HTTPException(status_code=400, detail="difficulty_level phải là 'easy', 'medium', hoặc 'hard'")
            SCORING_CONFIG["difficulty_level"] = config.difficulty_level
        
        # Update scoring_criterion
        if config.scoring_criterion is not None:
            if config.scoring_criterion not in ["di_deu", "di_nghiem"]:
                raise HTTPException(status_code=400, detail="scoring_criterion phải là 'di_deu' hoặc 'di_nghiem'")
            SCORING_CONFIG["scoring_criterion"] = config.scoring_criterion
        
        # Update app_mode
        if config.app_mode is not None:
            if config.app_mode not in ["dev", "release"]:
                raise HTTPException(status_code=400, detail="app_mode phải là 'dev' hoặc 'release'")
            SCORING_CONFIG["app_mode"] = config.app_mode
        
        logger.info(f"Scoring configuration updated: {config.dict(exclude_none=True)}")
        
        return {
            "success": True,
            "message": "Cấu hình đã được cập nhật",
            "config": {
                "error_weights": SCORING_CONFIG.get("error_weights", {}),
                "initial_score": SCORING_CONFIG.get("initial_score", 100.0),
                "fail_threshold": SCORING_CONFIG.get("fail_thresholds", {}).get("testing", 60.0),
                # Phải khớp giá trị vừa reset (mặc định True)
                "multi_person_enabled": SCORING_CONFIG.get("multi_person_enabled", True),
                "error_thresholds": ERROR_THRESHOLDS,
                "error_grouping": ERROR_GROUPING_CONFIG
            }
        }
    except Exception as e:
        logger.error(f"Error updating scoring config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi cập nhật cấu hình: {str(e)}"
        )


@router.post("/scoring/reset")
async def reset_scoring_config():
    """
    Reset scoring configuration to defaults
    
    Returns:
        Reset confirmation
    """
    try:
        # Reset to default values
        from backend.app.config import SCORING_CONFIG, ERROR_THRESHOLDS, ERROR_GROUPING_CONFIG
        
        # Reset SCORING_CONFIG
        SCORING_CONFIG["error_weights"] = {
            "arm_angle": 1.0,
            "leg_angle": 1.0,
            "arm_height": 0.8,
            "leg_height": 0.8,
            "head_angle": 1.0,
            "torso_stability": 0.8,
            "rhythm": 1.0,
            "distance": 0.8,
            "speed": 0.8,
        }
        SCORING_CONFIG["initial_score"] = 100.0
        SCORING_CONFIG["fail_thresholds"] = {
            "testing": 60.0,
            "practising": 0.0,
            "default": 50.0,
        }
        # Giữ đúng giá trị mặc định trong config.py (multi-person mặc định bật)
        SCORING_CONFIG["multi_person_enabled"] = True
        
        # Reset ERROR_THRESHOLDS
        ERROR_THRESHOLDS.update({
            "arm_angle": 50.0,
            "leg_angle": 45.0,
            "arm_height": 50.0,
            "leg_height": 45.0,
            "head_angle": 30.0,
            "torso_stability": 0.85,
            "rhythm": 0.15,
            "distance": 50.0,
            "speed": 50.0,
        })
        
        logger.info("Scoring configuration reset to defaults")
        
        return {
            "success": True,
            "message": "Cấu hình đã được reset về mặc định",
            "config": {
                "error_weights": SCORING_CONFIG.get("error_weights", {}),
                "initial_score": SCORING_CONFIG.get("initial_score", 100.0),
                "fail_threshold": SCORING_CONFIG.get("fail_thresholds", {}).get("testing", 60.0),
                "multi_person_enabled": SCORING_CONFIG.get("multi_person_enabled", False),
                "error_thresholds": ERROR_THRESHOLDS,
                "error_grouping": ERROR_GROUPING_CONFIG
            }
        }
    except Exception as e:
        logger.error(f"Error resetting scoring config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi reset cấu hình: {str(e)}"
        )

