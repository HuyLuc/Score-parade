#!/usr/bin/env python3
"""
Demo: Sequence-Based Error Detection
Shows how sequence comparison reduces over-penalization of persistent errors.
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from unittest.mock import Mock
from app.controllers.ai_controller import AIController


def create_frame_errors(num_frames, error_type="arm_angle", severity=2.0, deduction=0.5):
    """Create a list of frame errors simulating a persistent error"""
    errors = []
    for i in range(num_frames):
        errors.append({
            "type": error_type,
            "description": f"Tay trái quá cao ({severity}°)",
            "severity": severity,
            "deduction": deduction,
            "body_part": "arm",
            "side": "left",
            "frame_number": i,
            "timestamp": i * 0.033  # 30fps
        })
    return errors


def main():
    print("=" * 80)
    print("DEMO: Sequence-Based Error Detection")
    print("=" * 80)
    print()
    
    # Create mock AIController
    mock_pose_service = Mock()
    controller = AIController(mock_pose_service)
    
    # Scenario 1: Persistent error (600 frames)
    print("📊 Scenario 1: Persistent Small Error (600 frames)")
    print("-" * 80)
    print("Situation: User's arm is consistently 2° off target for 600 frames")
    print("Frame rate: 30 fps → 600 frames = 20 seconds")
    print()
    
    # Create 600 consecutive errors
    frame_errors = create_frame_errors(600, severity=2.0, deduction=0.5)
    
    print(f"❌ WITHOUT sequence comparison:")
    print(f"   • Total errors: {len(frame_errors)}")
    print(f"   • Total deduction: {len(frame_errors)} × 0.5 = {len(frame_errors) * 0.5} points")
    print(f"   • Starting score: 100 points")
    print(f"   • Final score: {100 - (len(frame_errors) * 0.5)} points")
    print(f"   • Result: UNFAIR! ❌")
    print()
    
    # Process with sequence comparison
    result = controller.process_video_sequence(frame_errors)
    
    print(f"✅ WITH sequence comparison:")
    print(f"   • Original errors: {result['original_error_count']}")
    print(f"   • Sequences detected: {result['sequence_count']}")
    print(f"   • Total deduction: {result['total_deduction']:.2f} points")
    print(f"   • Starting score: 100 points")
    print(f"   • Final score: {100 - result['total_deduction']:.2f} points")
    print(f"   • Improvement: {((len(frame_errors) * 0.5 - result['total_deduction']) / (len(frame_errors) * 0.5) * 100):.1f}% reduction in over-penalization")
    print(f"   • Result: FAIR! ✅")
    print()
    
    # Show sequence details
    if result['sequences']:
        seq = result['sequences'][0]
        print(f"📋 Sequence Details:")
        print(f"   • Type: {seq['type']}")
        print(f"   • Frames: {seq['start_frame']} - {seq['end_frame']} ({seq['frame_count']} frames)")
        print(f"   • Duration: {seq['frame_count'] / 30:.2f} seconds")
        print(f"   • Severity (aggregated): {seq['severity']:.2f}")
        print(f"   • Deduction: {seq['deduction']:.2f} points")
    print()
    print()
    
    # Scenario 2: Multiple error types
    print("📊 Scenario 2: Multiple Error Types")
    print("-" * 80)
    print("Situation: User has persistent arm AND leg errors")
    print()
    
    arm_errors = create_frame_errors(100, error_type="arm_angle", severity=2.0, deduction=0.5)
    leg_errors = create_frame_errors(100, error_type="leg_angle", severity=1.5, deduction=0.4)
    for err in leg_errors:
        err["body_part"] = "leg"
        err["side"] = "right"
        err["description"] = "Chân phải quá thấp"
    
    combined_errors = arm_errors + leg_errors
    
    print(f"❌ WITHOUT sequence comparison:")
    print(f"   • Total errors: {len(combined_errors)}")
    print(f"   • Total deduction: (100 × 0.5) + (100 × 0.4) = {(100 * 0.5) + (100 * 0.4)} points")
    print()
    
    result = controller.process_video_sequence(combined_errors)
    
    print(f"✅ WITH sequence comparison:")
    print(f"   • Original errors: {result['original_error_count']}")
    print(f"   • Sequences detected: {result['sequence_count']}")
    print(f"   • Total deduction: {result['total_deduction']:.2f} points")
    print(f"   • Improvement: {(((100 * 0.5) + (100 * 0.4) - result['total_deduction']) / ((100 * 0.5) + (100 * 0.4)) * 100):.1f}% reduction")
    print()
    
    for i, seq in enumerate(result['sequences'], 1):
        print(f"   Sequence {i}:")
        print(f"      • Type: {seq['type']} ({seq['side']})")
        print(f"      • Frames: {seq['frame_count']}")
        print(f"      • Deduction: {seq['deduction']:.2f} points")
    print()
    print()
    
    # Scenario 3: Isolated errors (should not be grouped)
    print("📊 Scenario 3: Isolated Errors")
    print("-" * 80)
    print("Situation: User makes only 2 brief mistakes (not persistent)")
    print()
    
    isolated_errors = create_frame_errors(2, severity=2.0, deduction=0.5)
    
    print(f"   • Total errors: {len(isolated_errors)}")
    
    result = controller.process_video_sequence(isolated_errors)
    
    print(f"   • Sequences detected: {result['sequence_count']}")
    print(f"   • Total deduction: {result['total_deduction']:.2f} points")
    print(f"   • Note: Isolated errors (< 3 consecutive frames) remain as individual errors")
    print()
    print()
    
    # Configuration info
    print("⚙️  Configuration")
    print("-" * 80)
    from app.config import SEQUENCE_COMPARISON_CONFIG
    print(f"   • Enabled: {SEQUENCE_COMPARISON_CONFIG['enabled']}")
    print(f"   • Min sequence length: {SEQUENCE_COMPARISON_CONFIG['min_sequence_length']} frames")
    print(f"   • Severity aggregation: {SEQUENCE_COMPARISON_CONFIG['severity_aggregation']}")
    print()
    
    print("=" * 80)
    print("✅ Demo Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
