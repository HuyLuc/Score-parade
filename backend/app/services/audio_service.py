"""
Audio service - Xử lý phát nhạc
"""
from pathlib import Path
from typing import Optional
import backend.app.config as config


class AudioService:
    """Service cho audio"""
    
    def __init__(self):
        self.audio_dir = config.DATA_DIR / "audio"
    
    def get_command_audio(self, command: str) -> Optional[Path]:
        """
        Lấy đường dẫn audio cho lệnh
        
        Args:
            command: Tên lệnh (vd: "nghiem_di_deu_buoc")
            
        Returns:
            Đường dẫn file audio hoặc None
        """
        audio_path = self.audio_dir / "command" / f"{command}.mp3"
        if audio_path.exists():
            return audio_path
        return None
    
    def get_mode_audio(
        self, 
        criteria: str,  # di_deu hoặc di_nghiem
        mode: str,  # local hoặc global
        practice_type: str  # testing hoặc practising
    ) -> Optional[Path]:
        """
        Lấy đường dẫn audio cho chế độ
        
        Args:
            criteria: Tiêu chí (di_deu/di_nghiem)
            mode: Chế độ (local/global)
            practice_type: Loại (testing/practising)
            
        Returns:
            Đường dẫn file audio hoặc None
        """
        if mode == "local":
            suffix = "short" if practice_type == "testing" else "long"
            audio_path = self.audio_dir / criteria / "local" / f"practising_{suffix}.mp3"
        else:  # global
            audio_path = self.audio_dir / criteria / "global" / "total.mp3"
        
        if audio_path.exists():
            return audio_path
        return None

