"""
Error Grouping Service - Nhóm các lỗi liên tiếp để tránh phạt trùng lặp
"""
from typing import List, Dict, Optional
from collections import defaultdict
from backend.app.config import ERROR_GROUPING_CONFIG


class ErrorGroupingService:
    """
    Service để nhóm các lỗi liên tiếp lại với nhau
    Tránh phạt nhiều lần cho cùng một lỗi kéo dài
    """
    
    def __init__(self):
        self.config = ERROR_GROUPING_CONFIG
        self.error_sequences = defaultdict(list)  # {error_key: [frames]}
        self.processed_errors = []  # Các lỗi đã được xử lý và nhóm
        
    def group_errors(self, frame_errors: List[Dict], frame_number: int) -> List[Dict]:
        """
        Nhóm các lỗi liên tiếp lại với nhau
        
        Args:
            frame_errors: Danh sách lỗi từ frame hiện tại
            frame_number: Số frame hiện tại
            
        Returns:
            Danh sách lỗi đã được nhóm (chỉ trả về lỗi mới bắt đầu hoặc kết thúc)
        """
        if not self.config.get("enabled", True):
            # Nếu không bật grouping, trả về tất cả lỗi
            return frame_errors
        
        new_errors = []
        min_sequence_length = self.config.get("min_sequence_length", 3)
        max_gap_frames = self.config.get("max_gap_frames", 5)
        
        # Tạo key cho mỗi loại lỗi (type + body_part + side)
        error_keys = set()
        for error in frame_errors:
            error_key = self._get_error_key(error)
            error_keys.add(error_key)
            
            # Thêm frame vào sequence
            if error_key not in self.error_sequences:
                self.error_sequences[error_key] = []
            
            # Kiểm tra gap với frame cuối cùng
            if len(self.error_sequences[error_key]) > 0:
                last_frame = self.error_sequences[error_key][-1]
                gap = frame_number - last_frame
                
                # Nếu gap quá lớn, coi như sequence mới
                if gap > max_gap_frames:
                    # Kết thúc sequence cũ và tạo sequence mới
                    self._finalize_sequence(error_key, new_errors)
                    self.error_sequences[error_key] = []
            
            # Thêm frame hiện tại vào sequence
            self.error_sequences[error_key].append(frame_number)
        
        # Kiểm tra các error keys không còn trong frame này (sequence đã kết thúc)
        ended_keys = set(self.error_sequences.keys()) - error_keys
        for error_key in ended_keys:
            if len(self.error_sequences[error_key]) >= min_sequence_length:
                # Sequence đủ dài, finalize nó
                self._finalize_sequence(error_key, new_errors)
            # Xóa sequence đã kết thúc
            del self.error_sequences[error_key]
        
        # Trả về các lỗi mới (chỉ khi sequence bắt đầu hoặc kết thúc)
        return new_errors
    
    def _get_error_key(self, error: Dict) -> str:
        """
        Tạo key duy nhất cho một loại lỗi
        
        Args:
            error: Error dictionary
            
        Returns:
            String key: "{type}_{body_part}_{side}"
        """
        error_type = error.get("type", "unknown")
        body_part = error.get("body_part", "")
        side = error.get("side", "")
        
        return f"{error_type}_{body_part}_{side}"
    
    def _finalize_sequence(self, error_key: str, new_errors: List[Dict]):
        """
        Finalize một sequence lỗi và tạo error entry cho nó
        
        Args:
            error_key: Key của sequence
            new_errors: List để thêm error mới vào
        """
        frames = self.error_sequences[error_key]
        if len(frames) < self.config.get("min_sequence_length", 3):
            return
        
        # Tạo error entry cho toàn bộ sequence
        # Sử dụng frame đầu tiên làm reference
        # Severity và deduction được tính dựa trên toàn bộ sequence
        sequence_error = {
            "type": error_key.split("_")[0],
            "body_part": error_key.split("_")[1] if len(error_key.split("_")) > 1 else "",
            "side": error_key.split("_")[2] if len(error_key.split("_")) > 2 else "",
            "frame_number": frames[0],  # Frame bắt đầu
            "frame_count": len(frames),  # Số frames trong sequence
            "frame_range": (frames[0], frames[-1]),  # Range của frames
            "is_sequence": True,  # Đánh dấu đây là lỗi sequence
            "description": f"Lỗi liên tục trong {len(frames)} frames",
        }
        
        # Tính severity và deduction dựa trên config
        aggregation_method = self.config.get("severity_aggregation", "mean")
        
        # Lấy deduction từ config (sẽ được tính lại trong controller)
        # Ở đây chỉ đánh dấu là sequence error
        sequence_error["deduction"] = self.config.get("sequence_deduction", 1.0)
        sequence_error["severity"] = len(frames) * 0.1  # Severity tăng theo số frames
        
        new_errors.append(sequence_error)
    
    def finalize_all_sequences(self) -> List[Dict]:
        """
        Finalize tất cả các sequence còn lại (khi video kết thúc)
        
        Returns:
            Danh sách các lỗi sequence cuối cùng
        """
        final_errors = []
        for error_key in list(self.error_sequences.keys()):
            if len(self.error_sequences[error_key]) >= self.config.get("min_sequence_length", 3):
                self._finalize_sequence(error_key, final_errors)
        
        self.error_sequences.clear()
        return final_errors
    
    def reset(self):
        """Reset service state"""
        self.error_sequences.clear()
        self.processed_errors.clear()

