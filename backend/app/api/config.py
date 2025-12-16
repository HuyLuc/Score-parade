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
    error_thresholds: Dict[str, float]
    error_grouping: Dict[str, Any]


class ScoringConfigUpdate(BaseModel):
    """Request model for updating scoring configuration"""
    error_weights: Dict[str, float] = None
    initial_score: float = None
    fail_threshold: float = None  # Giữ để tương thích, sẽ map sang fail_thresholds["testing"]
    error_thresholds: Dict[str, float] = None
    error_grouping: Dict[str, Any] = None


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
            fail_threshold=SCORING_CONFIG.get("fail_thresholds", {}).get("testing", 60.0),
            error_thresholds=ERROR_THRESHOLDS,
            error_grouping=ERROR_GROUPING_CONFIG
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
        
        # Update ERROR_THRESHOLDS
        if config.error_thresholds is not None:
            ERROR_THRESHOLDS.update(config.error_thresholds)
        
        # Update ERROR_GROUPING_CONFIG
        if config.error_grouping is not None:
            ERROR_GROUPING_CONFIG.update(config.error_grouping)
        
        logger.info(f"Scoring configuration updated: {config.dict(exclude_none=True)}")
        
        return {
            "success": True,
            "message": "Cấu hình đã được cập nhật",
            "config": {
                "error_weights": SCORING_CONFIG.get("error_weights", {}),
                "initial_score": SCORING_CONFIG.get("initial_score", 100.0),
                "fail_threshold": SCORING_CONFIG.get("fail_thresholds", {}).get("testing", 60.0),
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

