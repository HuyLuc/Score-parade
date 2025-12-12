"""
Progress tracking utility for real-time feedback during video processing
"""
import time
import sys
from typing import Optional
from backend.app.config import PROGRESS_TRACKING_CONFIG


class ProgressTracker:
    """
    Track progress of video processing with ETA and FPS calculation
    """
    
    def __init__(
        self,
        total: int,
        description: str = "Processing",
        config: dict = None
    ):
        """
        Initialize progress tracker
        
        Args:
            total: Total number of items to process
            description: Description of the task
            config: Optional config (uses PROGRESS_TRACKING_CONFIG if not provided)
        """
        self.total = total
        self.description = description
        self.config = config or PROGRESS_TRACKING_CONFIG
        
        # Tracking state
        self.current = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.update_interval = self.config.get("update_interval", 1.0)
        
        # Performance metrics
        self.fps_history = []
        self.max_history_size = 10
    
    def update(self, n: int = 1):
        """
        Update progress by n items
        
        Args:
            n: Number of items processed since last update
        """
        self.current += n
        
        # Calculate FPS for this update
        current_time = time.time()
        time_delta = current_time - self.last_update_time
        
        if time_delta > 0:
            fps = n / time_delta
            self.fps_history.append(fps)
            
            # Keep only recent history
            if len(self.fps_history) > self.max_history_size:
                self.fps_history.pop(0)
        
        self.last_update_time = current_time
        
        # Print progress if enough time has passed
        if self.config.get("enable_progress_bar", True):
            if current_time - self.last_print_time >= self.update_interval or self.current >= self.total:
                self.print_progress_bar()
                self.last_print_time = current_time
    
    def print_progress_bar(self):
        """Print formatted progress bar to console"""
        if not hasattr(self, 'last_print_time'):
            self.last_print_time = self.start_time
        
        # Calculate progress percentage
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        
        # Build progress bar
        bar_length = self.config.get("bar_length", 50)
        filled_length = int(bar_length * self.current / self.total) if self.total > 0 else 0
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Build status string
        status_parts = [f"{percentage:5.1f}%", f"[{bar}]", f"{self.current}/{self.total}"]
        
        # Add FPS if enabled
        if self.config.get("show_fps", True):
            fps = self.get_fps()
            if fps > 0:
                status_parts.append(f"{fps:.1f} FPS")
        
        # Add ETA if enabled
        if self.config.get("show_eta", True):
            eta = self.get_eta()
            if eta > 0:
                eta_str = self._format_time(eta)
                status_parts.append(f"ETA: {eta_str}")
        
        # Print with carriage return to overwrite previous line
        status = f"\r{self.description}: {' | '.join(status_parts)}"
        sys.stdout.write(status)
        sys.stdout.flush()
        
        # Print newline when complete
        if self.current >= self.total:
            elapsed = time.time() - self.start_time
            elapsed_str = self._format_time(elapsed)
            print(f"\n✅ Complete! Total time: {elapsed_str}")
    
    def get_fps(self) -> float:
        """
        Get current processing speed in frames per second
        
        Returns:
            Average FPS from recent history
        """
        if not self.fps_history:
            return 0.0
        
        # Use average of recent FPS values for stability
        return sum(self.fps_history) / len(self.fps_history)
    
    def get_eta(self) -> float:
        """
        Get estimated time remaining in seconds
        
        Returns:
            Estimated seconds until completion
        """
        if self.current == 0:
            return 0.0
        
        elapsed = time.time() - self.start_time
        avg_time_per_item = elapsed / self.current
        remaining_items = self.total - self.current
        
        return avg_time_per_item * remaining_items
    
    def get_elapsed(self) -> float:
        """
        Get elapsed time in seconds
        
        Returns:
            Seconds since start
        """
        return time.time() - self.start_time
    
    def get_percentage(self) -> float:
        """
        Get completion percentage
        
        Returns:
            Percentage complete (0-100)
        """
        return (self.current / self.total) * 100 if self.total > 0 else 0
    
    def _format_time(self, seconds: float) -> str:
        """
        Format time in human-readable format
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted string (e.g., "1m 23s" or "45s")
        """
        if seconds < 0:
            return "N/A"
        
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        
        if minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def reset(self):
        """Reset tracker to initial state"""
        self.current = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.fps_history = []
        if hasattr(self, 'last_print_time'):
            del self.last_print_time
    
    def close(self):
        """Close progress tracker and print final stats"""
        if self.current < self.total:
            print(f"\n⚠️  Processing interrupted at {self.current}/{self.total} items")
        
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)
        avg_fps = self.current / elapsed if elapsed > 0 else 0
        
        print(f"📊 Processing stats: {elapsed_str} elapsed, {avg_fps:.1f} FPS average")


class SimpleProgressBar:
    """
    Simplified progress bar for quick use (context manager compatible)
    """
    
    def __init__(self, total: int, description: str = "Processing"):
        """
        Initialize simple progress bar
        
        Args:
            total: Total number of items
            description: Task description
        """
        self.tracker = ProgressTracker(total, description)
    
    def __enter__(self):
        """Enter context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager"""
        self.tracker.close()
    
    def update(self, n: int = 1):
        """Update progress"""
        self.tracker.update(n)
    
    def set_progress(self, current: int):
        """Set absolute progress"""
        if current > self.tracker.current:
            self.tracker.update(current - self.tracker.current)
