"""
SummaryController - Tổng hợp danh sách các phiên chấm
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from backend.app.models.session import ScoringSession, SessionMode, SessionType
from backend.app.models.score import Score


class SummaryController:
    """Controller cho màn hình Summary"""

    def __init__(self, db: Session):
        self.db = db

    def list_results(self, limit: int = 100) -> List[Dict]:
        """Liệt kê kết quả của các phiên chấm"""
        sessions = (
            self.db.query(ScoringSession)
            .order_by(ScoringSession.started_at.desc())
            .limit(limit)
            .all()
        )
        results = []
        for s in sessions:
            score = self.db.query(Score).filter(Score.session_id == s.id).first()
            results.append({
                "id": s.id,
                "candidate_id": s.candidate_id,
                "mode": s.mode.value,
                "session_type": s.session_type.value,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "score": score.value if score else None,
                "is_passed": score.is_passed() if score else None if score else None,
            })
        return results

    def delete_session(self, session_id: int) -> bool:
        """Xoá session (mềm - soft delete: tạm thời xóa)"""
        session = self.db.query(ScoringSession).filter(ScoringSession.id == session_id).first()
        if not session:
            return False
        self.db.delete(session)
        self.db.commit()
        return True

