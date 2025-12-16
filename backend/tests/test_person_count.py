"""
Test script to verify correct person detection and tracking
Tests that the system detects the correct number of people in videos
"""
import sys
import cv2
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.pose_service import PoseService
from backend.app.services.bytetrack_service import ByteTrackService
from backend.app.config import MULTI_PERSON_CONFIG


def test_person_detection(video_path: str, expected_persons: int = 2):
    """
    Test person detection and tracking on a video
    
    Args:
        video_path: Path to video file
        expected_persons: Expected number of people in video
    """
    print(f"\n{'='*60}")
    print(f"Testing Person Detection: {video_path}")
    print(f"Expected persons: {expected_persons}")
    print(f"{'='*60}\n")
    
    # Initialize services
    pose_service = PoseService()
    
    bytetrack_config = MULTI_PERSON_CONFIG.get("bytetrack", {})
    bytetrack = ByteTrackService(
        track_thresh=bytetrack_config.get("track_thresh", 0.35),
        track_buffer=bytetrack_config.get("track_buffer", 50),
        match_thresh=bytetrack_config.get("match_thresh", 0.7),
        high_thresh=bytetrack_config.get("high_thresh", 0.45),
        low_thresh=bytetrack_config.get("low_thresh", 0.1),
    )
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"📹 Video info:")
    print(f"   - FPS: {fps:.2f}")
    print(f"   - Total frames: {total_frames}")
    print(f"   - Duration: {total_frames/fps:.2f}s\n")
    
    # Tracking statistics
    frame_id = 0
    all_track_ids = set()
    track_stats = {}  # track_id -> {frames_seen, first_frame, last_frame, heights}
    detections_per_frame = []
    
    print("Processing frames...")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_id += 1
        
        # Detect persons
        detections = pose_service.predict_multi_person(frame)
        detections_per_frame.append(len(detections))
        
        # Update tracker
        detections_for_tracker = []
        for det in detections:
            detections_for_tracker.append({
                "bbox": det["bbox"],
                "score": det["confidence"],
                "keypoints": det["keypoints"]
            })
        
        tracks = bytetrack.update(detections_for_tracker, frame_id)
        
        # Update statistics
        for track in tracks:
            track_id = track.track_id
            all_track_ids.add(track_id)
            
            if track_id not in track_stats:
                track_stats[track_id] = {
                    "frames_seen": 0,
                    "first_frame": frame_id,
                    "last_frame": frame_id,
                    "heights": [],
                }
            
            track_stats[track_id]["frames_seen"] += 1
            track_stats[track_id]["last_frame"] = frame_id
            track_stats[track_id]["heights"].append(track.bbox_xywh[3])
        
        # Progress
        if frame_id % 30 == 0:
            print(f"   Frame {frame_id}/{total_frames} - Detections: {len(detections)}, Active tracks: {len(tracks)}")
    
    cap.release()
    
    # Get stable track IDs
    stable_ids = bytetrack.get_stable_track_ids(
        min_frames=20,
        min_height=40.0,
        min_frame_ratio=0.70,
    )
    
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}\n")
    
    # Detection statistics
    avg_detections = np.mean(detections_per_frame)
    max_detections = np.max(detections_per_frame)
    
    print(f"📊 Detection Statistics:")
    print(f"   - Average detections per frame: {avg_detections:.2f}")
    print(f"   - Max detections in single frame: {max_detections}")
    print(f"   - Total unique track IDs created: {len(all_track_ids)}")
    print(f"   - Stable track IDs: {len(stable_ids)}")
    print()
    
    # Track details
    print(f"📋 Track Details:")
    print(f"{'ID':<6} {'Frames':<10} {'Duration':<15} {'Avg Height':<12} {'Status'}")
    print("-" * 60)
    
    for track_id in sorted(all_track_ids):
        stats = track_stats[track_id]
        frames = stats["frames_seen"]
        first = stats["first_frame"]
        last = stats["last_frame"]
        duration = f"{first}-{last}"
        avg_height = np.mean(stats["heights"]) if stats["heights"] else 0
        is_stable = "✅ STABLE" if track_id in stable_ids else "❌ Unstable"
        
        print(f"{track_id:<6} {frames:<10} {duration:<15} {avg_height:<12.1f} {is_stable}")
    
    print()
    
    # Verdict
    print(f"{'='*60}")
    if len(stable_ids) == expected_persons:
        print(f"✅ SUCCESS: Detected {len(stable_ids)} persons (expected {expected_persons})")
    else:
        print(f"❌ FAILED: Detected {len(stable_ids)} persons (expected {expected_persons})")
    
    if len(all_track_ids) > len(stable_ids) * 2:
        print(f"⚠️  WARNING: Too many temporary IDs ({len(all_track_ids)} total)")
        print(f"   This indicates ID switching or false detections")
    
    print(f"{'='*60}\n")
    
    # Recommendations
    if len(stable_ids) < expected_persons:
        print("💡 Recommendations:")
        print("   - Check if all persons are visible throughout the video")
        print("   - Consider lowering conf_threshold in POSE_CONFIG")
        print("   - Consider lowering track_thresh in bytetrack config")
        print("   - Check video quality and lighting conditions")
    elif len(stable_ids) > expected_persons:
        print("💡 Recommendations:")
        print("   - Consider raising conf_threshold in POSE_CONFIG")
        print("   - Consider raising track_thresh in bytetrack config")
        print("   - Check for reflections or background people")
    
    return len(stable_ids) == expected_persons


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_person_count.py <video_path> [expected_persons]")
        print("Example: python test_person_count.py data/input_videos/test.mp4 2")
        sys.exit(1)
    
    video_path = sys.argv[1]
    expected_persons = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    success = test_person_detection(video_path, expected_persons)
    sys.exit(0 if success else 1)
