"""
Tests for multi-person system infrastructure components
"""
import pytest
import numpy as np
import tempfile
import cv2
from pathlib import Path
import pickle

from backend.app.services.person_reidentification import PersonReIdentifier
from backend.app.utils.video_validator import VideoValidator
from backend.app.utils.progress_tracker import ProgressTracker, SimpleProgressBar
from backend.app.utils.cache_manager import CacheManager
from backend.app.services.pose_service import PoseService


class TestPersonReIdentifier:
    """Test PersonReIdentifier class"""
    
    def test_init(self):
        """Test re-identifier initialization"""
        reid = PersonReIdentifier(similarity_threshold=0.7, max_disappeared_frames=60)
        assert reid.similarity_threshold == 0.7
        assert reid.max_disappeared_frames == 60
        assert len(reid.disappeared_persons) == 0
    
    def test_register_disappeared(self):
        """Test registering a disappeared person"""
        reid = PersonReIdentifier()
        keypoints = np.random.rand(17, 3)
        keypoints[:, 2] = 1.0  # Set confidence
        
        reid.register_disappeared(person_id=0, keypoints=keypoints)
        
        assert 0 in reid.disappeared_persons
        assert reid.disappeared_persons[0]["frames_gone"] == 0
        assert "position" in reid.disappeared_persons[0]
        assert "keypoints" in reid.disappeared_persons[0]
    
    def test_update_disappeared(self):
        """Test updating disappeared counter"""
        reid = PersonReIdentifier(max_disappeared_frames=5)
        keypoints = np.random.rand(17, 3)
        keypoints[:, 2] = 1.0
        
        reid.register_disappeared(0, keypoints)
        
        # Update 5 times - should not expire yet
        for _ in range(5):
            reid.update_disappeared()
        
        assert 0 in reid.disappeared_persons
        
        # One more update should expire
        reid.update_disappeared()
        assert 0 not in reid.disappeared_persons
    
    def test_attempt_reidentification_no_match(self):
        """Test re-identification with no matches"""
        reid = PersonReIdentifier(similarity_threshold=0.9)
        
        # Register disappeared person
        keypoints1 = np.zeros((17, 3))
        keypoints1[:5, :2] = [[100, 100], [120, 110], [110, 105], [130, 115], [125, 120]]
        keypoints1[:, 2] = 1.0
        reid.register_disappeared(0, keypoints1)
        
        # New detection at very different location and pose
        keypoints2 = np.zeros((17, 3))
        keypoints2[:5, :2] = [[500, 500], [520, 510], [510, 505], [530, 515], [525, 520]]
        keypoints2[:, 2] = 1.0
        
        reidentified = reid.attempt_reidentification([keypoints2])
        
        # Should not match due to low similarity
        assert len(reidentified) == 0
    
    def test_attempt_reidentification_success(self):
        """Test successful re-identification"""
        reid = PersonReIdentifier(similarity_threshold=0.6)
        
        # Register disappeared person
        keypoints1 = np.zeros((17, 3))
        for i in range(17):
            keypoints1[i, :2] = [100 + i * 10, 100 + i * 5]
        keypoints1[:, 2] = 1.0
        reid.register_disappeared(0, keypoints1)
        
        # New detection at similar location and pose
        keypoints2 = np.zeros((17, 3))
        for i in range(17):
            keypoints2[i, :2] = [105 + i * 10, 105 + i * 5]  # Slightly moved
        keypoints2[:, 2] = 1.0
        
        reidentified = reid.attempt_reidentification([keypoints2])
        
        # Should match
        assert len(reidentified) > 0
        assert 0 in reidentified
    
    def test_reset(self):
        """Test resetting re-identifier"""
        reid = PersonReIdentifier()
        keypoints = np.random.rand(17, 3)
        keypoints[:, 2] = 1.0
        
        reid.register_disappeared(0, keypoints)
        reid.register_disappeared(1, keypoints)
        
        assert len(reid.disappeared_persons) == 2
        
        reid.reset()
        assert len(reid.disappeared_persons) == 0


class TestVideoValidator:
    """Test VideoValidator class"""
    
    def create_test_video(self, width=1280, height=720, fps=30, duration=2):
        """Create a temporary test video"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
        
        num_frames = int(fps * duration)
        for i in range(num_frames):
            # Create a simple frame
            frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            writer.write(frame)
        
        writer.release()
        return temp_path
    
    def test_validate_video_success(self):
        """Test validation of good quality video"""
        video_path = self.create_test_video(width=1280, height=720, fps=30)
        
        try:
            validator = VideoValidator()
            result = validator.validate_video(video_path)
            
            assert "valid" in result
            assert "specs" in result
            assert result["specs"]["resolution"] == (1280, 720)
            assert result["specs"]["fps"] == 30
        finally:
            Path(video_path).unlink(missing_ok=True)
    
    def test_validate_video_low_resolution(self):
        """Test validation of low resolution video"""
        video_path = self.create_test_video(width=320, height=240, fps=30)
        
        try:
            validator = VideoValidator()
            result = validator.validate_video(video_path)
            
            assert result["valid"] == False
            assert len(result["errors"]) > 0
            assert any("Resolution" in error for error in result["errors"])
        finally:
            Path(video_path).unlink(missing_ok=True)
    
    def test_validate_nonexistent_video(self):
        """Test validation of nonexistent video"""
        validator = VideoValidator()
        result = validator.validate_video("/nonexistent/video.mp4")
        
        assert result["valid"] == False
        assert len(result["errors"]) > 0
    
    def test_quick_validate(self):
        """Test quick validation"""
        video_path = self.create_test_video(width=1280, height=720, fps=30)
        
        try:
            validator = VideoValidator()
            assert validator.quick_validate(video_path) == True
        finally:
            Path(video_path).unlink(missing_ok=True)


class TestProgressTracker:
    """Test ProgressTracker class"""
    
    def test_init(self):
        """Test progress tracker initialization"""
        tracker = ProgressTracker(total=100, description="Test")
        
        assert tracker.total == 100
        assert tracker.current == 0
        assert tracker.description == "Test"
    
    def test_update(self):
        """Test updating progress"""
        tracker = ProgressTracker(total=100)
        
        tracker.update(10)
        assert tracker.current == 10
        
        tracker.update(20)
        assert tracker.current == 30
    
    def test_get_percentage(self):
        """Test percentage calculation"""
        tracker = ProgressTracker(total=100)
        
        tracker.update(25)
        assert tracker.get_percentage() == 25.0
        
        tracker.update(25)
        assert tracker.get_percentage() == 50.0
    
    def test_get_fps(self):
        """Test FPS calculation"""
        tracker = ProgressTracker(total=100)
        
        # Simulate some processing
        tracker.update(10)
        fps = tracker.get_fps()
        
        # Should have some FPS value
        assert fps >= 0
    
    def test_reset(self):
        """Test resetting tracker"""
        tracker = ProgressTracker(total=100)
        
        tracker.update(50)
        assert tracker.current == 50
        
        tracker.reset()
        assert tracker.current == 0


class TestSimpleProgressBar:
    """Test SimpleProgressBar context manager"""
    
    def test_context_manager(self):
        """Test progress bar as context manager"""
        with SimpleProgressBar(total=10, description="Test") as pbar:
            for i in range(10):
                pbar.update(1)
            
            assert pbar.tracker.current == 10


class TestCacheManager:
    """Test CacheManager class"""
    
    def test_init(self):
        """Test cache manager initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            assert cache_manager.cache_dir.exists()
            assert cache_manager.keypoints_dir.exists()
            assert cache_manager.templates_dir.exists()
            assert cache_manager.metadata_dir.exists()
    
    def test_save_and_get_keypoints(self):
        """Test saving and retrieving keypoints"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Create test video file
            video_path = Path(temp_dir) / "test_video.mp4"
            video_path.write_text("test")
            
            # Create test keypoints
            keypoints = [np.random.rand(17, 3) for _ in range(10)]
            
            # Save to cache
            cache_manager.save_keypoints(str(video_path), keypoints, config_hash="test_hash")
            
            # Retrieve from cache
            cached = cache_manager.get_cached_keypoints(str(video_path), config_hash="test_hash")
            
            assert cached is not None
            assert "keypoints" in cached
            assert "metadata" in cached
            assert len(cached["keypoints"]) == 10
    
    def test_cache_invalidation_on_video_change(self):
        """Test cache invalidation when video changes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Create test video file
            video_path = Path(temp_dir) / "test_video.mp4"
            video_path.write_text("test content 1")
            
            # Create and save keypoints
            keypoints = [np.random.rand(17, 3) for _ in range(5)]
            cache_manager.save_keypoints(str(video_path), keypoints)
            
            # Verify cache exists
            cached = cache_manager.get_cached_keypoints(str(video_path))
            assert cached is not None
            
            # Modify video file
            video_path.write_text("test content 2 - modified")
            
            # Cache should be invalidated
            cached = cache_manager.get_cached_keypoints(str(video_path))
            assert cached is None
    
    def test_save_and_get_template(self):
        """Test saving and retrieving templates"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Create test template
            template_data = {
                "keypoints": np.random.rand(100, 17, 3),
                "profile": {"name": "person_0"}
            }
            
            # Save template
            cache_manager.save_template("person_0", template_data)
            
            # Retrieve template
            cached_template = cache_manager.get_cached_template("person_0")
            
            assert cached_template is not None
            assert "keypoints" in cached_template
            assert "profile" in cached_template
    
    def test_clear_cache(self):
        """Test clearing cache"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            # Save some data
            video_path = Path(temp_dir) / "test.mp4"
            video_path.write_text("test")
            
            cache_manager.save_keypoints(str(video_path), [np.random.rand(17, 3)])
            cache_manager.save_template("test_template", {"data": "test"})
            
            # Verify files exist
            assert len(list(cache_manager.keypoints_dir.glob("*"))) > 0
            assert len(list(cache_manager.templates_dir.glob("*"))) > 0
            
            # Clear cache
            cache_manager.clear_cache("all")
            
            # Verify cache is empty
            assert len(list(cache_manager.keypoints_dir.glob("*"))) == 0
            assert len(list(cache_manager.templates_dir.glob("*"))) == 0
    
    def test_get_cache_stats(self):
        """Test getting cache statistics"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_manager = CacheManager(cache_dir=temp_dir)
            
            stats = cache_manager.get_cache_stats()
            
            assert "total_size_mb" in stats
            assert "keypoints_count" in stats
            assert "templates_count" in stats
            assert stats["total_size_mb"] >= 0


class TestBatchProcessing:
    """Test batch processing functionality"""
    
    def test_predict_batch_multi_person(self):
        """Test batch processing returns correct structure"""
        pose_service = PoseService()
        
        # Create test frames
        frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(4)]
        
        # Process batch
        results = pose_service.predict_batch_multi_person(frames, batch_size=2)
        
        # Check structure
        assert len(results) == 4  # One result per frame
        assert isinstance(results, list)
        
        for frame_result in results:
            assert isinstance(frame_result, list)  # List of person detections
            
            for detection in frame_result:
                assert "keypoints" in detection
                assert "confidence" in detection
                assert "bbox" in detection
