"""
Beat Detection Service - Phát hiện beat và timing trong nhạc
Sử dụng Librosa để phân tích âm thanh
"""
import numpy as np
from typing import List, Tuple, Optional
import librosa


class BeatDetector:
    """
    Detector cho beat và timing trong audio
    """
    
    def __init__(self, audio_path: str, hop_length: int = 512):
        """
        Args:
            audio_path: Đường dẫn file audio
            hop_length: Hop length cho librosa (mặc định 512)
        """
        self.audio_path = audio_path
        self.hop_length = hop_length
        
        # Load audio
        self.y, self.sr = librosa.load(audio_path)
        
        # Detect beats
        self.tempo, self.beat_frames = librosa.beat.beat_track(
            y=self.y, 
            sr=self.sr,
            hop_length=hop_length
        )
        
        # Convert beat frames to timestamps
        self.beat_times = librosa.frames_to_time(
            self.beat_frames,
            sr=self.sr,
            hop_length=hop_length
        )
    
    def get_beat_at_time(self, timestamp: float, tolerance: float = 0.1) -> Optional[float]:
        """
        Tìm beat gần nhất với timestamp
        
        Args:
            timestamp: Thời điểm cần kiểm tra (giây)
            tolerance: Khoảng dung sai (giây)
            
        Returns:
            Beat time gần nhất, hoặc None nếu không có beat trong khoảng tolerance
        """
        # Tìm beat gần nhất
        idx = np.searchsorted(self.beat_times, timestamp)
        
        candidates = []
        if idx > 0:
            candidates.append(self.beat_times[idx - 1])
        if idx < len(self.beat_times):
            candidates.append(self.beat_times[idx])
        
        if not candidates:
            return None
        
        # Chọn beat gần nhất
        closest = min(candidates, key=lambda t: abs(t - timestamp))
        
        # Kiểm tra tolerance
        if abs(closest - timestamp) <= tolerance:
            return closest
        return None
    
    def calculate_rhythm_error(
        self,
        motion_timestamps: List[float],
        tolerance: float = 0.15
    ) -> Tuple[int, List[Tuple[float, float]]]:
        """
        Tính lỗi rhythm - số động tác không khớp beat
        
        Args:
            motion_timestamps: List timestamps của các động tác
            tolerance: Khoảng dung sai (giây)
            
        Returns:
            Tuple (số lỗi, list các cặp (motion_time, beat_time) lỗi)
        """
        errors = []
        error_count = 0
        
        for motion_time in motion_timestamps:
            beat_time = self.get_beat_at_time(motion_time, tolerance)
            
            if beat_time is None:
                # Không có beat trong khoảng tolerance → lỗi
                error_count += 1
                # Tìm beat gần nhất để report
                idx = np.searchsorted(self.beat_times, motion_time)
                if idx < len(self.beat_times):
                    closest = self.beat_times[idx]
                elif idx > 0:
                    closest = self.beat_times[idx - 1]
                else:
                    closest = motion_time
                errors.append((motion_time, closest))
        
        return error_count, errors
    
    def get_expected_beats_in_range(
        self,
        start_time: float,
        end_time: float
    ) -> List[float]:
        """
        Lấy danh sách beats trong khoảng thời gian
        
        Args:
            start_time: Thời điểm bắt đầu (giây)
            end_time: Thời điểm kết thúc (giây)
            
        Returns:
            List timestamps của beats
        """
        mask = (self.beat_times >= start_time) & (self.beat_times <= end_time)
        return self.beat_times[mask].tolist()
