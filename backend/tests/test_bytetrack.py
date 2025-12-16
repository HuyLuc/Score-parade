"""
Test ByteTrack implementation
"""
import cv2
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.app.services.pose_service import PoseService
from backend.app.services.bytetrack_service import ByteTrackService
from backend.app.config import MULTI_PERSON_CONFIG


def test_bytetrack(video_path: str, max_frames: int = None):
    """
    Test ByteTrack trên video
    """
    print("=" * 80)
    print("TESTING BYTETRACK MULTI-PERSON TRACKING")
    print("=" * 80)
    print(f"Video: {video_path}")
    
    # Khởi tạo services
    pose_service = PoseService()
    
    bytetrack_config = MULTI_PERSON_CONFIG.get("bytetrack", {})
    bytetrack = ByteTrackService(
        track_thresh=bytetrack_config.get("track_thresh", 0.5),
        track_buffer=bytetrack_config.get("track_buffer", 30),
        match_thresh=bytetrack_config.get("match_thresh", 0.8),
        high_thresh=bytetrack_config.get("high_thresh", 0.6),
        low_thresh=bytetrack_config.get("low_thresh", 0.1),
    )
    
    print(f"\nByteTrack Config:")
    print(f"  - track_thresh: {bytetrack_config.get('track_thresh', 0.5)}")
    print(f"  - track_buffer: {bytetrack_config.get('track_buffer', 30)}")
    print(f"  - match_thresh: {bytetrack_config.get('match_thresh', 0.8)}")
    print(f"  - high_thresh: {bytetrack_config.get('high_thresh', 0.6)}")
    print(f"  - low_thresh: {bytetrack_config.get('low_thresh', 0.1)}")
    
    # Mở video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video {video_path}")
        return
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"\nVideo Info:")
    print(f"  - Total frames: {total_frames}")
    print(f"  - FPS: {fps}")
    print(f"  - Duration: {total_frames / fps:.2f}s")
    
    if max_frames:
        total_frames = min(total_frames, max_frames)
        print(f"  - Processing: {total_frames} frames")
    
    print("=" * 80)
    
    frame_num = 0
    track_counts = []
    active_ids = set()
    
    # Statistics
    id_switches = 0
    prev_frame_ids = set()
    
    while True:
        if max_frames and frame_num >= max_frames:
            break
            
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_num += 1
        
        # Detect persons
        detections_meta = pose_service.predict_multi_person(frame)
        
        # Prepare for ByteTrack
        detections_for_bytetrack = []
        for det in detections_meta:
            detections_for_bytetrack.append({
                "bbox": det["bbox"],
                "score": det["confidence"],
                "keypoints": det["keypoints"]
            })
        
        # Update ByteTrack
        tracks = bytetrack.update(detections_for_bytetrack, frame_num)
        track_counts.append(len(tracks))
        
        current_frame_ids = {track.track_id for track in tracks}
        active_ids.update(current_frame_ids)
        
        # Count ID switches (tracks that disappeared and new tracks appeared)
        disappeared = prev_frame_ids - current_frame_ids
        appeared = current_frame_ids - prev_frame_ids
        if frame_num > 1 and (disappeared or appeared):
            id_switches += len(appeared)
        
        prev_frame_ids = current_frame_ids
        
        # Print progress
        if frame_num % 30 == 0 or len(tracks) > 0:
            print(f"Frame {frame_num:4d}/{total_frames}: "
                  f"{len(detections_meta)} detections → "
                  f"{len(tracks)} tracks (IDs: {sorted([t.track_id for t in tracks])})")
    
    cap.release()
    
    # Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    
    if track_counts:
        avg_tracks = sum(track_counts) / len(track_counts)
        max_tracks = max(track_counts)
        
        print(f"\nTracking Statistics:")
        print(f"  - Average tracks per frame: {avg_tracks:.2f}")
        print(f"  - Max tracks in a frame: {max_tracks}")
        print(f"  - Total unique track IDs: {len(active_ids)}")
        print(f"  - ID switches: {id_switches}")
    
    # Get stable persons
    stable_ids = bytetrack.get_stable_track_ids(
        min_frames=30,
        min_height=50.0,
        min_frame_ratio=0.85,
    )
    
    print(f"\nStable Persons (người thật):")
    print(f"  - Count: {len(stable_ids)}")
    print(f"  - IDs: {stable_ids}")
    
    # Per-person statistics
    if stable_ids:
        print(f"\nPer-Person Details:")
        all_tracks = bytetrack.tracked_stracks + bytetrack.lost_stracks + bytetrack.removed_stracks
        
        for track_id in stable_ids:
            track = next((t for t in all_tracks if t.track_id == track_id), None)
            if track:
                frames_seen = track.frames_seen
                avg_height = track.total_height / max(frames_seen, 1)
                avg_score = sum(track.score_history) / len(track.score_history) if track.score_history else 0
                
                print(f"  Person {track_id}:")
                print(f"    - Frames: {frames_seen}/{frame_num} ({100*frames_seen/frame_num:.1f}%)")
                print(f"    - First/Last: {track.first_frame}/{track.last_frame}")
                print(f"    - Avg height: {avg_height:.1f}px")
                print(f"    - Avg confidence: {avg_score:.3f}")
                print(f"    - State: {track.state}")
    
    # Quality metrics
    print(f"\nQuality Metrics:")
    if frame_num > 0:
        print(f"  - ID Switches Rate: {id_switches / frame_num:.4f} per frame")
        print(f"  - Track Stability: {len(stable_ids) / max(len(active_ids), 1):.2%}")
        
        # Compare với expected (nếu biết trước)
        # expected_persons = 2  # Điều chỉnh theo video
        # if len(stable_ids) == expected_persons:
        #     print(f"  - ✅ Detection: CORRECT ({len(stable_ids)} persons)")
        # else:
        #     print(f"  - ❌ Detection: INCORRECT (detected {len(stable_ids)}, expected {expected_persons})")
    
    print("\n" + "=" * 80)
    
    # Recommendations
    print("\nRECOMMENDATIONS:")
    if id_switches / frame_num > 0.1:
        print("  ⚠️  High ID switch rate! Consider:")
        print("     - Increasing match_thresh")
        print("     - Increasing track_buffer")
    
    if len(stable_ids) > len(active_ids) * 0.5:
        print("  ⚠️  Too many stable tracks! Consider:")
        print("     - Increasing min_frames")
        print("     - Increasing min_frame_ratio")
    elif len(stable_ids) < 1 and len(active_ids) > 0:
        print("  ⚠️  No stable tracks detected! Consider:")
        print("     - Decreasing min_frames")
        print("     - Decreasing min_frame_ratio")
    else:
        print("  ✅ Tracking parameters look good!")
    
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_bytetrack.py <video_path> [max_frames]")
        print("Example: python test_bytetrack.py ../data/input_videos/test.mp4 300")
        sys.exit(1)
    
    video_path = sys.argv[1]
    max_frames = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    test_bytetrack(video_path, max_frames)
