"""
LoginController - Điều khiển việc đăng nhập
"""
from typing import Dict, Optional, Tuple
from backend.app.controllers.db_controller import DBController
from backend.app.models.person import Person
from backend.app.utils.auth import create_access_token


class LoginController:
    """Controller cho đăng nhập"""
    
    def __init__(self, db_controller: DBController):
        self.db_controller = db_controller
    
    def validate(self, data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate dữ liệu đăng nhập
        
        Args:
            data: Dict chứa username, password
            
        Returns:
            (is_valid, error_message)
        """
        if not data.get("username"):
            return False, "Thiếu username"
        if not data.get("password"):
            return False, "Thiếu password"
        
        return True, None
    
    def login(self, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Đăng nhập user
        
        Args:
            data: Dict chứa username, password
            
        Returns:
            (user_data, error_message)
            user_data: {"person": Person, "token": str}
        """
        # Validate
        is_valid, error = self.validate(data)
        if not is_valid:
            return None, error
        
        # Authenticate
        person = self.db_controller.authenticate_user(
            username=data.get("username"),
            password=data.get("password")
        )
        
        if not person:
            return None, "Sai username hoặc password"
        
        # Tạo token
        token = create_access_token(data={"sub": person.username, "person_id": person.id})
        
        # Cập nhật token vào database
        self.db_controller.update_person_token(person.id, token)
        
        return {
            "person": person,
            "token": token
        }, None

