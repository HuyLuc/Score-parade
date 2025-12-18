"""
Sessions API endpoints - liệt kê các phiên chấm điểm đã lưu trong database
"""
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Query

from backend.app.database.connection import db_session
from backend.app.database.models import Session, Person

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: active/completed/cancelled"),
) -> Dict[str, Any]:
    """
    Trả về danh sách sessions đã lưu trong DB (kèm điểm và tổng lỗi tổng hợp).
    """
    with db_session() as db:
        query = db.query(Session)
        if status:
            query = query.filter(Session.status == status)

        total = query.count()
        sessions: List[Session] = (
            query.order_by(Session.start_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        if not sessions:
            return {"items": [], "total": total}

        # Lấy persons cho tất cả sessions để tính điểm & tổng lỗi
        session_ids = [s.id for s in sessions]
        persons: List[Person] = (
            db.query(Person)
            .filter(Person.session_id.in_(session_ids))
            .all()
        )

        persons_map: Dict[Any, List[Person]] = {}
        for p in persons:
            persons_map.setdefault(p.session_id, []).append(p)

        items: List[Dict[str, Any]] = []
        for s in sessions:
            persons_for_session = persons_map.get(s.id, [])

            if persons_for_session:
                # Điểm: lấy điểm cao nhất trong session (hoặc có thể đổi sang trung bình nếu cần)
                max_score = max(float(p.score or 0.0) for p in persons_for_session)
                # Tổng lỗi: cộng tất cả người
                total_errors = sum(int(p.total_errors or 0) for p in persons_for_session)
            else:
                max_score = 0.0
                total_errors = 0

            # Chuẩn hóa mode về 'testing' | 'practising' cho frontend
            raw_mode = (s.mode or "testing").lower()
            if raw_mode.startswith("local_"):
                raw_mode = raw_mode.replace("local_", "")
            frontend_mode = raw_mode if raw_mode in ("testing", "practising") else "testing"

            items.append(
                {
                    "id": s.session_id,
                    "mode": frontend_mode,
                    "startTime": s.start_time,
                    "status": s.status or "active",
                    "score": max_score,
                    "totalErrors": total_errors,
                    "audioSet": False,
                }
            )

        return {"items": items, "total": total}


