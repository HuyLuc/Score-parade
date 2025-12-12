"""
Visualization utilities for multi-person tracking and evaluation
"""
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple


# Color palette for different persons (BGR format)
PERSON_COLORS = [
    (255, 0, 0),      # Blue
    (0, 255, 0),      # Green
    (0, 0, 255),      # Red
    (255, 255, 0),    # Cyan
    (255, 0, 255),    # Magenta
    (0, 255, 255),    # Yellow
    (128, 0, 255),    # Purple
    (255, 128, 0),    # Orange
    (0, 128, 255),    # Sky blue
    (255, 0, 128),    # Pink
]


def draw_multi_person_tracking(
    frame: np.ndarray,
    tracked_persons: Dict[int, np.ndarray],
    matches: Dict[int, str],
    errors: Dict[int, List[Dict]]
) -> np.ndarray:
    """
    Draw tracking visualization with colored bounding boxes, IDs, and error counts
    
    Args:
        frame: Input frame (BGR)
        tracked_persons: Dict mapping person_id to keypoints [17, 3]
        matches: Dict mapping person_id to template_id
        errors: Dict mapping person_id to list of errors
        
    Returns:
        Annotated frame
    """
    annotated = frame.copy()
    
    for person_id, keypoints in tracked_persons.items():
        # Get color for this person
        color = PERSON_COLORS[person_id % len(PERSON_COLORS)]
        
        # Draw skeleton
        annotated = draw_skeleton(annotated, keypoints, color, thickness=2)
        
        # Get bounding box
        valid_mask = keypoints[:, 2] > 0
        if np.any(valid_mask):
            valid_points = keypoints[valid_mask, :2]
            x1, y1 = valid_points.min(axis=0).astype(int)
            x2, y2 = valid_points.max(axis=0).astype(int)
            
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Prepare text
            template_id = matches.get(person_id, "N/A")
            error_count = len(errors.get(person_id, []))
            
            # Draw person ID and template
            text = f"ID:{person_id} | {template_id}"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            
            # Background rectangle for text
            cv2.rectangle(annotated, (x1, y1 - text_size[1] - 10), 
                         (x1 + text_size[0] + 5, y1), color, -1)
            
            # Text
            cv2.putText(annotated, text, (x1 + 2, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # Draw error count
            error_text = f"Errors: {error_count}"
            cv2.putText(annotated, error_text, (x1, y2 + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return annotated


def draw_skeleton(frame: np.ndarray, keypoints: np.ndarray, color: Tuple[int, int, int], 
                  thickness: int = 2) -> np.ndarray:
    """
    Draw skeleton on frame
    
    Args:
        frame: Input frame
        keypoints: Keypoints array [17, 3]
        color: Color for skeleton (BGR)
        thickness: Line thickness
        
    Returns:
        Frame with skeleton drawn
    """
    # COCO skeleton connections
    skeleton = [
        (0, 1), (0, 2), (1, 3), (2, 4),  # Head
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
        (5, 11), (6, 12), (11, 12),  # Torso
        (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
    ]
    
    annotated = frame.copy()
    
    # Draw connections
    for pt1_idx, pt2_idx in skeleton:
        if keypoints[pt1_idx, 2] > 0 and keypoints[pt2_idx, 2] > 0:
            pt1 = tuple(keypoints[pt1_idx, :2].astype(int))
            pt2 = tuple(keypoints[pt2_idx, :2].astype(int))
            cv2.line(annotated, pt1, pt2, color, thickness)
    
    # Draw keypoints
    for i, kp in enumerate(keypoints):
        if kp[2] > 0:
            center = tuple(kp[:2].astype(int))
            cv2.circle(annotated, center, 3, color, -1)
    
    return annotated


def draw_person_trajectories(
    frame: np.ndarray,
    person_trajectories: Dict[int, List[Tuple[int, int]]]
) -> np.ndarray:
    """
    Draw movement trajectories for each person
    
    Args:
        frame: Input frame
        person_trajectories: Dict mapping person_id to list of (x, y) positions
        
    Returns:
        Frame with trajectories drawn
    """
    annotated = frame.copy()
    
    for person_id, trajectory in person_trajectories.items():
        if len(trajectory) < 2:
            continue
        
        color = PERSON_COLORS[person_id % len(PERSON_COLORS)]
        
        # Draw trajectory line
        points = np.array(trajectory, dtype=np.int32)
        cv2.polylines(annotated, [points], isClosed=False, color=color, thickness=2)
        
        # Draw start and end points
        cv2.circle(annotated, tuple(trajectory[0]), 5, color, -1)
        cv2.circle(annotated, tuple(trajectory[-1]), 7, (0, 255, 0), -1)
    
    return annotated


def create_multi_person_summary(results: Dict[int, Dict]) -> np.ndarray:
    """
    Create summary visualization comparing all persons
    
    Args:
        results: Dict mapping person_id to evaluation results
            {
                person_id: {
                    "score": float,
                    "errors": List[Dict],
                    "matched_template": str,
                    "frame_count": int
                }
            }
            
    Returns:
        Summary image (BGR)
    """
    # Create blank image
    height = 100 + len(results) * 80
    width = 800
    summary = np.ones((height, width, 3), dtype=np.uint8) * 255
    
    # Title
    cv2.putText(summary, "Multi-Person Evaluation Summary", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    
    # Draw line
    cv2.line(summary, (20, 60), (width - 20, 60), (0, 0, 0), 2)
    
    # Draw results for each person
    y_offset = 100
    for person_id, result in sorted(results.items()):
        color = PERSON_COLORS[person_id % len(PERSON_COLORS)]
        
        # Person info
        text = f"Person {person_id}"
        cv2.putText(summary, text, (30, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Template
        template = result.get("matched_template", "N/A")
        cv2.putText(summary, f"Template: {template}", (200, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Score
        score = result.get("score", 0.0)
        score_color = (0, 255, 0) if score >= 80 else (0, 165, 255) if score >= 60 else (0, 0, 255)
        cv2.putText(summary, f"Score: {score:.1f}", (400, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, score_color, 2)
        
        # Error count
        error_count = len(result.get("errors", []))
        cv2.putText(summary, f"Errors: {error_count}", (580, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Frame count
        frame_count = result.get("frame_count", 0)
        cv2.putText(summary, f"Frames: {frame_count}", (700, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Draw score bar
        bar_width = int(score * 3)
        cv2.rectangle(summary, (30, y_offset + 15), 
                     (30 + bar_width, y_offset + 35), score_color, -1)
        cv2.rectangle(summary, (30, y_offset + 15), 
                     (330, y_offset + 35), (200, 200, 200), 2)
        
        y_offset += 80
    
    return summary


def create_side_by_side_comparison(
    test_frame: np.ndarray,
    golden_frame: np.ndarray,
    person_id: int,
    template_id: str,
    score: float
) -> np.ndarray:
    """
    Create side-by-side comparison of test and golden frames
    
    Args:
        test_frame: Test video frame with person highlighted
        golden_frame: Golden template frame
        person_id: Person ID
        template_id: Template ID
        score: Evaluation score
        
    Returns:
        Side-by-side comparison image
    """
    # Resize frames to same height
    h1, w1 = test_frame.shape[:2]
    h2, w2 = golden_frame.shape[:2]
    target_height = min(h1, h2, 480)
    
    test_resized = cv2.resize(test_frame, (int(w1 * target_height / h1), target_height))
    golden_resized = cv2.resize(golden_frame, (int(w2 * target_height / h2), target_height))
    
    # Create combined image
    combined_width = test_resized.shape[1] + golden_resized.shape[1] + 20
    combined = np.ones((target_height + 100, combined_width, 3), dtype=np.uint8) * 255
    
    # Place frames
    combined[50:50 + target_height, 10:10 + test_resized.shape[1]] = test_resized
    combined[50:50 + target_height, 20 + test_resized.shape[1]:] = golden_resized
    
    # Add labels
    cv2.putText(combined, f"Test - Person {person_id}", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(combined, f"Golden - {template_id}", (30 + test_resized.shape[1], 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # Add score
    score_color = (0, 255, 0) if score >= 80 else (0, 165, 255) if score >= 60 else (0, 0, 255)
    cv2.putText(combined, f"Score: {score:.1f}", (combined_width // 2 - 50, target_height + 80),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, score_color, 2)
    
    return combined
