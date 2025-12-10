"""
EndOfSectionController - Tổng hợp kết quả sau khi chấm xong (Local + Global)
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from backend.app.models.session import ScoringSession, SessionType, SessionMode, Error
from backend.app.models.score import Score


class EndOfSectionController:
    """Controller tổng hợp kết quả cho một session"""

    def __init__(self, db: Session):
        self.db = db

    def get_session_result(self, session_id: int) -> Dict:
        """Lấy kết quả cuối cho một session"""
        session = self.db.query(ScoringSession).filter(ScoringSession.id == session_id).first()
        if not session:
            return {}

        score = self.db.query(Score).filter(Score.session_id == session_id).first()
        errors = self.db.query(Error).filter(Error.session_id == session_id).all()

        # Phân loại lỗi theo loại (local vs global)
        local_errors = []
        global_errors = []
        for e in errors:
            # Tạm thời phân loại theo session_type của session
            if session.session_type == SessionType.LOCAL:
                local_errors.append(e)
            else:
                global_errors.append(e)

        def _serialize_error(e: Error) -> Dict:
            return {
                "id": e.id,
                "type": e.error_type,
                "description": e.description,
                "severity": e.severity,
                "deduction": e.deduction,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "snapshot_path": e.snapshot_path,
                "video_path": getattr(e, "video_path", None),
                "video_start_time": getattr(e, "video_start_time", None),
                "video_end_time": getattr(e, "video_end_time", None),
            }

        return {
            "session_id": session.id,
            "candidate_id": session.candidate_id,
            "mode": session.mode.value,
            "session_type": session.session_type.value,
            "score": {
                "value": score.value if score else None,
                "initial_value": score.initial_value if score else None,
                "is_passed": score.is_passed() if score else None,
                "deductions": score.list_of_modified_times if score else [],
            },
            "local_errors": [_serialize_error(e) for e in local_errors],
            "global_errors": [_serialize_error(e) for e in global_errors],
        }

    def list_sessions(self, limit: int = 50) -> List[Dict]:
        """Liệt kê các phiên chấm gần đây"""
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
            })
        return results

