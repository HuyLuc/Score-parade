"""
ConfigurationController - Điều khiển việc cấu hình hệ thống
"""
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.controllers.db_controller import DBController
from backend.app.models.person import Person
from backend.app.utils.auth import get_password_hash, verify_password


class ConfigurationController:
    """Controller cho configuration"""
    
    def __init__(self, db_controller: DBController):
        self.db_controller = db_controller
    
    def change_password(
        self,
        person_id: int,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Đổi mật khẩu
        
        Args:
            person_id: ID của person
            old_password: Mật khẩu cũ
            new_password: Mật khẩu mới
            
        Returns:
            (success, error_message)
        """
        # Lấy person
        person = self.db_controller.get_person_by_id(person_id)
        if not person:
            return False, "Không tìm thấy user"
        
        # Kiểm tra mật khẩu cũ
        if not verify_password(old_password, person.password):
            return False, "Mật khẩu cũ không đúng"
        
        # Validate mật khẩu mới
        if len(new_password) < 6:
            return False, "Mật khẩu mới phải có ít nhất 6 ký tự"
        
        # Cập nhật mật khẩu
        person.password = get_password_hash(new_password)
        self.db_controller.db.commit()
        
        return True, None
    
    def get_configuration(self, person_id: int) -> Dict:
        """
        Lấy cấu hình của user
        
        Returns:
            Dict chứa các cấu hình
        """
        # Có thể lưu config trong database hoặc file
        # Tạm thời trả về default config
        return {
            "mode": "testing",  # testing hoặc practising
            "criteria": "di_deu",  # di_deu hoặc di_nghiem
            "difficulty": "normal",  # easy, normal, hard
            "operation_mode": "release",  # dev hoặc release
        }
    
    def update_configuration(
        self,
        person_id: int,
        mode: Optional[str] = None,
        criteria: Optional[str] = None,
        difficulty: Optional[str] = None,
        operation_mode: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Cập nhật cấu hình
        
        Args:
            person_id: ID của person
            mode: Chế độ (testing/practising)
            criteria: Tiêu chí (di_deu/di_nghiem)
            difficulty: Mức độ khắt khe (easy/normal/hard)
            operation_mode: Chế độ hoạt động (dev/release)
            
        Returns:
            (success, error_message)
        """
        # Validate
        if mode and mode not in ["testing", "practising"]:
            return False, "Mode phải là 'testing' hoặc 'practising'"
        
        if criteria and criteria not in ["di_deu", "di_nghiem"]:
            return False, "Criteria phải là 'di_deu' hoặc 'di_nghiem'"
        
        if difficulty and difficulty not in ["easy", "normal", "hard"]:
            return False, "Difficulty phải là 'easy', 'normal' hoặc 'hard'"
        
        if operation_mode and operation_mode not in ["dev", "release"]:
            return False, "Operation mode phải là 'dev' hoặc 'release'"
        
        # Có thể lưu vào database hoặc file
        # Tạm thời chỉ validate, chưa lưu
        
        return True, None

