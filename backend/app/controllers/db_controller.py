"""
DBController - Điều khiển việc truy xuất CSDL
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from backend.app.models.person import Person
from backend.app.models.candidate import Candidate
from backend.app.utils.auth import get_password_hash, verify_password


class DBController:
    """Controller cho database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== Person Operations ==========
    
    def create_person(
        self,
        name: str,
        username: str,
        password: str,
        gender: Optional[str] = None,
        rank: Optional[str] = None,
        insignia: Optional[str] = None,
        avatar: Optional[str] = None
    ) -> tuple[Person, Optional[str]]:
        """
        Tạo person mới
        
        Returns:
            (Person, error_message)
        """
        # Kiểm tra trùng username
        existing = self.db.query(Person).filter(Person.username == username).first()
        if existing:
            return None, "Username đã tồn tại"
        
        try:
            person = Person(
                name=name,
                username=username,
                password=get_password_hash(password),
                gender=gender,
                rank=rank,
                insignia=insignia,
                avatar=avatar
            )
            self.db.add(person)
            self.db.commit()
            self.db.refresh(person)
            return person, None
        except IntegrityError as e:
            self.db.rollback()
            return None, f"Lỗi database: {str(e)}"
        except Exception as e:
            self.db.rollback()
            return None, f"Lỗi: {str(e)}"
    
    def get_person_by_username(self, username: str) -> Optional[Person]:
        """Lấy person theo username"""
        return self.db.query(Person).filter(Person.username == username).first()
    
    def get_person_by_id(self, person_id: int) -> Optional[Person]:
        """Lấy person theo ID"""
        return self.db.query(Person).filter(Person.id == person_id).first()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Person]:
        """Xác thực user"""
        person = self.get_person_by_username(username)
        if not person:
            return None
        
        if not verify_password(password, person.password):
            return None
        
        return person
    
    def update_person_token(self, person_id: int, token: str) -> bool:
        """Cập nhật token cho person"""
        person = self.get_person_by_id(person_id)
        if not person:
            return False
        
        person.token = token
        self.db.commit()
        return True
    
    # ========== Candidate Operations ==========
    
    def create_candidate(
        self,
        name: str,
        code: Optional[str] = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        unit: Optional[str] = None,
        notes: Optional[str] = None,
        created_by_id: Optional[int] = None
    ) -> tuple[Candidate, Optional[str]]:
        """Tạo candidate mới"""
        try:
            candidate = Candidate(
                name=name,
                code=code,
                age=age,
                gender=gender,
                unit=unit,
                notes=notes,
                created_by_id=created_by_id
            )
            self.db.add(candidate)
            self.db.commit()
            self.db.refresh(candidate)
            return candidate, None
        except IntegrityError as e:
            self.db.rollback()
            return None, f"Lỗi database: {str(e)}"
        except Exception as e:
            self.db.rollback()
            return None, f"Lỗi: {str(e)}"
    
    def get_all_candidates(self, created_by_id: Optional[int] = None) -> List[Candidate]:
        """Lấy tất cả candidates"""
        query = self.db.query(Candidate)
        if created_by_id:
            query = query.filter(Candidate.created_by_id == created_by_id)
        return query.order_by(Candidate.created_at.desc()).all()
    
    def get_candidate_by_id(self, candidate_id: int) -> Optional[Candidate]:
        """Lấy candidate theo ID"""
        return self.db.query(Candidate).filter(Candidate.id == candidate_id).first()
    
    def update_candidate(self, candidate_id: int, **kwargs) -> tuple[bool, Optional[str]]:
        """Cập nhật candidate"""
        candidate = self.get_candidate_by_id(candidate_id)
        if not candidate:
            return False, "Không tìm thấy candidate"
        
        try:
            for key, value in kwargs.items():
                if hasattr(candidate, key):
                    setattr(candidate, key, value)
            self.db.commit()
            self.db.refresh(candidate)
            return True, None
        except Exception as e:
            self.db.rollback()
            return False, f"Lỗi: {str(e)}"
    
    def delete_candidate(self, candidate_id: int) -> tuple[bool, Optional[str]]:
        """Xóa candidate"""
        candidate = self.get_candidate_by_id(candidate_id)
        if not candidate:
            return False, "Không tìm thấy candidate"
        
        try:
            self.db.delete(candidate)
            self.db.commit()
            return True, None
        except Exception as e:
            self.db.rollback()
            return False, f"Lỗi: {str(e)}"

