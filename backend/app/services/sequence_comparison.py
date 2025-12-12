"""
Sequence Comparison Service - Groups consecutive errors into sequences to avoid over-penalization

This service addresses the problem where each frame is penalized independently:
- Before: 600 frames with 2° error → 600 errors → -300 points → Final score: -200
- After: 600 frames → 1 sequence error → -2.6 points → Final score: 97.4

The key idea is to group consecutive errors of the same type/body_part/side into sequences
and apply penalty once per sequence rather than per frame.
"""

import logging
from typing import List, Dict, Optional, Tuple
from statistics import mean, median
import numpy as np

logger = logging.getLogger(__name__)


class SequenceComparator:
    """
    Compares video sequences and groups consecutive errors to avoid over-penalization
    """
    
    def __init__(
        self,
        min_sequence_length: int = 3,
        severity_aggregation: str = "mean",
        enabled: bool = True
    ):
        """
        Initialize SequenceComparator
        
        Args:
            min_sequence_length: Minimum number of consecutive frames to form a sequence (default: 3)
            severity_aggregation: How to aggregate severity across sequence ("mean", "max", "median")
            enabled: Whether sequence comparison is enabled
        """
        self.min_sequence_length = min_sequence_length
        self.severity_aggregation = severity_aggregation
        self.enabled = enabled
        
        logger.info(
            f"SequenceComparator initialized: "
            f"min_sequence_length={min_sequence_length}, "
            f"severity_aggregation={severity_aggregation}, "
            f"enabled={enabled}"
        )
    
    def group_errors_into_sequences(
        self,
        frame_errors: List[Dict]
    ) -> List[Dict]:
        """
        Group consecutive frame errors into sequences by error type, body part, and side
        
        This is the main method that transforms frame-by-frame errors into sequence errors.
        
        Args:
            frame_errors: List of error dicts, each containing:
                {
                    "type": "arm_angle",
                    "body_part": "arm",
                    "side": "left",
                    "severity": 2.0,
                    "deduction": 2.0,
                    "frame_number": 10,
                    "description": "...",
                    ...
                }
        
        Returns:
            List of sequence error dicts:
                {
                    "type": "arm_angle",
                    "body_part": "arm",
                    "side": "left",
                    "start_frame": 10,
                    "end_frame": 50,
                    "sequence_length": 41,
                    "severity": 1.8,  # aggregated
                    "deduction": 1.8,  # aggregated
                    "description": "Arm angle error (left) from frame 10-50",
                    "is_sequence": True
                }
        """
        if not self.enabled or not frame_errors:
            return frame_errors
        
        # Sort errors by frame number to ensure consecutive grouping
        sorted_errors = sorted(frame_errors, key=lambda e: e.get("frame_number", 0))
        
        sequences = []
        current_sequence = []
        
        for error in sorted_errors:
            # Create a key to identify error type (type + body_part + side)
            error_key = self._get_error_key(error)
            frame_num = error.get("frame_number", 0)
            
            if not current_sequence:
                # Start new sequence
                current_sequence = [error]
            else:
                # Check if this error continues the current sequence
                last_error = current_sequence[-1]
                last_key = self._get_error_key(last_error)
                last_frame = last_error.get("frame_number", 0)
                
                # Sequence continues if: same error type AND consecutive frames
                if error_key == last_key and frame_num == last_frame + 1:
                    current_sequence.append(error)
                else:
                    # Sequence breaks - process current sequence and start new one
                    sequences.extend(self._process_sequence(current_sequence))
                    current_sequence = [error]
        
        # Process last sequence
        if current_sequence:
            sequences.extend(self._process_sequence(current_sequence))
        
        logger.info(
            f"Grouped {len(frame_errors)} frame errors into {len(sequences)} sequences "
            f"(reduction: {len(frame_errors) - len(sequences)})"
        )
        
        return sequences
    
    def _get_error_key(self, error: Dict) -> Tuple:
        """
        Create a unique key for an error based on type, body_part, and side
        
        Args:
            error: Error dict
        
        Returns:
            Tuple of (type, body_part, side) that uniquely identifies error category
        """
        return (
            error.get("type", "unknown"),
            error.get("body_part", "unknown"),
            error.get("side", None)  # None for errors without side (e.g., head_angle)
        )
    
    def _process_sequence(self, sequence: List[Dict]) -> List[Dict]:
        """
        Process a sequence of consecutive errors
        
        If sequence length >= min_sequence_length, aggregate into single sequence error.
        Otherwise, return individual frame errors (too short to be a sequence).
        
        Args:
            sequence: List of consecutive error dicts with same type/body_part/side
        
        Returns:
            List containing either:
                - Single aggregated sequence error (if len >= min_sequence_length)
                - Original individual errors (if len < min_sequence_length)
        """
        if not sequence:
            return []
        
        sequence_length = len(sequence)
        
        # Too short to be a sequence - return individual errors
        if sequence_length < self.min_sequence_length:
            return sequence
        
        # Aggregate into sequence error
        aggregated_error = self._aggregate_sequence(sequence)
        return [aggregated_error]
    
    def _aggregate_sequence(self, sequence: List[Dict]) -> Dict:
        """
        Aggregate a sequence of errors into a single sequence error
        
        Args:
            sequence: List of consecutive error dicts with same type/body_part/side
        
        Returns:
            Aggregated sequence error dict
        """
        if not sequence:
            return {}
        
        first_error = sequence[0]
        last_error = sequence[-1]
        
        # Extract severities and deductions
        severities = [e.get("severity", 0.0) for e in sequence]
        deductions = [e.get("deduction", 0.0) for e in sequence]
        
        # Aggregate based on configured method
        if self.severity_aggregation == "mean":
            agg_severity = mean(severities)
            agg_deduction = mean(deductions)
        elif self.severity_aggregation == "max":
            agg_severity = max(severities)
            agg_deduction = max(deductions)
        elif self.severity_aggregation == "median":
            agg_severity = median(severities)
            agg_deduction = median(deductions)
        else:
            logger.warning(f"Unknown aggregation method: {self.severity_aggregation}, using mean")
            agg_severity = mean(severities)
            agg_deduction = mean(deductions)
        
        # Build aggregated error
        start_frame = first_error.get("frame_number", 0)
        end_frame = last_error.get("frame_number", 0)
        sequence_length = len(sequence)
        
        error_type = first_error.get("type", "unknown")
        body_part = first_error.get("body_part", "unknown")
        side = first_error.get("side")
        
        # Build description
        side_str = f" ({side})" if side else ""
        description = (
            f"{error_type.replace('_', ' ').title()}{side_str} "
            f"from frame {start_frame}-{end_frame} ({sequence_length} frames)"
        )
        
        aggregated_error = {
            "type": error_type,
            "body_part": body_part,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "sequence_length": sequence_length,
            "severity": round(agg_severity, 2),
            "deduction": round(agg_deduction, 2),
            "description": description,
            "is_sequence": True
        }
        
        # Add side if present
        if side:
            aggregated_error["side"] = side
        
        return aggregated_error
    
    def calculate_sequence_score(
        self,
        frame_errors: List[Dict],
        initial_score: float = 100.0
    ) -> Tuple[float, List[Dict]]:
        """
        Calculate score with sequence-based error grouping
        
        This is the main entry point for scoring with sequence comparison.
        
        Args:
            frame_errors: List of frame-by-frame errors
            initial_score: Starting score (default: 100.0)
        
        Returns:
            Tuple of (final_score, sequence_errors):
                - final_score: Score after applying sequence penalties
                - sequence_errors: List of sequence error dicts
        """
        # Group errors into sequences
        sequence_errors = self.group_errors_into_sequences(frame_errors)
        
        # Calculate total deduction
        total_deduction = sum(e.get("deduction", 0.0) for e in sequence_errors)
        
        # Calculate final score
        final_score = initial_score - total_deduction
        
        logger.info(
            f"Sequence scoring: {len(frame_errors)} frame errors → "
            f"{len(sequence_errors)} sequences, "
            f"deduction: {total_deduction:.2f}, "
            f"final score: {final_score:.2f}"
        )
        
        return final_score, sequence_errors
