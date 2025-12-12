"""
Demo script for sequence-based error detection

This script demonstrates how the sequence-based error detection reduces over-penalization
by grouping consecutive errors of the same type into sequences.

Problem:
    Without sequence grouping: 600 frames with 2° error → 600 errors → -300 points → Final score: -200
    
Solution:
    With sequence grouping: 600 frames → 1 sequence error → -2.6 points → Final score: 97.4

Usage:
    python demo_sequence_comparison.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.app.services.sequence_comparison import SequenceComparator
from backend.app.config import SEQUENCE_COMPARISON_CONFIG


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def demo_basic_usage():
    """Demonstrate basic usage of SequenceComparator"""
    print_header("1. Basic Usage: Grouping Consecutive Errors")
    
    # Create comparator
    comparator = SequenceComparator(
        min_sequence_length=3,
        severity_aggregation="mean",
        enabled=True
    )
    
    # Create 10 consecutive arm angle errors
    frame_errors = []
    for i in range(10):
        frame_errors.append({
            "type": "arm_angle",
            "body_part": "arm",
            "side": "left",
            "frame_number": i,
            "severity": 2.0,
            "deduction": 2.0,
            "description": f"Arm angle error at frame {i}"
        })
    
    print(f"\n📊 Input: {len(frame_errors)} consecutive frame errors")
    print(f"   Type: arm_angle (left)")
    print(f"   Frames: 0-9")
    print(f"   Deduction per frame: 2.0 points")
    
    # Group into sequences
    sequences = comparator.group_errors_into_sequences(frame_errors)
    
    print(f"\n✅ Output: {len(sequences)} sequence(s)")
    if sequences:
        seq = sequences[0]
        print(f"   Frames: {seq['start_frame']}-{seq['end_frame']} ({seq['sequence_length']} frames)")
        print(f"   Aggregated severity: {seq['severity']}")
        print(f"   Aggregated deduction: {seq['deduction']}")
        print(f"\n💡 Reduction: {len(frame_errors)} errors → {len(sequences)} sequence")
        print(f"   Penalty: -{len(frame_errors) * 2.0} → -{seq['deduction']} points")


def demo_multiple_sequences():
    """Demonstrate handling multiple sequences"""
    print_header("2. Multiple Sequences: Different Error Types")
    
    comparator = SequenceComparator(min_sequence_length=3)
    
    frame_errors = [
        # Sequence 1: arm_angle left (frames 0-4)
        *[{"type": "arm_angle", "body_part": "arm", "side": "left",
           "frame_number": i, "severity": 2.0, "deduction": 2.0}
          for i in range(5)],
        
        # Sequence 2: leg_angle right (frames 5-9)
        *[{"type": "leg_angle", "body_part": "leg", "side": "right",
           "frame_number": i, "severity": 1.5, "deduction": 1.5}
          for i in range(5, 10)],
    ]
    
    print(f"\n📊 Input: {len(frame_errors)} frame errors (2 different types)")
    print(f"   - arm_angle (left): frames 0-4")
    print(f"   - leg_angle (right): frames 5-9")
    
    sequences = comparator.group_errors_into_sequences(frame_errors)
    
    print(f"\n✅ Output: {len(sequences)} sequences")
    for i, seq in enumerate(sequences, 1):
        print(f"\n   Sequence {i}:")
        print(f"     Type: {seq['type']} ({seq.get('side', 'N/A')})")
        print(f"     Frames: {seq['start_frame']}-{seq['end_frame']}")
        print(f"     Deduction: {seq['deduction']}")


def demo_isolated_errors():
    """Demonstrate that isolated errors are not grouped"""
    print_header("3. Isolated Errors: Too Short to Form Sequence")
    
    comparator = SequenceComparator(min_sequence_length=3)
    
    frame_errors = [
        # Only 2 consecutive errors (< min 3)
        {"type": "arm_angle", "body_part": "arm", "side": "left",
         "frame_number": 0, "severity": 2.0, "deduction": 2.0},
        {"type": "arm_angle", "body_part": "arm", "side": "left",
         "frame_number": 1, "severity": 2.0, "deduction": 2.0},
    ]
    
    print(f"\n📊 Input: {len(frame_errors)} consecutive frame errors")
    print(f"   Type: arm_angle (left)")
    print(f"   Frames: 0-1")
    print(f"   Note: Only 2 frames (< min_sequence_length=3)")
    
    sequences = comparator.group_errors_into_sequences(frame_errors)
    
    print(f"\n✅ Output: {len(sequences)} individual errors (not grouped)")
    print(f"   Reason: Sequence too short (< {comparator.min_sequence_length} frames)")


def demo_main_use_case():
    """Demonstrate the main use case from requirements"""
    print_header("4. Main Use Case: 600 Consecutive Errors")
    
    comparator = SequenceComparator(
        min_sequence_length=SEQUENCE_COMPARISON_CONFIG["min_sequence_length"],
        severity_aggregation=SEQUENCE_COMPARISON_CONFIG["severity_aggregation"],
        enabled=SEQUENCE_COMPARISON_CONFIG["enabled"]
    )
    
    # Create 600 consecutive errors (the problem from requirements)
    frame_errors = []
    for i in range(600):
        frame_errors.append({
            "type": "arm_angle",
            "body_part": "arm",
            "side": "left",
            "frame_number": i,
            "severity": 0.5,  # Small error (2°)
            "deduction": 0.5
        })
    
    print(f"\n📊 Scenario: Person holds arm at 2° off throughout entire video")
    print(f"   - Video: 600 frames (20 seconds @ 30fps)")
    print(f"   - Error: 2° angle deviation")
    print(f"   - Severity per frame: 0.5")
    print(f"   - Deduction per frame: 0.5 points")
    
    # Calculate without sequence grouping
    without_sequence_score = 100.0 - (600 * 0.5)
    print(f"\n❌ Without sequence grouping:")
    print(f"   - Total errors: 600")
    print(f"   - Total deduction: -{600 * 0.5} points")
    print(f"   - Final score: {without_sequence_score} (UNFAIR!)")
    
    # Calculate with sequence grouping
    final_score, sequences = comparator.calculate_sequence_score(
        frame_errors=frame_errors,
        initial_score=100.0
    )
    
    print(f"\n✅ With sequence grouping:")
    print(f"   - Sequences: {len(sequences)}")
    if sequences:
        seq = sequences[0]
        print(f"   - Sequence length: {seq['sequence_length']} frames")
        print(f"   - Aggregated deduction: -{seq['deduction']} points")
    print(f"   - Final score: {final_score:.2f}")
    
    improvement = final_score - without_sequence_score
    reduction_percentage = (improvement / abs(without_sequence_score)) * 100
    
    print(f"\n🎯 Results:")
    print(f"   - Improvement: +{improvement:.2f} points")
    print(f"   - Penalty reduction: {reduction_percentage:.1f}%")
    print(f"   - This is now FAIR scoring! ✅")


def demo_aggregation_methods():
    """Demonstrate different severity aggregation methods"""
    print_header("5. Severity Aggregation Methods")
    
    # Create errors with varying severities
    frame_errors = [
        {"type": "arm_angle", "body_part": "arm", "side": "left",
         "frame_number": i, "severity": severity, "deduction": severity}
        for i, severity in enumerate([1.0, 2.0, 3.0, 2.0, 1.0])
    ]
    
    print(f"\n📊 Input: 5 consecutive errors with varying severities")
    print(f"   Severities: [1.0, 2.0, 3.0, 2.0, 1.0]")
    
    for method in ["mean", "max", "median"]:
        comparator = SequenceComparator(
            min_sequence_length=3,
            severity_aggregation=method
        )
        
        sequences = comparator.group_errors_into_sequences(frame_errors)
        
        if sequences:
            print(f"\n   {method.upper()}: severity = {sequences[0]['severity']}")


def main():
    """Run all demos"""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "SEQUENCE-BASED ERROR DETECTION DEMO" + " " * 18 + "║")
    print("╚" + "═" * 68 + "╝")
    
    print("\nThis demo shows how sequence-based error detection reduces")
    print("over-penalization by grouping consecutive errors into sequences.")
    
    try:
        demo_basic_usage()
        demo_multiple_sequences()
        demo_isolated_errors()
        demo_main_use_case()
        demo_aggregation_methods()
        
        print("\n" + "=" * 70)
        print("  ✅ Demo completed successfully!")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  1. Consecutive errors are grouped into sequences")
        print("  2. Sequences must be ≥ min_sequence_length (default: 3 frames)")
        print("  3. Severity is aggregated (mean/max/median)")
        print("  4. Reduces over-penalization by 99% for persistent errors")
        print("  5. Isolated errors remain as individual penalties")
        print("\nConfiguration:")
        print(f"  SEQUENCE_COMPARISON_CONFIG = {{")
        print(f"    'enabled': {SEQUENCE_COMPARISON_CONFIG['enabled']},")
        print(f"    'min_sequence_length': {SEQUENCE_COMPARISON_CONFIG['min_sequence_length']},")
        print(f"    'severity_aggregation': '{SEQUENCE_COMPARISON_CONFIG['severity_aggregation']}'")
        print(f"  }}")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
