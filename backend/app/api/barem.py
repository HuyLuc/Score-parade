"""
Barem API endpoints - Hiển thị tiêu chí chấm điểm và điểm trừ
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel

from backend.app.database.connection import get_db
from backend.app.config import SCORING_CONFIG, ERROR_THRESHOLDS

router = APIRouter(prefix="/api/barem", tags=["barem"])


class CriterionResponse(BaseModel):
    """Tiêu chí chấm điểm"""
    id: str
    name: str
    description: str
    error_type: str
    weight: float
    threshold: float
    deduction_per_error: float
    examples: List[str]


@router.get("", response_model=List[CriterionResponse])
async def get_barem(
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách tất cả tiêu chí chấm điểm (Barem)
    
    Returns:
        Danh sách các tiêu chí với thông tin điểm trừ
    """
    error_weights = SCORING_CONFIG.get("error_weights", {})
    error_thresholds = ERROR_THRESHOLDS
    
    criteria = []
    
    # 1. Tay (Arm)
    criteria.append(CriterionResponse(
        id="arm_angle",
        name="Góc Tay",
        description="Kiểm tra góc tay có đúng tư thế chuẩn không (quá cao/quá thấp)",
        error_type="arm_angle",
        weight=error_weights.get("arm_angle", 1.0),
        threshold=error_thresholds.get("arm_angle", 50.0),
        deduction_per_error=error_weights.get("arm_angle", 1.0) * 1.0,  # weight * severity
        examples=[
            "Tay trái quá cao",
            "Tay phải quá thấp",
            "Góc tay không đúng tư thế"
        ]
    ))
    
    # 2. Chân (Leg)
    criteria.append(CriterionResponse(
        id="leg_angle",
        name="Góc Chân",
        description="Kiểm tra góc chân có đúng tư thế chuẩn không",
        error_type="leg_angle",
        weight=error_weights.get("leg_angle", 1.0),
        threshold=error_thresholds.get("leg_angle", 45.0),
        deduction_per_error=error_weights.get("leg_angle", 1.0) * 1.0,
        examples=[
            "Chân trái quá cao",
            "Chân phải quá thấp",
            "Góc chân không đúng tư thế"
        ]
    ))
    
    # 3. Đầu (Head)
    criteria.append(CriterionResponse(
        id="head_angle",
        name="Góc Đầu",
        description="Kiểm tra đầu có cúi quá thấp hoặc ngẩng quá cao không",
        error_type="head_angle",
        weight=error_weights.get("head_angle", 1.0),
        threshold=error_thresholds.get("head_angle", 30.0),
        deduction_per_error=error_weights.get("head_angle", 1.0) * 1.0,
        examples=[
            "Đầu cúi quá thấp",
            "Đầu ngẩng quá cao"
        ]
    ))
    
    # 4. Cổ (Neck)
    criteria.append(CriterionResponse(
        id="neck_angle",
        name="Góc Cổ",
        description="Kiểm tra cổ có thẳng không",
        error_type="neck_angle",
        weight=error_weights.get("neck_angle", 0.9),
        threshold=error_thresholds.get("neck_angle", 25.0),
        deduction_per_error=error_weights.get("neck_angle", 0.9) * 1.0,
        examples=[
            "Cổ cúi quá thấp",
            "Cổ ngẩng quá cao"
        ]
    ))
    
    # 5. Vai (Shoulder)
    criteria.append(CriterionResponse(
        id="torso_stability",
        name="Ổn Định Thân Người",
        description="Kiểm tra vai có cân bằng không, thân người có ổn định không",
        error_type="torso_stability",
        weight=error_weights.get("torso_stability", 0.8),
        threshold=error_thresholds.get("torso_stability", 0.85),
        deduction_per_error=error_weights.get("torso_stability", 0.8) * 1.0,
        examples=[
            "Vai không cân bằng",
            "Thân người không ổn định"
        ]
    ))
    
    # 6. Nhịp (Rhythm)
    criteria.append(CriterionResponse(
        id="rhythm",
        name="Đồng Bộ Nhịp",
        description="Kiểm tra động tác có theo đúng nhịp nhạc không",
        error_type="rhythm",
        weight=error_weights.get("rhythm", 1.0),
        threshold=error_thresholds.get("rhythm", 0.15),  # 150ms tolerance
        deduction_per_error=error_weights.get("rhythm", 1.0) * 1.0,
        examples=[
            "Động tác không theo nhịp (lệch > 150ms)",
            "Bước chân không đồng bộ với nhạc",
            "Vung tay không đúng nhịp"
        ]
    ))
    
    # 7. Khoảng Cách (Distance)
    criteria.append(CriterionResponse(
        id="distance",
        name="Khoảng Cách",
        description="Kiểm tra bước chân và vung tay có quá dài/quá xa so với quy định không",
        error_type="distance",
        weight=error_weights.get("distance", 0.8),
        threshold=error_thresholds.get("distance", 50.0),
        deduction_per_error=error_weights.get("distance", 0.8) * 1.0,
        examples=[
            "Bước chân quá dài",
            "Vung tay quá xa"
        ]
    ))
    
    # 8. Tốc Độ (Speed)
    criteria.append(CriterionResponse(
        id="speed",
        name="Tốc Độ",
        description="Kiểm tra tốc độ thực hiện động tác có quá nhanh hay quá chậm không",
        error_type="speed",
        weight=error_weights.get("speed", 0.8),
        threshold=error_thresholds.get("speed", 80.0),
        deduction_per_error=error_weights.get("speed", 0.8) * 1.0,
        examples=[
            "Thực hiện động tác quá nhanh",
            "Thực hiện động tác quá chậm"
        ]
    ))
    
    return criteria


@router.get("/weights", response_model=Dict[str, float])
async def get_error_weights():
    """
    Lấy trọng số điểm trừ cho từng loại lỗi
    
    Returns:
        Dict mapping error_type -> weight
    """
    return SCORING_CONFIG.get("error_weights", {})


@router.get("/thresholds", response_model=Dict[str, float])
async def get_error_thresholds():
    """
    Lấy ngưỡng sai lệch cho từng loại lỗi
    
    Returns:
        Dict mapping error_type -> threshold
    """
    return ERROR_THRESHOLDS

