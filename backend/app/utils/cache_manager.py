"""
Cache manager for storing and retrieving processed video data
"""
import pickle
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import numpy as np
from backend.app.config import CACHING_CONFIG


class CacheManager:
    """
    Manage caching of keypoints and templates for faster re-processing
    """
    
    def __init__(self, cache_dir: str = None, config: Dict = None):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory for cache storage
            config: Optional config (uses CACHING_CONFIG if not provided)
        """
        self.config = config or CACHING_CONFIG
        
        # Set up cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = self.config.get("cache_dir", Path("data/cache"))
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.keypoints_dir = self.cache_dir / "keypoints"
        self.templates_dir = self.cache_dir / "templates"
        self.metadata_dir = self.cache_dir / "metadata"
        
        for directory in [self.keypoints_dir, self.templates_dir, self.metadata_dir]:
            directory.mkdir(exist_ok=True)
    
    def get_cached_keypoints(
        self,
        video_path: str,
        config_hash: str = None
    ) -> Optional[Dict]:
        """
        Retrieve cached keypoints for a video
        
        Args:
            video_path: Path to video file
            config_hash: Optional hash of processing config
            
        Returns:
            Dict with cached data or None if not found/invalid
            {
                "keypoints": List[List[np.ndarray]],  # Per-frame, per-person keypoints
                "metadata": Dict
            }
        """
        if not self.config.get("enabled", True) or not self.config.get("cache_keypoints", True):
            return None
        
        # Calculate cache key
        cache_key = self._get_cache_key(video_path, config_hash)
        cache_path = self.keypoints_dir / f"{cache_key}.pkl"
        metadata_path = self.metadata_dir / f"{cache_key}.json"
        
        # Check if cache exists
        if not cache_path.exists() or not metadata_path.exists():
            return None
        
        # Load metadata and validate
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Check if cache is still valid
            if not self._is_cache_valid(video_path, metadata):
                # Clean up invalid cache
                cache_path.unlink(missing_ok=True)
                metadata_path.unlink(missing_ok=True)
                return None
            
            # Load cached keypoints
            with open(cache_path, 'rb') as f:
                keypoints = pickle.load(f)
            
            return {
                "keypoints": keypoints,
                "metadata": metadata
            }
        
        except Exception as e:
            print(f"⚠️  Error loading cache: {e}")
            return None
    
    def save_keypoints(
        self,
        video_path: str,
        keypoints: Any,
        config_hash: str = None,
        additional_metadata: Dict = None
    ):
        """
        Save keypoints to cache
        
        Args:
            video_path: Path to video file
            keypoints: Keypoints data to cache
            config_hash: Optional hash of processing config
            additional_metadata: Optional additional metadata to store
        """
        if not self.config.get("enabled", True) or not self.config.get("cache_keypoints", True):
            return
        
        try:
            # Calculate cache key
            cache_key = self._get_cache_key(video_path, config_hash)
            cache_path = self.keypoints_dir / f"{cache_key}.pkl"
            metadata_path = self.metadata_dir / f"{cache_key}.json"
            
            # Save keypoints
            with open(cache_path, 'wb') as f:
                pickle.dump(keypoints, f)
            
            # Save metadata
            metadata = {
                "video_path": str(video_path),
                "video_hash": self._calculate_file_hash(video_path),
                "config_hash": config_hash,
                "cache_time": datetime.now().isoformat(),
                "file_size": os.path.getsize(video_path),
                "cache_size": os.path.getsize(cache_path)
            }
            
            if additional_metadata:
                metadata.update(additional_metadata)
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Check cache size and clean if necessary
            self._check_cache_size()
        
        except Exception as e:
            print(f"⚠️  Error saving to cache: {e}")
    
    def get_cached_template(self, template_id: str) -> Optional[Dict]:
        """
        Retrieve cached golden template
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template data or None if not found
        """
        if not self.config.get("enabled", True) or not self.config.get("cache_templates", True):
            return None
        
        cache_path = self.templates_dir / f"{template_id}.pkl"
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"⚠️  Error loading template cache: {e}")
            return None
    
    def save_template(self, template_id: str, template_data: Dict):
        """
        Save golden template to cache
        
        Args:
            template_id: Template identifier
            template_data: Template data to cache
        """
        if not self.config.get("enabled", True) or not self.config.get("cache_templates", True):
            return
        
        try:
            cache_path = self.templates_dir / f"{template_id}.pkl"
            
            with open(cache_path, 'wb') as f:
                pickle.dump(template_data, f)
        
        except Exception as e:
            print(f"⚠️  Error saving template to cache: {e}")
    
    def clear_cache(self, cache_type: str = "all"):
        """
        Clear cache
        
        Args:
            cache_type: Type to clear ("all", "keypoints", "templates", "metadata")
        """
        try:
            if cache_type in ["all", "keypoints"]:
                shutil.rmtree(self.keypoints_dir, ignore_errors=True)
                self.keypoints_dir.mkdir(exist_ok=True)
                print("✅ Cleared keypoints cache")
            
            if cache_type in ["all", "templates"]:
                shutil.rmtree(self.templates_dir, ignore_errors=True)
                self.templates_dir.mkdir(exist_ok=True)
                print("✅ Cleared templates cache")
            
            if cache_type in ["all", "metadata"]:
                shutil.rmtree(self.metadata_dir, ignore_errors=True)
                self.metadata_dir.mkdir(exist_ok=True)
                print("✅ Cleared metadata cache")
        
        except Exception as e:
            print(f"⚠️  Error clearing cache: {e}")
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dict with cache statistics
        """
        def get_dir_size(directory: Path) -> int:
            """Calculate total size of directory"""
            total = 0
            for item in directory.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
            return total
        
        def count_files(directory: Path) -> int:
            """Count files in directory"""
            return len([f for f in directory.rglob("*") if f.is_file()])
        
        keypoints_size = get_dir_size(self.keypoints_dir)
        templates_size = get_dir_size(self.templates_dir)
        metadata_size = get_dir_size(self.metadata_dir)
        total_size = keypoints_size + templates_size + metadata_size
        
        return {
            "total_size_mb": total_size / (1024 * 1024),
            "keypoints_count": count_files(self.keypoints_dir),
            "keypoints_size_mb": keypoints_size / (1024 * 1024),
            "templates_count": count_files(self.templates_dir),
            "templates_size_mb": templates_size / (1024 * 1024),
            "metadata_count": count_files(self.metadata_dir),
            "metadata_size_mb": metadata_size / (1024 * 1024),
        }
    
    def print_cache_stats(self):
        """Print formatted cache statistics"""
        stats = self.get_cache_stats()
        
        print("\n" + "="*50)
        print("CACHE STATISTICS")
        print("="*50)
        print(f"Total Size: {stats['total_size_mb']:.2f} MB")
        print(f"\nKeypoints:")
        print(f"  Count: {stats['keypoints_count']}")
        print(f"  Size: {stats['keypoints_size_mb']:.2f} MB")
        print(f"\nTemplates:")
        print(f"  Count: {stats['templates_count']}")
        print(f"  Size: {stats['templates_size_mb']:.2f} MB")
        print(f"\nMetadata:")
        print(f"  Count: {stats['metadata_count']}")
        print(f"  Size: {stats['metadata_size_mb']:.2f} MB")
        print("="*50)
    
    def _get_cache_key(self, video_path: str, config_hash: str = None) -> str:
        """
        Generate cache key from video path and config
        
        Args:
            video_path: Path to video file
            config_hash: Optional config hash
            
        Returns:
            Cache key string
        """
        # Use video path + config hash
        key_parts = [str(video_path)]
        
        if config_hash:
            key_parts.append(config_hash)
        
        key_string = "|".join(key_parts)
        
        # Hash to create short key
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate hash of file for invalidation detection
        
        Args:
            file_path: Path to file
            
        Returns:
            MD5 hash of file
        """
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, "rb") as f:
                # Read in chunks for large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            return hash_md5.hexdigest()
        
        except Exception:
            return ""
    
    def _is_cache_valid(self, video_path: str, metadata: Dict) -> bool:
        """
        Check if cache is still valid
        
        Args:
            video_path: Path to video file
            metadata: Cached metadata
            
        Returns:
            True if cache is valid
        """
        # Check if video file still exists
        if not os.path.exists(video_path):
            return False
        
        # Check if video was modified
        current_hash = self._calculate_file_hash(video_path)
        if current_hash != metadata.get("video_hash", ""):
            return False
        
        # Check expiry date
        expiry_days = self.config.get("cache_expiry_days", 7)
        cache_time = datetime.fromisoformat(metadata.get("cache_time", "2000-01-01"))
        expiry_time = cache_time + timedelta(days=expiry_days)
        
        if datetime.now() > expiry_time:
            return False
        
        return True
    
    def _check_cache_size(self):
        """Check cache size and clean old entries if exceeding limit"""
        max_size_mb = self.config.get("max_cache_size_mb", 500)
        stats = self.get_cache_stats()
        
        if stats["total_size_mb"] > max_size_mb:
            print(f"⚠️  Cache size ({stats['total_size_mb']:.1f} MB) exceeds limit ({max_size_mb} MB)")
            print("   Automatically cleaning oldest entries...")
            self._cleanup_old_entries(target_size_mb=max_size_mb * 0.8)  # Clean to 80% of limit
    
    def _cleanup_old_entries(self, target_size_mb: float):
        """
        Clean up oldest cache entries until target size is reached
        
        Args:
            target_size_mb: Target cache size in MB
        """
        import os
        from datetime import datetime
        
        # Get all cache files with timestamps
        cache_files = []
        for directory in [self.keypoints_dir, self.templates_dir, self.metadata_dir]:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    size = file_path.stat().st_size
                    cache_files.append((file_path, mtime, size))
        
        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda x: x[1])
        
        # Delete oldest files until we reach target size
        current_size_mb = sum(f[2] for f in cache_files) / (1024 * 1024)
        deleted_count = 0
        
        for file_path, mtime, size in cache_files:
            if current_size_mb <= target_size_mb:
                break
            
            try:
                file_path.unlink()
                current_size_mb -= size / (1024 * 1024)
                deleted_count += 1
            except Exception as e:
                print(f"   Failed to delete {file_path}: {e}")
        
        if deleted_count > 0:
            print(f"   ✅ Deleted {deleted_count} old cache files")
            print(f"   Cache size reduced to {current_size_mb:.1f} MB")
