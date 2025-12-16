"""
Script để test việc phát hiện số người trong video
"""
import cv2
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.app.services.pose_service import PoseService
from backend.app.services.tracker_service import TrackerService, Detection
from backend.app.config import MULTI_PERSON_CONFIG


def test_person_detection(video_path: str):
    """
    Test việc phát hiện số người trong video
    
    Args:
        video_path: Đường dẫn đến video cần test
    """
    print(f"Testing person detection on: {video_path}")
    print("=" * 60)
    
    # Khởi tạo services
    pose_service = PoseService()
    tracker_service = TrackerService(
        max_disappeared=MULTI_PERSON_CONFIG.get("max_disappeared", 60),
        iou_threshold=MULTI_PERSON_CONFIG.get("iou_threshold", 0.25),
    )
    
    # Mở video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video {video_path}")
        return
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"Total frames: {total_frames}")
    print(f"FPS: {fps}")
    print(f"Duration: {total_frames / fps:.2f}s")
    print("=" * 60)
    
    frame_num = 0
    detection_counts = []
    track_counts = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_num += 1
        
        # Detect persons
        detections_meta = pose_service.predict_multi_person(frame)
        detection_counts.append(len(detections_meta))
        
        # Create Detection objects for tracker
        detections_for_tracker = []
        for det in detections_meta:
            kpts = det["keypoints"]
            bbox = det["bbox"]
            conf = det["confidence"]
            detections_for_tracker.append(Detection(bbox=bbox, score=conf, keypoints=kpts))
        
        # Update tracker
        tracks = tracker_service.update(detections_for_tracker, frame_num)
        track_counts.append(len(tracks))
        
        # Print progress every 30 frames
        if frame_num % 30 == 0:
            print(f"Frame {frame_num}/{total_frames}: "
                  f"Detected {len(detections_meta)} persons, "
                  f"Tracking {len(tracks)} persons")
    
    cap.release()
    
    # Phân tích kết quả
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    
    if detection_counts:
        avg_detections = sum(detection_counts) / len(detection_counts)
        max_detections = max(detection_counts)
        min_detections = min(detection_counts)
        
        print(f"Detections per frame:")
        print(f"  - Average: {avg_detections:.2f}")
        print(f"  - Max: {max_detections}")
        print(f"  - Min: {min_detections}")
    
    if track_counts:
        avg_tracks = sum(track_counts) / len(track_counts)
        max_tracks = max(track_counts)
        
        print(f"\nTracks per frame:")
        print(f"  - Average: {avg_tracks:.2f}")
        print(f"  - Max: {max_tracks}")
    
    # Get stable persons
    stable_ids = tracker_service.get_stable_track_ids(
        min_frames=30,
        min_height=50.0,
        min_frame_ratio=0.85,
    )
    
    print(f"\nStable person IDs (người thật trong video): {stable_ids}")
    print(f"Total stable persons: {len(stable_ids)}")
    
    # Show stats for each stable person
    if stable_ids:
        print("\nPer-person statistics:")
        for track_id in stable_ids:
            stats = tracker_service.stats.get(track_id)
            if stats:
                frames_seen = stats.get("frames_seen", 0)
                first_frame = stats.get("first_frame", 0)
                last_frame = stats.get("last_frame", 0)
                total_height = stats.get("total_height", 0.0)
                avg_height = total_height / max(frames_seen, 1)
                
                print(f"  Person {track_id}:")
                print(f"    - Frames seen: {frames_seen}/{total_frames} ({100*frames_seen/total_frames:.1f}%)")
                print(f"    - First/Last frame: {first_frame}/{last_frame}")
                print(f"    - Average height: {avg_height:.1f}px")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_person_detection.py <video_path>")
        print("Example: python test_person_detection.py ../data/input_videos/test.mp4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    test_person_detection(video_path)
