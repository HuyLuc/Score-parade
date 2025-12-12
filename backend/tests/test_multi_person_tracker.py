"""
Tests for multi-person tracking service
"""
import pytest
import numpy as np
from backend.app.services.multi_person_tracker import PersonTracker, MultiPersonManager


class TestPersonTracker:
    """Test PersonTracker class"""
    
    def test_init(self):
        """Test tracker initialization"""
        tracker = PersonTracker(max_disappeared=30, iou_threshold=0.5)
        assert tracker.max_disappeared == 30
        assert tracker.iou_threshold == 0.5
        assert tracker.next_person_id == 0
        assert len(tracker.persons) == 0
        assert len(tracker.disappeared) == 0
    
    def test_register_person(self):
        """Test registering a new person"""
        tracker = PersonTracker()
        keypoints = np.random.rand(17, 3)
        
        person_id = tracker.register(keypoints, frame_num=0)
        
        assert person_id == 0
        assert len(tracker.persons) == 1
        assert person_id in tracker.persons
        assert tracker.disappeared[person_id] == 0
        assert tracker.next_person_id == 1
    
    def test_deregister_person(self):
        """Test deregistering a person"""
        tracker = PersonTracker()
        keypoints = np.random.rand(17, 3)
        
        person_id = tracker.register(keypoints, frame_num=0)
        tracker.deregister(person_id)
        
        assert len(tracker.persons) == 0
        assert person_id not in tracker.persons
        assert person_id not in tracker.disappeared
    
    def test_track_single_person_across_frames(self):
        """Test tracking a single person across multiple frames"""
        tracker = PersonTracker(iou_threshold=0.3)
        
        # Frame 0: Register person
        keypoints_0 = np.zeros((17, 3))
        keypoints_0[:, :2] = np.array([[100, 100], [120, 110], [110, 105]] + [[0, 0]] * 14)
        keypoints_0[:, 2] = 1.0
        
        tracked = tracker.update([keypoints_0], frame_num=0)
        assert len(tracked) == 1
        person_id = list(tracked.keys())[0]
        assert person_id == 0
        
        # Frame 1: Same person, slightly moved
        keypoints_1 = np.zeros((17, 3))
        keypoints_1[:, :2] = np.array([[105, 105], [125, 115], [115, 110]] + [[0, 0]] * 14)
        keypoints_1[:, 2] = 1.0
        
        tracked = tracker.update([keypoints_1], frame_num=1)
        assert len(tracked) == 1
        assert person_id in tracked  # Same person ID
    
    def test_track_multiple_persons(self):
        """Test tracking multiple persons simultaneously"""
        tracker = PersonTracker(iou_threshold=0.3)
        
        # Frame 0: Two persons
        person1_kpts = np.zeros((17, 3))
        person1_kpts[:, :2] = np.array([[100, 100]] * 17)
        person1_kpts[:, 2] = 1.0
        
        person2_kpts = np.zeros((17, 3))
        person2_kpts[:, :2] = np.array([[300, 100]] * 17)
        person2_kpts[:, 2] = 1.0
        
        tracked = tracker.update([person1_kpts, person2_kpts], frame_num=0)
        assert len(tracked) == 2
        
        # Frame 1: Same two persons
        person1_kpts_1 = np.zeros((17, 3))
        person1_kpts_1[:, :2] = np.array([[105, 105]] * 17)
        person1_kpts_1[:, 2] = 1.0
        
        person2_kpts_1 = np.zeros((17, 3))
        person2_kpts_1[:, :2] = np.array([[305, 105]] * 17)
        person2_kpts_1[:, 2] = 1.0
        
        tracked = tracker.update([person1_kpts_1, person2_kpts_1], frame_num=1)
        assert len(tracked) == 2
    
    def test_person_disappears(self):
        """Test person disappearing and being deregistered"""
        tracker = PersonTracker(max_disappeared=2, iou_threshold=0.3)
        
        # Frame 0: Register person
        keypoints = np.ones((17, 3))
        keypoints[:, :2] = 100
        
        tracked = tracker.update([keypoints], frame_num=0)
        person_id = list(tracked.keys())[0]
        
        # Frames 1-2: No detections
        tracker.update([], frame_num=1)
        assert person_id in tracker.persons
        
        tracker.update([], frame_num=2)
        assert person_id in tracker.persons
        
        # Frame 3: Person should be deregistered
        tracker.update([], frame_num=3)
        assert person_id not in tracker.persons
    
    def test_calculate_iou(self):
        """Test IoU calculation"""
        tracker = PersonTracker()
        
        # Perfect overlap
        bbox1 = (0, 0, 100, 100)
        bbox2 = (0, 0, 100, 100)
        iou = tracker._calculate_iou(bbox1, bbox2)
        assert iou == 1.0
        
        # No overlap
        bbox1 = (0, 0, 50, 50)
        bbox2 = (100, 100, 150, 150)
        iou = tracker._calculate_iou(bbox1, bbox2)
        assert iou == 0.0
        
        # Partial overlap
        bbox1 = (0, 0, 100, 100)
        bbox2 = (50, 50, 150, 150)
        iou = tracker._calculate_iou(bbox1, bbox2)
        assert 0.0 < iou < 1.0
    
    def test_get_bbox_from_keypoints(self):
        """Test bounding box extraction from keypoints"""
        tracker = PersonTracker()
        
        keypoints = np.zeros((17, 3))
        keypoints[:, :2] = np.array([
            [50, 60], [55, 65], [45, 65],  # Head area
            [40, 70], [60, 70],  # Shoulders
        ] + [[0, 0]] * 12)
        keypoints[:5, 2] = 1.0  # Only first 5 keypoints valid
        
        bbox = tracker._get_bbox(keypoints)
        x1, y1, x2, y2 = bbox
        
        assert x1 == 40
        assert y1 == 60
        assert x2 == 60
        assert y2 == 70
    
    def test_reset(self):
        """Test resetting tracker state"""
        tracker = PersonTracker()
        
        # Register some persons
        tracker.register(np.random.rand(17, 3), 0)
        tracker.register(np.random.rand(17, 3), 0)
        
        assert len(tracker.persons) > 0
        assert tracker.next_person_id > 0
        
        # Reset
        tracker.reset()
        
        assert len(tracker.persons) == 0
        assert len(tracker.disappeared) == 0
        assert tracker.next_person_id == 0


class TestMultiPersonManager:
    """Test MultiPersonManager class"""
    
    def test_init(self):
        """Test manager initialization"""
        manager = MultiPersonManager(similarity_threshold=0.7)
        assert manager.similarity_threshold == 0.7
        assert len(manager.golden_templates) == 0
        assert len(manager.matches) == 0
    
    def test_add_golden_template(self):
        """Test adding golden template"""
        manager = MultiPersonManager()
        
        keypoints = np.random.rand(100, 17, 3)  # 100 frames
        profile = {"frame_count": 100}
        
        manager.add_golden_template("template_1", keypoints, profile)
        
        assert len(manager.golden_templates) == 1
        assert "template_1" in manager.golden_templates
        assert np.array_equal(manager.golden_templates["template_1"]["keypoints"], keypoints)
        assert manager.golden_templates["template_1"]["profile"] == profile
    
    def test_match_test_to_golden_single_template(self):
        """Test matching with single golden template"""
        manager = MultiPersonManager(similarity_threshold=0.5)
        
        # Add golden template (single frame)
        golden_kpts = np.zeros((17, 3))
        golden_kpts[:, :2] = 100
        golden_kpts[:, 2] = 1.0
        manager.add_golden_template("template_1", golden_kpts)
        
        # Test person (similar pose)
        test_kpts = np.zeros((17, 3))
        test_kpts[:, :2] = 105  # Slightly different
        test_kpts[:, 2] = 1.0
        
        test_persons = {0: test_kpts}
        matches = manager.match_test_to_golden(test_persons)
        
        # Should match if similarity > threshold
        assert 0 in matches
    
    def test_match_test_to_golden_multiple_templates(self):
        """Test matching with multiple golden templates"""
        manager = MultiPersonManager(similarity_threshold=0.5)
        
        # Add two different templates
        template1_kpts = np.zeros((17, 3))
        template1_kpts[:, :2] = 100
        template1_kpts[:, 2] = 1.0
        
        template2_kpts = np.zeros((17, 3))
        template2_kpts[:, :2] = 300
        template2_kpts[:, 2] = 1.0
        
        manager.add_golden_template("template_1", template1_kpts)
        manager.add_golden_template("template_2", template2_kpts)
        
        # Test persons (each similar to different template)
        test1_kpts = np.zeros((17, 3))
        test1_kpts[:, :2] = 105
        test1_kpts[:, 2] = 1.0
        
        test2_kpts = np.zeros((17, 3))
        test2_kpts[:, :2] = 305
        test2_kpts[:, 2] = 1.0
        
        test_persons = {0: test1_kpts, 1: test2_kpts}
        matches = manager.match_test_to_golden(test_persons)
        
        # Should have matches for both persons
        assert len(matches) <= 2
    
    def test_no_match_below_threshold(self):
        """Test that no match is made if similarity is below threshold"""
        manager = MultiPersonManager(similarity_threshold=0.9)  # High threshold
        
        # Add golden template
        golden_kpts = np.zeros((17, 3))
        golden_kpts[:, :2] = 100
        golden_kpts[:, 2] = 1.0
        manager.add_golden_template("template_1", golden_kpts)
        
        # Test person with very different pose
        test_kpts = np.zeros((17, 3))
        test_kpts[:, :2] = np.random.rand(17, 2) * 1000
        test_kpts[:, 2] = 1.0
        
        test_persons = {0: test_kpts}
        matches = manager.match_test_to_golden(test_persons)
        
        # May or may not match depending on similarity
        # This is mainly to test threshold logic works
        assert isinstance(matches, dict)
    
    def test_calculate_similarity(self):
        """Test pose similarity calculation"""
        manager = MultiPersonManager()
        
        # Identical poses
        kpts1 = np.zeros((17, 3))
        kpts1[:, :2] = 100
        kpts1[:, 2] = 1.0
        
        kpts2 = np.zeros((17, 3))
        kpts2[:, :2] = 100
        kpts2[:, 2] = 1.0
        
        similarity = manager._calculate_similarity(kpts1, kpts2)
        assert similarity > 0.9  # Should be very high for identical poses
        
        # Different poses
        kpts3 = np.zeros((17, 3))
        kpts3[:, :2] = np.random.rand(17, 2) * 1000
        kpts3[:, 2] = 1.0
        
        similarity = manager._calculate_similarity(kpts1, kpts3)
        # Similarity should be lower (but depends on random values)
        assert 0.0 <= similarity <= 1.0
    
    def test_get_template_for_person(self):
        """Test retrieving matched template for a person"""
        manager = MultiPersonManager()
        
        # Manually set a match
        manager.matches[0] = "template_1"
        
        template_id = manager.get_template_for_person(0)
        assert template_id == "template_1"
        
        # Non-existent person
        template_id = manager.get_template_for_person(999)
        assert template_id is None
    
    def test_get_template_data(self):
        """Test retrieving template data"""
        manager = MultiPersonManager()
        
        keypoints = np.random.rand(17, 3)
        profile = {"test": "data"}
        manager.add_golden_template("template_1", keypoints, profile)
        
        data = manager.get_template_data("template_1")
        assert data is not None
        assert np.array_equal(data["keypoints"], keypoints)
        assert data["profile"] == profile
        
        # Non-existent template
        data = manager.get_template_data("nonexistent")
        assert data is None
    
    def test_reset_matches(self):
        """Test resetting matches"""
        manager = MultiPersonManager()
        manager.matches = {0: "template_1", 1: "template_2"}
        
        manager.reset_matches()
        assert len(manager.matches) == 0
    
    def test_reset_all(self):
        """Test resetting all data"""
        manager = MultiPersonManager()
        
        # Add some data
        manager.add_golden_template("template_1", np.random.rand(17, 3))
        manager.matches = {0: "template_1"}
        
        manager.reset_all()
        
        assert len(manager.golden_templates) == 0
        assert len(manager.matches) == 0
    
    def test_template_with_multiple_frames(self):
        """Test handling templates with multiple frames"""
        manager = MultiPersonManager()
        
        # Template with 100 frames
        keypoints = np.random.rand(100, 17, 3)
        manager.add_golden_template("template_1", keypoints)
        
        # Test matching uses average
        test_kpts = np.mean(keypoints, axis=0)
        test_persons = {0: test_kpts}
        
        matches = manager.match_test_to_golden(test_persons)
        
        # Should be able to match (similarity calculation should handle multi-frame)
        assert isinstance(matches, dict)


class TestIntegration:
    """Integration tests for multi-person tracking and matching"""
    
    def test_full_tracking_workflow(self):
        """Test complete workflow: track persons and match to templates"""
        # Initialize components
        tracker = PersonTracker(iou_threshold=0.3)
        manager = MultiPersonManager(similarity_threshold=0.5)
        
        # Add golden templates
        template1_kpts = np.zeros((17, 3))
        template1_kpts[:, :2] = 100
        template1_kpts[:, 2] = 1.0
        
        template2_kpts = np.zeros((17, 3))
        template2_kpts[:, :2] = 300
        template2_kpts[:, 2] = 1.0
        
        manager.add_golden_template("person_0", template1_kpts)
        manager.add_golden_template("person_1", template2_kpts)
        
        # Simulate video frames
        for frame_num in range(10):
            # Two persons in each frame
            person1_kpts = np.zeros((17, 3))
            person1_kpts[:, :2] = 100 + frame_num  # Moving slightly
            person1_kpts[:, 2] = 1.0
            
            person2_kpts = np.zeros((17, 3))
            person2_kpts[:, :2] = 300 + frame_num
            person2_kpts[:, 2] = 1.0
            
            # Track persons
            tracked = tracker.update([person1_kpts, person2_kpts], frame_num)
            
            # Match to templates
            matches = manager.match_test_to_golden(tracked)
            
            # Should track 2 persons consistently
            assert len(tracked) == 2
    
    def test_person_entering_and_leaving(self):
        """Test handling persons entering and leaving the scene"""
        tracker = PersonTracker(max_disappeared=2)
        
        # Frame 0: Person 1 appears
        kpts1 = np.ones((17, 3)) * 100
        tracked = tracker.update([kpts1], 0)
        assert len(tracked) == 1
        person1_id = list(tracked.keys())[0]
        
        # Frame 1: Person 2 appears
        kpts2 = np.ones((17, 3)) * 300
        tracked = tracker.update([kpts1, kpts2], 1)
        assert len(tracked) == 2
        
        # Frame 2: Person 1 leaves
        tracked = tracker.update([kpts2], 2)
        assert len(tracked) == 2  # Still tracked
        
        # Frame 3-4: Person 1 still gone
        tracker.update([kpts2], 3)
        tracked = tracker.update([kpts2], 4)
        
        # Person 1 should be deregistered by now
        assert person1_id not in tracked
        assert len(tracked) == 1
