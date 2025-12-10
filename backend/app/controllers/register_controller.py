"""
RegisterController - Điều khiển việc đăng ký
"""
from typing import Dict, Optional, Tuple
from backend.app.controllers.db_controller import DBController
from backend.app.models.person import Person
from backend.app.utils.exceptions import ValidationException


class RegisterController:
    """Controller cho đăng ký"""
    
    def __init__(self, db_controller: DBController):
        self.db_controller = db_controller
    
    def validate(self, data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate dữ liệu đăng ký
        
        Args:
            data: Dict chứa name, username, password, age, rank, insignia, avatar
            
        Returns:
            (is_valid, error_message)
        """
        # Kiểm tra các trường bắt buộc
        required_fields = ["name", "username", "password"]
        for field in required_fields:
            if not data.get(field):
                return False, f"Thiếu trường: {field}"
        
        # Validate username
        username = data.get("username", "").strip()
        if len(username) < 3:
            return False, "Username phải có ít nhất 3 ký tự"
        if not username.isalnum():
            return False, "Username chỉ được chứa chữ cái và số"
        
        # Validate password
        password = data.get("password", "")
        if len(password) < 6:
            return False, "Mật khẩu phải có ít nhất 6 ký tự"
        
        # Validate age (nếu có)
        age = data.get("age")
        if age is not None:
            try:
                age = int(age)
                if age < 18 or age > 100:
                    return False, "Tuổi phải từ 18 đến 100"
            except (ValueError, TypeError):
                return False, "Tuổi không hợp lệ"
        
        return True, None
    
    def register(self, data: Dict) -> Person:
        """
        Register a new user
        
        Args:
            data: Dict containing registration info
            
        Returns:
            Person object
            
        Raises:
            ValidationException: If validation fails
            DatabaseException: If database operation fails
        """
        # Validate
        is_valid, error = self.validate(data)
        if not is_valid:
            raise ValidationException(error)
        
        # Create person (will raise exceptions if fails)
        person = self.db_controller.create_person(
            name=data.get("name"),
            username=data.get("username"),
            password=data.get("password"),
            gender=data.get("gender"),
            rank=data.get("rank"),
            insignia=data.get("insignia"),
            avatar=data.get("avatar")
        )
        
        return person

