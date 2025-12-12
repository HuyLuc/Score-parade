"""
Demo script for multi-person tracking and evaluation
"""
import sys
import pickle
from pathlib import Path
import cv2
import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.pose_service import PoseService
from backend.app.controllers.ai_controller import AIController
from backend.app.utils.multi_person_visualizer import (
    draw_multi_person_tracking,
    create_multi_person_summary
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
        # Extract person ID from filename
        person_id = template_file.stem  # e.g., "person_0"
        
        try:
            with open(template_file, 'rb') as f:
                template_data = pickle.load(f)
            
            # Extract keypoints and profile
            keypoints = template_data.get("keypoints") or template_data.get("valid_skeletons")
            profile = template_data.get("profile", {})
            
            templates[person_id] = {
                "keypoints": keypoints,
                "profile": profile
            }
            
            print(f"✅ Loaded template: {person_id} ({len(keypoints)} frames)")
        except Exception as e:
            print(f"⚠️  Failed to load {template_file}: {e}")
    
    return templates


def demo_multi_person_evaluation(
    test_video_path: str,
    template_dir: str,
    output_path: str = None,
    show_visualization: bool = True
):
    """
    Demo workflow for multi-person evaluation
    
    Args:
        test_video_path: Path to test video with multiple people
        template_dir: Directory with golden templates
        output_path: Optional path to save output video
        show_visualization: Whether to display visualization
    """
    print("🎬 Multi-Person Evaluation Demo")
    print("=" * 60)
    
    # Step 1: Load golden templates
    print("\n📁 Step 1: Loading golden templates...")
    golden_templates = load_golden_templates(template_dir)
    
    if len(golden_templates) == 0:
        print("❌ Error: No golden templates found!")
        return
    
    print(f"   Loaded {len(golden_templates)} templates: {list(golden_templates.keys())}")
    
    # Step 2: Initialize AI controller
    print("\n🤖 Step 2: Initializing AI controller...")
    pose_service = PoseService()
    ai_controller = AIController(pose_service)
    
    # Step 3: Enable multi-person mode
    print("\n👥 Step 3: Enabling multi-person mode...")
    ai_controller.enable_multi_person_mode(golden_templates)
    
    # Step 4: Process test video
    print("\n🎥 Step 4: Processing test video...")
    print(f"   Video: {test_video_path}")
    
    results = ai_controller.process_video_multi_person(test_video_path)
    
    # Step 5: Display results
    print("\n📊 Step 5: Evaluation Results")
    print("=" * 60)
    
    for person_id, result in sorted(results.items()):
        print(f"\n👤 Person {person_id}:")
        print(f"   Matched Template: {result['matched_template']}")
        print(f"   Score: {result['score']:.2f}/100")
        print(f"   Total Errors: {len(result['errors'])}")
        print(f"   Frames Evaluated: {result['frame_count']}")
        
        # Show error breakdown
        error_types = {}
        for error in result['errors']:
            error_type = error.get('type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if error_types:
            print(f"   Error Breakdown:")
            for error_type, count in sorted(error_types.items()):
                print(f"     - {error_type}: {count}")
    
    # Step 6: Create visualization
    if show_visualization or output_path:
        print("\n🎨 Step 6: Creating visualization...")
        
        cap = cv2.VideoCapture(test_video_path)
        if not cap.isOpened():
            print(f"❌ Error: Cannot open video for visualization")
            return
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Setup video writer if output path specified
        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            print(f"   Saving to: {output_path}")
        
        # Reset tracker for visualization pass
        ai_controller.person_tracker.reset()
        ai_controller.multi_person_manager.reset_matches()
        
        frame_number = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame
            detections = pose_service.predict_multi_person(frame)
            detection_keypoints = [d["keypoints"] for d in detections]
            
            # Track persons
            tracked_persons = ai_controller.person_tracker.update(detection_keypoints, frame_number)
            
            # Match persons to templates
            matches = ai_controller.multi_person_manager.match_test_to_golden(tracked_persons)
            
            # Get errors for this frame
            frame_errors = {}
            for person_id in tracked_persons.keys():
                person_errors = [e for e in results.get(person_id, {}).get('errors', [])
                               if e.get('frame_number') == frame_number]
                frame_errors[person_id] = person_errors
            
            # Draw visualization
            annotated = draw_multi_person_tracking(frame, tracked_persons, matches, frame_errors)
            
            # Write to output video
            if writer is not None:
                writer.write(annotated)
            
            # Display
            if show_visualization:
                cv2.imshow('Multi-Person Tracking', annotated)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            frame_number += 1
            
            if frame_number % 30 == 0:
                print(f"   Processed {frame_number} frames...")
        
        cap.release()
        if writer is not None:
            writer.release()
        if show_visualization:
            cv2.destroyAllWindows()
    
    # Step 7: Create summary
    print("\n📋 Step 7: Creating summary visualization...")
    summary = create_multi_person_summary(results)
    
    if show_visualization:
        cv2.imshow('Evaluation Summary', summary)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    # Save summary
    if output_path:
        summary_path = Path(output_path).parent / "summary.png"
        cv2.imwrite(str(summary_path), summary)
        print(f"   Summary saved to: {summary_path}")
    
    print("\n✅ Demo complete!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Demo multi-person tracking and evaluation"
    )
    parser.add_argument(
        "test_video",
        help="Path to test video with multiple people"
    )
    parser.add_argument(
        "-t", "--templates",
        default="data/multi_person_templates",
        help="Directory with golden templates (default: data/multi_person_templates)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Optional path to save output video"
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable visualization display (useful for headless environments)"
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not Path(args.test_video).exists():
        print(f"❌ Error: Test video not found: {args.test_video}")
        sys.exit(1)
    
    if not Path(args.templates).exists():
        print(f"❌ Error: Template directory not found: {args.templates}")
        sys.exit(1)
    
    # Run demo
    demo_multi_person_evaluation(
        test_video_path=args.test_video,
        template_dir=args.templates,
        output_path=args.output,
        show_visualization=not args.no_display
    )


if __name__ == "__main__":
    main()
