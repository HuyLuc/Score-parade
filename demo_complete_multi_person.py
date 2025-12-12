"""
Complete multi-person system demo showcasing all infrastructure features
"""
import sys
import pickle
import time
from pathlib import Path
import cv2
import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.pose_service import PoseService
from backend.app.services.multi_person_tracker import PersonTracker, MultiPersonManager
from backend.app.services.person_reidentification import PersonReIdentifier
from backend.app.utils.multi_person_visualizer import (
    draw_multi_person_tracking,
    create_multi_person_summary,
    draw_skeleton
)
from backend.app.utils.video_validator import VideoValidator
from backend.app.utils.progress_tracker import ProgressTracker
from backend.app.utils.cache_manager import CacheManager
from backend.app.config import (
    PERFORMANCE_CONFIG,
    ERROR_RECOVERY_CONFIG,
    VISUALIZATION_CONFIG,
    VIDEO_VALIDATION_CONFIG
)


def load_golden_templates(template_dir: str):
    """
    Load all golden templates from directory
    
    Args:
        template_dir: Directory containing person_*.pkl files
        
    Returns:
        Dict mapping template_id to template data
    """
    template_path = Path(template_dir)
    if not template_path.exists():
        print(f"❌ Error: Template directory not found: {template_dir}")
        return {}
    
    templates = {}
    for template_file in sorted(template_path.glob("person_*.pkl")):
        person_id = template_file.stem
        
        try:
            with open(template_file, 'rb') as f:
                template_data = pickle.load(f)
            
            # Extract keypoints
            keypoints = template_data.get("keypoints")
            if keypoints is None:
                keypoints = template_data.get("valid_skeletons")
            profile = template_data.get("profile", {})
            
            templates[person_id] = {
                "keypoints": keypoints,
                "profile": profile
            }
            
            print(f"✅ Loaded template: {person_id} ({len(keypoints)} frames)")
        except Exception as e:
            print(f"⚠️  Failed to load {template_file}: {e}")
    
    return templates


def demo_complete_workflow(
    test_video_path: str,
    template_dir: str,
    output_path: str = None,
    enable_caching: bool = True,
    enable_reid: bool = True,
    show_visualization: bool = True
):
    """
    Complete multi-person workflow demonstrating all infrastructure features
    
    Args:
        test_video_path: Path to test video with multiple people
        template_dir: Directory with golden templates
        output_path: Optional path to save output video
        enable_caching: Enable caching for faster re-runs
        enable_reid: Enable person re-identification
        show_visualization: Whether to display visualization
    """
    print("\n" + "="*80)
    print("🎬 COMPLETE MULTI-PERSON SYSTEM DEMO")
    print("="*80)
    
    # Step 1: Video Validation
    print("\n📹 Step 1: Validating video quality...")
    print("-" * 80)
    
    validator = VideoValidator()
    validation_result = validator.validate_video(test_video_path)
    validator.print_validation_report(validation_result)
    
    if not validation_result["valid"]:
        print("\n❌ Video validation failed! Please fix the issues and try again.")
        return
    
    # Step 2: Initialize cache manager
    print("\n💾 Step 2: Initializing cache manager...")
    print("-" * 80)
    
    cache_manager = CacheManager() if enable_caching else None
    
    if cache_manager:
        cache_manager.print_cache_stats()
        
        # Try to load from cache
        cached_data = cache_manager.get_cached_keypoints(test_video_path, config_hash="demo_v1")
        
        if cached_data:
            print("✅ Found cached keypoints! Loading from cache...")
            use_cache = True
        else:
            print("⚠️  No cache found. Will process and save to cache.")
            use_cache = False
    else:
        use_cache = False
    
    # Step 3: Load golden templates
    print("\n📁 Step 3: Loading golden templates...")
    print("-" * 80)
    
    golden_templates = load_golden_templates(template_dir)
    
    if len(golden_templates) == 0:
        print("❌ Error: No golden templates found!")
        return
    
    print(f"✅ Loaded {len(golden_templates)} templates: {list(golden_templates.keys())}")
    
    # Cache templates
    if cache_manager:
        for template_id, template_data in golden_templates.items():
            cache_manager.save_template(template_id, template_data)
        print("✅ Cached golden templates")
    
    # Step 4: Initialize services
    print("\n🤖 Step 4: Initializing processing services...")
    print("-" * 80)
    
    pose_service = PoseService()
    print(f"✅ Pose estimation initialized")
    
    # Initialize tracker with re-identification
    tracker = PersonTracker(
        max_disappeared=ERROR_RECOVERY_CONFIG["max_disappeared_frames"],
        iou_threshold=0.5,
        enable_reid=enable_reid
    )
    print(f"✅ Person tracker initialized (Re-ID: {enable_reid})")
    
    # Initialize multi-person manager
    manager = MultiPersonManager(similarity_threshold=0.6)
    for template_id, template_data in golden_templates.items():
        manager.add_golden_template(template_id, template_data["keypoints"], template_data["profile"])
    print(f"✅ Multi-person manager initialized")
    
    # Step 5: Process video
    print("\n🎥 Step 5: Processing video...")
    print("-" * 80)
    
    cap = cv2.VideoCapture(test_video_path)
    if not cap.isOpened():
        print("❌ Error: Could not open video")
        return
    
    # Get video properties
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"📊 Video info: {width}x{height} @ {fps:.1f} FPS, {total_frames} frames")
    
    # Initialize progress tracker
    progress = ProgressTracker(total=total_frames, description="Processing frames")
    
    # Prepare output video writer
    output_writer = None
    if output_path and VISUALIZATION_CONFIG.get("save_visualizations", True):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        output_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        print(f"✅ Output video writer initialized: {output_path}")
    
    # Process frames
    all_keypoints = [] if not use_cache else cached_data["keypoints"]
    frame_results = []
    processing_start = time.time()
    
    if not use_cache:
        # Batch processing settings
        use_batch = PERFORMANCE_CONFIG.get("enable_batch_processing", True)
        batch_size = PERFORMANCE_CONFIG.get("batch_size", 8)
        
        frame_idx = 0
        batch_frames = []
        batch_frame_indices = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if use_batch:
                batch_frames.append(frame)
                batch_frame_indices.append(frame_idx)
                
                # Process batch when full or at end
                if len(batch_frames) >= batch_size or frame_idx == total_frames - 1:
                    # Batch process
                    batch_detections = pose_service.predict_batch_multi_person(
                        batch_frames, 
                        batch_size=batch_size
                    )
                    
                    # Process each frame in batch
                    for i, (frame_img, detections) in enumerate(zip(batch_frames, batch_detections)):
                        # Extract keypoints
                        keypoints_list = [det["keypoints"] for det in detections]
                        all_keypoints.append(keypoints_list)
                        
                        # Update tracker
                        tracked_persons = tracker.update(keypoints_list, batch_frame_indices[i])
                        
                        # Match to templates
                        matches = manager.match_test_to_golden(tracked_persons)
                        
                        # Visualize if enabled
                        if VISUALIZATION_CONFIG.get("enabled", True):
                            annotated = draw_multi_person_tracking(
                                frame_img,
                                tracked_persons,
                                matches,
                                {}  # Empty errors for this demo
                            )
                            
                            if output_writer:
                                output_writer.write(annotated)
                            
                            if show_visualization:
                                cv2.imshow("Multi-Person Tracking", annotated)
                                if cv2.waitKey(1) & 0xFF == ord('q'):
                                    break
                        
                        # Update progress
                        progress.update(1)
                    
                    # Clear batch
                    batch_frames = []
                    batch_frame_indices = []
            else:
                # Single frame processing
                detections = pose_service.predict_multi_person(frame)
                keypoints_list = [det["keypoints"] for det in detections]
                all_keypoints.append(keypoints_list)
                
                # Update tracker
                tracked_persons = tracker.update(keypoints_list, frame_idx)
                
                # Match to templates
                matches = manager.match_test_to_golden(tracked_persons)
                
                # Visualize
                if VISUALIZATION_CONFIG.get("enabled", True):
                    annotated = draw_multi_person_tracking(frame, tracked_persons, matches, {})
                    
                    if output_writer:
                        output_writer.write(annotated)
                    
                    if show_visualization:
                        cv2.imshow("Multi-Person Tracking", annotated)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                
                progress.update(1)
            
            frame_idx += 1
        
        # Save to cache
        if cache_manager:
            print("\n💾 Saving processed data to cache...")
            cache_manager.save_keypoints(
                test_video_path,
                all_keypoints,
                config_hash="demo_v1",
                additional_metadata={
                    "total_frames": total_frames,
                    "fps": fps,
                    "resolution": f"{width}x{height}"
                }
            )
            print("✅ Saved to cache for faster future runs")
    else:
        # Using cached data - just visualize
        print("📊 Using cached keypoints for visualization...")
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        for frame_idx in range(min(len(all_keypoints), total_frames)):
            ret, frame = cap.read()
            if not ret:
                break
            
            keypoints_list = all_keypoints[frame_idx]
            
            # Update tracker
            tracked_persons = tracker.update(keypoints_list, frame_idx)
            
            # Match to templates
            matches = manager.match_test_to_golden(tracked_persons)
            
            # Visualize
            if VISUALIZATION_CONFIG.get("enabled", True):
                annotated = draw_multi_person_tracking(frame, tracked_persons, matches, {})
                
                if output_writer:
                    output_writer.write(annotated)
                
                if show_visualization:
                    cv2.imshow("Multi-Person Tracking (Cached)", annotated)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            
            progress.update(1)
    
    # Cleanup
    cap.release()
    if output_writer:
        output_writer.release()
    cv2.destroyAllWindows()
    
    processing_time = time.time() - processing_start
    avg_fps = total_frames / processing_time if processing_time > 0 else 0
    
    # Step 6: Display results
    print("\n" + "="*80)
    print("📊 PROCESSING COMPLETE")
    print("="*80)
    print(f"\n⏱️  Processing time: {processing_time:.2f}s")
    print(f"🚀 Average FPS: {avg_fps:.1f}")
    print(f"📹 Total frames: {total_frames}")
    
    if enable_reid and tracker.reidentifier:
        print(f"🔄 Re-identification enabled: Yes")
        print(f"   Currently disappeared persons: {tracker.reidentifier.get_disappeared_count()}")
    
    if cache_manager:
        print("\n💾 Cache statistics:")
        cache_manager.print_cache_stats()
    
    if output_path and output_writer:
        print(f"\n✅ Output saved to: {output_path}")
    
    print("\n" + "="*80)
    print("Demo complete! 🎉")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Complete multi-person system demo")
    parser.add_argument("--video", type=str, required=True, help="Path to test video")
    parser.add_argument("--templates", type=str, required=True, help="Directory with golden templates")
    parser.add_argument("--output", type=str, help="Path to save output video")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--no-reid", action="store_true", help="Disable re-identification")
    parser.add_argument("--no-viz", action="store_true", help="Disable visualization display")
    
    args = parser.parse_args()
    
    demo_complete_workflow(
        test_video_path=args.video,
        template_dir=args.templates,
        output_path=args.output,
        enable_caching=not args.no_cache,
        enable_reid=not args.no_reid,
        show_visualization=not args.no_viz
    )
