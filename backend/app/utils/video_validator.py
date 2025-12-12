"""
Video validation utility for checking video quality and specifications
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from backend.app.config import VIDEO_VALIDATION_CONFIG


class VideoValidator:
    """
    Validate video files for quality and specifications before processing
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize video validator
        
        Args:
            config: Optional validation configuration (uses VIDEO_VALIDATION_CONFIG if not provided)
        """
        self.config = config or VIDEO_VALIDATION_CONFIG
    
    def validate_video(self, video_path: str) -> Dict:
        """
        Comprehensive video validation
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "recommendations": List[str],
                "specs": {
                    "resolution": (width, height),
                    "fps": float,
                    "duration": float,
                    "frame_count": int
                },
                "quality": {
                    "lighting": float,  # 0-255
                    "blur": float,      # Variance
                    "noise": float      # 0-1
                }
            }
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "recommendations": [],
            "specs": {},
            "quality": {}
        }
        
        # Check if file exists
        if not Path(video_path).exists():
            result["valid"] = False
            result["errors"].append(f"Video file not found: {video_path}")
            return result
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            result["valid"] = False
            result["errors"].append("Failed to open video file. File may be corrupted.")
            return result
        
        try:
            # Get video specifications
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            result["specs"] = {
                "resolution": (width, height),
                "fps": fps,
                "duration": duration,
                "frame_count": frame_count
            }
            
            # Validate resolution
            min_width, min_height = self.config["min_resolution"]
            if width < min_width or height < min_height:
                result["valid"] = False
                result["errors"].append(
                    f"Resolution too low: {width}x{height} (minimum: {min_width}x{min_height})"
                )
                result["recommendations"].append(
                    f"Re-record video at minimum {min_width}x{min_height} resolution (720p or higher recommended)"
                )
            
            # Validate FPS
            min_fps = self.config["min_fps"]
            if fps < min_fps:
                result["warnings"].append(
                    f"Low frame rate: {fps:.1f} FPS (minimum: {min_fps} FPS)"
                )
                result["recommendations"].append(
                    f"Use camera with at least {min_fps} FPS for better tracking accuracy"
                )
            
            # Validate duration
            max_duration = self.config.get("max_duration", 600)
            if duration > max_duration:
                result["warnings"].append(
                    f"Video duration exceeds recommended maximum: {duration:.1f}s (max: {max_duration}s)"
                )
                result["recommendations"].append(
                    "Consider splitting long videos into shorter segments for faster processing"
                )
            
            # Sample frames for quality analysis
            if self.config.get("check_lighting") or self.config.get("check_blur") or self.config.get("check_noise"):
                quality_metrics = self._analyze_video_quality(cap, frame_count)
                result["quality"] = quality_metrics
                
                # Check lighting
                if self.config.get("check_lighting"):
                    lighting_threshold = self.config.get("lighting_threshold", 50)
                    if quality_metrics["lighting"] < lighting_threshold:
                        result["warnings"].append(
                            f"Poor lighting detected: {quality_metrics['lighting']:.1f} (minimum: {lighting_threshold})"
                        )
                        result["recommendations"].append(
                            "Improve lighting conditions for better pose detection accuracy"
                        )
                
                # Check blur
                if self.config.get("check_blur"):
                    blur_threshold = self.config.get("blur_threshold", 100)
                    if quality_metrics["blur"] < blur_threshold:
                        result["warnings"].append(
                            f"Motion blur detected: {quality_metrics['blur']:.1f} (minimum: {blur_threshold})"
                        )
                        result["recommendations"].append(
                            "Use higher shutter speed or reduce motion speed to minimize blur"
                        )
                
                # Check noise
                if self.config.get("check_noise"):
                    if quality_metrics["noise"] > 0.15:
                        result["warnings"].append(
                            f"High noise level detected: {quality_metrics['noise']:.3f}"
                        )
                        result["recommendations"].append(
                            "Improve lighting or reduce camera ISO to minimize noise"
                        )
        
        finally:
            cap.release()
        
        return result
    
    def _analyze_video_quality(self, cap: cv2.VideoCapture, frame_count: int) -> Dict:
        """
        Analyze video quality by sampling frames
        
        Args:
            cap: OpenCV VideoCapture object
            frame_count: Total number of frames
            
        Returns:
            Dict with quality metrics
        """
        # Sample 10 frames evenly distributed
        sample_count = min(10, frame_count)
        sample_indices = np.linspace(0, frame_count - 1, sample_count, dtype=int)
        
        lighting_values = []
        blur_values = []
        noise_values = []
        
        for idx in sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Lighting: average brightness
            lighting = np.mean(gray)
            lighting_values.append(lighting)
            
            # Blur: Laplacian variance (higher = sharper)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            blur_values.append(laplacian_var)
            
            # Noise: estimate from high-frequency components
            noise = self._estimate_noise(gray)
            noise_values.append(noise)
        
        # Average the metrics
        return {
            "lighting": np.mean(lighting_values) if lighting_values else 0,
            "blur": np.mean(blur_values) if blur_values else 0,
            "noise": np.mean(noise_values) if noise_values else 0
        }
    
    def _estimate_noise(self, gray: np.ndarray) -> float:
        """
        Estimate noise level using high-pass filter
        
        Args:
            gray: Grayscale image
            
        Returns:
            Noise estimate (0-1 scale)
        """
        # Use Sobel operator to get high-frequency components
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        
        # Calculate magnitude
        magnitude = np.sqrt(sobelx**2 + sobely**2)
        
        # Normalize to 0-1 range
        noise_estimate = np.std(magnitude) / 255.0
        
        return noise_estimate
    
    def quick_validate(self, video_path: str) -> bool:
        """
        Quick validation check (only essential specs, no quality analysis)
        
        Args:
            video_path: Path to video file
            
        Returns:
            True if video passes basic validation
        """
        if not Path(video_path).exists():
            return False
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False
        
        try:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            min_width, min_height = self.config["min_resolution"]
            min_fps = self.config["min_fps"]
            
            return width >= min_width and height >= min_height and fps >= min_fps
        
        finally:
            cap.release()
    
    def print_validation_report(self, validation_result: Dict):
        """
        Print formatted validation report
        
        Args:
            validation_result: Result from validate_video()
        """
        print("\n" + "="*60)
        print("VIDEO VALIDATION REPORT")
        print("="*60)
        
        # Status
        status = "✅ PASS" if validation_result["valid"] else "❌ FAIL"
        print(f"\nStatus: {status}")
        
        # Specifications
        if "specs" in validation_result:
            specs = validation_result["specs"]
            print("\n📹 Specifications:")
            print(f"  Resolution: {specs['resolution'][0]}x{specs['resolution'][1]}")
            print(f"  FPS: {specs['fps']:.1f}")
            print(f"  Duration: {specs['duration']:.1f}s ({specs['frame_count']} frames)")
        
        # Quality metrics
        if "quality" in validation_result and validation_result["quality"]:
            quality = validation_result["quality"]
            print("\n🎨 Quality Metrics:")
            print(f"  Lighting: {quality['lighting']:.1f} / 255")
            print(f"  Sharpness: {quality['blur']:.1f}")
            print(f"  Noise: {quality['noise']:.3f}")
        
        # Errors
        if validation_result["errors"]:
            print("\n❌ Errors:")
            for error in validation_result["errors"]:
                print(f"  • {error}")
        
        # Warnings
        if validation_result["warnings"]:
            print("\n⚠️  Warnings:")
            for warning in validation_result["warnings"]:
                print(f"  • {warning}")
        
        # Recommendations
        if validation_result["recommendations"]:
            print("\n💡 Recommendations:")
            for rec in validation_result["recommendations"]:
                print(f"  • {rec}")
        
        print("\n" + "="*60)
