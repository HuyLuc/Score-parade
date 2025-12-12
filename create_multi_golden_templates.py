"""
Script to create multiple golden templates from video with multiple people
"""
import sys
import pickle
import json
from pathlib import Path
import cv2
import numpy as np
from typing import Dict, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.pose_service import PoseService
from backend.app.services.multi_person_tracker import PersonTracker
from backend.app.config import MULTI_PERSON_CONFIG


def calculate_statistics(keypoints_sequence: np.ndarray) -> Dict:
    """
    Calculate statistics for a keypoints sequence
    
    Args:
        keypoints_sequence: Keypoints array [n_frames, 17, 3]
        
    Returns:
        Dict containing statistics (mean, std) for various metrics
    """
    from backend.app.services.geometry import (
        calculate_arm_angle,
        calculate_leg_angle,
        calculate_arm_height,
        calculate_leg_height,
        calculate_head_angle,
        calculate_torso_stability
    )
    
    statistics = {
        "arm_angle": {"left": {}, "right": {}},
        "leg_angle": {"left": {}, "right": {}},
        "arm_height": {"left": {}, "right": {}},
        "leg_height": {"left": {}, "right": {}},
        "head_angle": {},
        "torso_stability": {}
    }
    
    # Collect metrics for all frames
    arm_angles_left = []
    arm_angles_right = []
    leg_angles_left = []
    leg_angles_right = []
    arm_heights_left = []
    arm_heights_right = []
    leg_heights_left = []
    leg_heights_right = []
    head_angles = []
    torso_stabilities = []
    
    for keypoints in keypoints_sequence:
        # Arm angles
        left_arm_angle = calculate_arm_angle(keypoints, "left")
        right_arm_angle = calculate_arm_angle(keypoints, "right")
        if left_arm_angle is not None:
            arm_angles_left.append(left_arm_angle)
        if right_arm_angle is not None:
            arm_angles_right.append(right_arm_angle)
        
        # Leg angles
        left_leg_angle = calculate_leg_angle(keypoints, "left")
        right_leg_angle = calculate_leg_angle(keypoints, "right")
        if left_leg_angle is not None:
            leg_angles_left.append(left_leg_angle)
        if right_leg_angle is not None:
            leg_angles_right.append(right_leg_angle)
        
        # Heights
        left_arm_height = calculate_arm_height(keypoints, "left")
        right_arm_height = calculate_arm_height(keypoints, "right")
        if left_arm_height is not None:
            arm_heights_left.append(left_arm_height)
        if right_arm_height is not None:
            arm_heights_right.append(right_arm_height)
        
        left_leg_height = calculate_leg_height(keypoints, "left")
        right_leg_height = calculate_leg_height(keypoints, "right")
        if left_leg_height is not None:
            leg_heights_left.append(left_leg_height)
        if right_leg_height is not None:
            leg_heights_right.append(right_leg_height)
        
        # Head angle
        head_angle = calculate_head_angle(keypoints)
        if head_angle is not None:
            head_angles.append(head_angle)
        
        # Torso stability
        torso_stability = calculate_torso_stability(keypoints)
        if torso_stability is not None:
            torso_stabilities.append(torso_stability)
    
    # Calculate statistics
    if arm_angles_left:
        statistics["arm_angle"]["left"] = {
            "mean": float(np.mean(arm_angles_left)),
            "std": float(np.std(arm_angles_left))
        }
    if arm_angles_right:
        statistics["arm_angle"]["right"] = {
            "mean": float(np.mean(arm_angles_right)),
            "std": float(np.std(arm_angles_right))
        }
    
    if leg_angles_left:
        statistics["leg_angle"]["left"] = {
            "mean": float(np.mean(leg_angles_left)),
            "std": float(np.std(leg_angles_left))
        }
    if leg_angles_right:
        statistics["leg_angle"]["right"] = {
            "mean": float(np.mean(leg_angles_right)),
            "std": float(np.std(leg_angles_right))
        }
    
    if arm_heights_left:
        statistics["arm_height"]["left"] = {
            "mean": float(np.mean(arm_heights_left)),
            "std": float(np.std(arm_heights_left))
        }
    if arm_heights_right:
        statistics["arm_height"]["right"] = {
            "mean": float(np.mean(arm_heights_right)),
            "std": float(np.std(arm_heights_right))
        }
    
    if leg_heights_left:
        statistics["leg_height"]["left"] = {
            "mean": float(np.mean(leg_heights_left)),
            "std": float(np.std(leg_heights_left))
        }
    if leg_heights_right:
        statistics["leg_height"]["right"] = {
            "mean": float(np.mean(leg_heights_right)),
            "std": float(np.std(leg_heights_right))
        }
    
    if head_angles:
        statistics["head_angle"] = {
            "mean": float(np.mean(head_angles)),
            "std": float(np.std(head_angles))
        }
    
    if torso_stabilities:
        statistics["torso_stability"] = {
            "mean": float(np.mean(torso_stabilities)),
            "std": float(np.std(torso_stabilities))
        }
    
    return statistics


def create_multi_golden_templates(video_path: str, output_dir: str):
    """
    Process video with multiple people and create separate golden template for each
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save templates
        
    Output:
        Creates files: person_0.pkl, person_1.pkl, etc.
        Each file contains: {"keypoints": [...], "profile": {...}}
    """
    print(f"🎬 Processing video: {video_path}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize services
    pose_service = PoseService()
    max_disappeared = MULTI_PERSON_CONFIG.get("max_disappeared", 30)
    iou_threshold = MULTI_PERSON_CONFIG.get("iou_threshold", 0.5)
    tracker = PersonTracker(max_disappeared=max_disappeared, iou_threshold=iou_threshold)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Error: Cannot open video {video_path}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"📊 Video info: {total_frames} frames @ {fps:.1f} fps")
    
    # Track all persons throughout video
    person_keypoints_sequences = {}  # {person_id: [keypoints_per_frame]}
    
    frame_number = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detect all persons in frame
        detections = pose_service.predict_multi_person(frame)
        detection_keypoints = [d["keypoints"] for d in detections]
        
        # Track persons
        tracked_persons = tracker.update(detection_keypoints, frame_number)
        
        # Store keypoints for each person
        for person_id, keypoints in tracked_persons.items():
            if person_id not in person_keypoints_sequences:
                person_keypoints_sequences[person_id] = []
            person_keypoints_sequences[person_id].append(keypoints)
        
        frame_number += 1
        
        # Progress
        if frame_number % 30 == 0:
            print(f"  Progress: {frame_number}/{total_frames} frames, "
                  f"{len(person_keypoints_sequences)} persons detected")
    
    cap.release()
    
    print(f"\n✅ Video processing complete!")
    print(f"   Detected {len(person_keypoints_sequences)} persons")
    
    # Create template for each person
    for person_id, keypoints_list in person_keypoints_sequences.items():
        if len(keypoints_list) < 10:
            print(f"⚠️  Skipping person {person_id} (only {len(keypoints_list)} frames)")
            continue
        
        # Convert to numpy array
        keypoints_sequence = np.array(keypoints_list)  # [n_frames, 17, 3]
        
        print(f"\n👤 Creating template for person {person_id}:")
        print(f"   Frames: {len(keypoints_list)}")
        
        # Calculate statistics
        statistics = calculate_statistics(keypoints_sequence)
        
        # Create profile
        profile = {
            "statistics": statistics,
            "frame_count": len(keypoints_list),
            "fps": fps,
            "person_id": person_id
        }
        
        # Save template
        # Note: valid_skeletons is kept for backward compatibility with existing code
        # that expects this key. Both keys point to the same numpy array (no duplication).
        template_data = {
            "keypoints": keypoints_sequence,
            "profile": profile,
            "valid_skeletons": keypoints_sequence  # Backward compatibility
        }
        
        # Save as pickle
        template_file = output_path / f"person_{person_id}.pkl"
        with open(template_file, 'wb') as f:
            pickle.dump(template_data, f)
        
        print(f"   ✅ Saved template: {template_file}")
        
        # Save profile as JSON for easy inspection
        profile_file = output_path / f"person_{person_id}_profile.json"
        with open(profile_file, 'w') as f:
            json.dump(profile, f, indent=2)
        
        print(f"   ✅ Saved profile: {profile_file}")
    
    print(f"\n🎉 All templates created successfully!")
    print(f"   Output directory: {output_dir}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create multiple golden templates from multi-person video"
    )
    parser.add_argument(
        "video_path",
        help="Path to video file with multiple people"
    )
    parser.add_argument(
        "-o", "--output",
        default="data/multi_person_templates",
        help="Output directory for templates (default: data/multi_person_templates)"
    )
    
    args = parser.parse_args()
    
    # Validate video file
    if not Path(args.video_path).exists():
        print(f"❌ Error: Video file not found: {args.video_path}")
        sys.exit(1)
    
    # Create templates
    create_multi_golden_templates(args.video_path, args.output)


if __name__ == "__main__":
    main()
