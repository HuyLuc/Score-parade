"""
Service for database operations - Lưu sessions, errors, và persons vào database
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID

from backend.app.database.connection import db_session
from backend.app.database.models import Session, Person, Error, GoldenTemplate, Config

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service để lưu và truy vấn dữ liệu từ database"""

    @staticmethod
    def create_or_update_session(
        session_id: str,
        mode: str = "testing",
        status: str = "active",
        total_frames: int = 0,
        video_path: Optional[str] = None,
        skeleton_video_url: Optional[str] = None,
    ) -> Optional[Session]:
        """Tạo hoặc cập nhật session"""
        try:
            with db_session() as db:
                # Tìm session hiện có
                session = db.query(Session).filter(Session.session_id == session_id).first()
                
                if session:
                    # Cập nhật
                    session.mode = mode
                    session.status = status
                    session.total_frames = total_frames
                    if video_path is not None:
                        session.video_path = video_path
                    if skeleton_video_url is not None:
                        session.skeleton_video_url = skeleton_video_url
                    if status == "completed":
                        session.end_time = datetime.utcnow()
                    logger.debug(f"✅ Updated session: {session_id}")
                else:
                    # Tạo mới
                    session = Session(
                        session_id=session_id,
                        mode=mode,
                        status=status,
                        total_frames=total_frames,
                        video_path=video_path,
                        skeleton_video_url=skeleton_video_url,
                    )
                    db.add(session)
                    logger.info(f"✅ Created session: {session_id}")
                
                db.commit()
                return session
        except Exception as e:
            logger.error(f"❌ Error creating/updating session {session_id}: {e}")
            return None

    @staticmethod
    def create_or_update_person(
        session_id: str,
        person_id: int,
        score: float = 100.0,
        total_errors: int = 0,
        status: str = "active",
        first_frame: Optional[int] = None,
        last_frame: Optional[int] = None
    ) -> Optional[Person]:
        """Tạo hoặc cập nhật person trong session"""
        try:
            with db_session() as db:
                # Tìm session
                session = db.query(Session).filter(Session.session_id == session_id).first()
                if not session:
                    logger.error(f"❌ Session not found: {session_id}")
                    return None

                # Tìm person hiện có
                person = db.query(Person).filter(
                    Person.session_id == session.id,
                    Person.person_id == person_id
                ).first()

                if person:
                    # Cập nhật
                    person.score = score
                    person.total_errors = total_errors
                    person.status = status
                    if first_frame is not None:
                        person.first_frame = first_frame
                    if last_frame is not None:
                        person.last_frame = last_frame
                    logger.debug(f"✅ Updated person {person_id} in session {session_id}")
                else:
                    # Tạo mới
                    person = Person(
                        session_id=session.id,
                        person_id=person_id,
                        score=score,
                        total_errors=total_errors,
                        status=status,
                        first_frame=first_frame,
                        last_frame=last_frame
                    )
                    db.add(person)
                    logger.info(f"✅ Created person {person_id} in session {session_id}")

                db.commit()
                return person
        except Exception as e:
            logger.error(f"❌ Error creating/updating person {person_id} in session {session_id}: {e}")
            return None

    @staticmethod
    def save_error(
        session_id: str,
        person_id: int,
        error_type: str,
        severity: float,
        deduction: float,
        message: Optional[str] = None,
        frame_number: Optional[int] = None,
        timestamp_sec: Optional[float] = None,
        is_sequence: bool = False,
        sequence_length: Optional[int] = None,
        start_frame: Optional[int] = None,
        end_frame: Optional[int] = None
    ) -> Optional[Error]:
        """Lưu error vào database"""
        try:
            with db_session() as db:
                # Tìm session
                session = db.query(Session).filter(Session.session_id == session_id).first()
                if not session:
                    logger.error(f"❌ Session not found: {session_id}")
                    return None

                # Tạo error
                error = Error(
                    session_id=session.id,
                    person_id=person_id,
                    error_type=error_type,
                    severity=severity,
                    deduction=deduction,
                    message=message,
                    frame_number=frame_number,
                    timestamp_sec=timestamp_sec,
                    is_sequence=is_sequence,
                    sequence_length=sequence_length,
                    start_frame=start_frame,
                    end_frame=end_frame
                )
                db.add(error)
                db.commit()
                logger.debug(f"✅ Saved error: {error_type} for person {person_id} in session {session_id}")
                return error
        except Exception as e:
            logger.error(f"❌ Error saving error for person {person_id} in session {session_id}: {e}")
            return None

    @staticmethod
    def save_errors_batch(
        session_id: str,
        errors: List[Dict]
    ) -> int:
        """Lưu nhiều errors cùng lúc (batch insert)"""
        try:
            with db_session() as db:
                # Tìm session
                session = db.query(Session).filter(Session.session_id == session_id).first()
                if not session:
                    logger.error(f"❌ Session not found: {session_id}")
                    return 0

                # Tạo errors
                error_objects = []
                for err in errors:
                    error_obj = Error(
                        session_id=session.id,
                        person_id=err.get("person_id", 0),
                        error_type=err.get("error_type"),
                        severity=err.get("severity", 0.0),
                        deduction=err.get("deduction", 0.0),
                        message=err.get("message"),
                        frame_number=err.get("frame_number"),
                        timestamp_sec=err.get("timestamp_sec"),
                        is_sequence=err.get("is_sequence", False),
                        sequence_length=err.get("sequence_length"),
                        start_frame=err.get("start_frame"),
                        end_frame=err.get("end_frame")
                    )
                    error_objects.append(error_obj)

                db.bulk_save_objects(error_objects)
                db.commit()
                logger.info(f"✅ Saved {len(error_objects)} errors in batch for session {session_id}")
                return len(error_objects)
        except Exception as e:
            logger.error(f"❌ Error saving errors batch for session {session_id}: {e}")
            return 0

    @staticmethod
    def get_session(session_id: str) -> Optional[Session]:
        """Lấy session từ database"""
        try:
            with db_session() as db:
                return db.query(Session).filter(Session.session_id == session_id).first()
        except Exception as e:
            logger.error(f"❌ Error getting session {session_id}: {e}")
            return None

    @staticmethod
    def get_session_persons(session_id: str) -> List[Person]:
        """Lấy tất cả persons trong session"""
        try:
            with db_session() as db:
                session = db.query(Session).filter(Session.session_id == session_id).first()
                if not session:
                    return []
                return db.query(Person).filter(Person.session_id == session.id).all()
        except Exception as e:
            logger.error(f"❌ Error getting persons for session {session_id}: {e}")
            return []

    @staticmethod
    def get_session_errors(
        session_id: str,
        person_id: Optional[int] = None
    ) -> List[Error]:
        """Lấy errors của session (có thể filter theo person_id)"""
        try:
            with db_session() as db:
                session = db.query(Session).filter(Session.session_id == session_id).first()
                if not session:
                    return []

                query = db.query(Error).filter(Error.session_id == session.id)
                if person_id is not None:
                    query = query.filter(Error.person_id == person_id)

                return query.order_by(Error.frame_number).all()
        except Exception as e:
            logger.error(f"❌ Error getting errors for session {session_id}: {e}")
            return []

    @staticmethod
    def complete_session(session_id: str) -> bool:
        """Đánh dấu session là completed"""
        try:
            with db_session() as db:
                session = db.query(Session).filter(Session.session_id == session_id).first()
                if session:
                    session.status = "completed"
                    session.end_time = datetime.utcnow()
                    db.commit()
                    logger.info(f"✅ Completed session: {session_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"❌ Error completing session {session_id}: {e}")
            return False

    # -----------------------------
    # Helpers for API fallback
    # -----------------------------
    @staticmethod
    def get_scores_map(session_id: str) -> Dict[int, float]:
        """Trả về dict person_id -> score cho session (từ DB)."""
        try:
            with db_session() as db:
                session = db.query(Session).filter(Session.session_id == session_id).first()
                if not session:
                    return {}
                persons = db.query(Person).filter(Person.session_id == session.id).all()
                return {p.person_id: float(p.score) for p in persons}
        except Exception as e:
            logger.error(f"❌ Error getting scores map for session {session_id}: {e}")
            return {}

    @staticmethod
    def get_errors_map(session_id: str, person_id: Optional[int] = None) -> Dict[int, List[Dict]]:
        """Trả về dict person_id -> list errors (đã serialize) từ DB."""
        try:
            with db_session() as db:
                session = db.query(Session).filter(Session.session_id == session_id).first()
                if not session:
                    return {}

                query = db.query(Error).filter(Error.session_id == session.id)
                if person_id is not None:
                    query = query.filter(Error.person_id == person_id)
                errors = query.order_by(Error.frame_number).all()

                result: Dict[int, List[Dict]] = {}
                for err in errors:
                    pid = err.person_id
                    result.setdefault(pid, []).append({
                        "person_id": pid,
                        "type": err.error_type,
                        "severity": err.severity,
                        "deduction": err.deduction,
                        "message": err.message,
                        "frame_number": err.frame_number,
                        "timestamp": err.timestamp_sec,
                        "is_sequence": err.is_sequence,
                        "sequence_length": err.sequence_length,
                        "start_frame": err.start_frame,
                        "end_frame": err.end_frame,
                    })
                return result
        except Exception as e:
            logger.error(f"❌ Error getting errors map for session {session_id}: {e}")
            return {}

    @staticmethod
    def delete_session_data(session_id: str) -> bool:
        """Xóa dữ liệu session (persons, errors) và đặt trạng thái cancelled."""
        try:
            with db_session() as db:
                session = db.query(Session).filter(Session.session_id == session_id).first()
                if not session:
                    return False
                # Cascade delete via relationships
                db.delete(session)
                db.commit()
                logger.info(f"✅ Deleted session data for {session_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Error deleting session data for {session_id}: {e}")
            return False

