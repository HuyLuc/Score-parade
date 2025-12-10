"""
CandidateController - Điều khiển việc quản lý thí sinh
"""
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.controllers.db_controller import DBController
from backend.app.models.candidate import Candidate, CandidateStatus
import pandas as pd
from io import BytesIO


class CandidateController:
    """Controller cho candidate management"""
    
    def __init__(self, db_controller: DBController):
        self.db_controller = db_controller
    
    def validate_candidate_data(self, data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate dữ liệu candidate
        
        Args:
            data: Dict chứa name, code, age, gender, unit, notes
            
        Returns:
            (is_valid, error_message)
        """
        # Kiểm tra name (bắt buộc)
        if not data.get("name") or not data.get("name").strip():
            return False, "Tên thí sinh không được để trống"
        
        # Validate code (nếu có)
        code = data.get("code")
        if code:
            code = code.strip()
            if len(code) < 2:
                return False, "Mã thí sinh phải có ít nhất 2 ký tự"
        
        # Validate age (nếu có)
        age = data.get("age")
        if age is not None:
            try:
                age = int(age)
                if age < 1 or age > 150:
                    return False, "Tuổi phải từ 1 đến 150"
            except (ValueError, TypeError):
                return False, "Tuổi không hợp lệ"
        
        # Validate gender (nếu có)
        gender = data.get("gender")
        if gender and gender not in ["male", "female", "nam", "nữ"]:
            return False, "Giới tính không hợp lệ"
        
        return True, None
    
    def create_candidate(self, data: Dict, created_by_id: Optional[int] = None) -> Tuple[Optional[Candidate], Optional[str]]:
        """
        Tạo candidate mới
        
        Args:
            data: Dict chứa thông tin candidate
            created_by_id: ID của person tạo candidate
            
        Returns:
            (Candidate, error_message)
        """
        # Validate
        is_valid, error = self.validate_candidate_data(data)
        if not is_valid:
            return None, error
        
        # Tạo candidate
        candidate, error = self.db_controller.create_candidate(
            name=data.get("name").strip(),
            code=data.get("code", "").strip() if data.get("code") else None,
            age=int(data.get("age")) if data.get("age") else None,
            gender=data.get("gender"),
            unit=data.get("unit"),
            notes=data.get("notes"),
            created_by_id=created_by_id
        )
        
        if error:
            return None, error
        
        return candidate, None
    
    def import_from_excel(self, file_content: bytes, created_by_id: Optional[int] = None) -> Tuple[List[Candidate], List[str]]:
        """
        Import candidates từ file Excel
        
        Args:
            file_content: Nội dung file Excel (bytes)
            created_by_id: ID của person import
            
        Returns:
            (list_of_created_candidates, list_of_errors)
        """
        errors = []
        created_candidates = []
        
        try:
            # Đọc Excel (pandas tự động detect engine: openpyxl cho .xlsx, xlrd cho .xls)
            df = pd.read_excel(BytesIO(file_content), engine=None)  # engine=None để auto-detect
            
            # Kiểm tra các cột bắt buộc
            required_columns = ["name"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                errors.append(f"Thiếu các cột: {', '.join(missing_columns)}")
                return [], errors
            
            # Xử lý từng dòng
            for idx, row in df.iterrows():
                try:
                    data = {
                        "name": str(row.get("name", "")).strip(),
                        "code": str(row.get("code", "")).strip() if pd.notna(row.get("code")) else None,
                        "age": int(row.get("age")) if pd.notna(row.get("age")) else None,
                        "gender": str(row.get("gender", "")).strip() if pd.notna(row.get("gender")) else None,
                        "unit": str(row.get("unit", "")).strip() if pd.notna(row.get("unit")) else None,
                        "notes": str(row.get("notes", "")).strip() if pd.notna(row.get("notes")) else None,
                    }
                    
                    # Validate và tạo
                    candidate, error = self.create_candidate(data, created_by_id)
                    
                    if error:
                        errors.append(f"Dòng {idx + 2}: {error}")
                    else:
                        created_candidates.append(candidate)
                
                except Exception as e:
                    errors.append(f"Dòng {idx + 2}: Lỗi xử lý - {str(e)}")
        
        except Exception as e:
            errors.append(f"Lỗi đọc file Excel: {str(e)}")
        
        return created_candidates, errors
    
    def get_all_candidates(self, created_by_id: Optional[int] = None) -> List[Candidate]:
        """Lấy tất cả candidates"""
        return self.db_controller.get_all_candidates(created_by_id)
    
    def get_candidate_by_id(self, candidate_id: int) -> Optional[Candidate]:
        """Lấy candidate theo ID"""
        return self.db_controller.get_candidate_by_id(candidate_id)
    
    def update_candidate(self, candidate_id: int, data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Cập nhật candidate
        
        Args:
            candidate_id: ID của candidate
            data: Dict chứa các trường cần cập nhật
            
        Returns:
            (success, error_message)
        """
        # Validate
        is_valid, error = self.validate_candidate_data(data)
        if not is_valid:
            return False, error
        
        # Chuẩn hóa data
        update_data = {}
        if "name" in data:
            update_data["name"] = data["name"].strip()
        if "code" in data:
            update_data["code"] = data["code"].strip() if data["code"] else None
        if "age" in data:
            update_data["age"] = int(data["age"]) if data["age"] else None
        if "gender" in data:
            update_data["gender"] = data["gender"]
        if "unit" in data:
            update_data["unit"] = data["unit"]
        if "notes" in data:
            update_data["notes"] = data["notes"]
        
        # Cập nhật
        success, error = self.db_controller.update_candidate(candidate_id, **update_data)
        return success, error
    
    def delete_candidate(self, candidate_id: int) -> Tuple[bool, Optional[str]]:
        """Xóa candidate"""
        return self.db_controller.delete_candidate(candidate_id)
    
    def select_candidate(self, candidate_id: int) -> Tuple[Optional[Candidate], Optional[str]]:
        """
        Chọn candidate (đánh dấu là đang được chọn)
        
        Args:
            candidate_id: ID của candidate
            
        Returns:
            (Candidate, error_message)
        """
        candidate = self.get_candidate_by_id(candidate_id)
        if not candidate:
            return None, "Không tìm thấy candidate"
        
        # Có thể cập nhật status thành IN_PROGRESS nếu cần
        # Hoặc chỉ trả về candidate để frontend xử lý
        
        return candidate, None

