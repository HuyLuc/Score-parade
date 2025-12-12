"""
Sequence comparison service - Group consecutive errors into sequences
to avoid over-penalizing persistent errors.
"""
from typing import List, Dict, Optional
import numpy as np


class SequenceComparator:
    """
    Groups consecutive frame errors into sequences and calculates
    a single error per sequence instead of per frame.
    """
    
    def __init__(self, min_sequence_length: int = 3, severity_aggregation: str = "mean"):
        """
        Initialize SequenceComparator
        
        Args:
            min_sequence_length: Minimum consecutive frames to form a sequence
            severity_aggregation: Method to aggregate severity ("mean", "max", "median")
        """
        self.min_sequence_length = min_sequence_length
        self.severity_aggregation = severity_aggregation
    
    def group_errors_into_sequences(self, frame_errors: List[Dict]) -> List[Dict]:
        """
        Group consecutive frame errors by error type into sequences.
        
        Args:
            frame_errors: List of error dicts from all frames, each containing:
                {
                    "type": str,
                    "description": str,
                    "severity": float,
                    "deduction": float,
                    "body_part": str,
                    "side": Optional[str],
                    "frame_number": int,
                    "timestamp": float
                }
        
        Returns:
            List of sequence dicts:
                {
                    "type": str,
                    "description": str,
                    "severity": float,
                    "deduction": float,
                    "body_part": str,
                    "side": Optional[str],
                    "start_frame": int,
                    "end_frame": int,
                    "frame_count": int,
                    "start_timestamp": float,
                    "end_timestamp": float
                }
        """
        if not frame_errors:
            return []
        
        # Sort errors by frame_number to ensure consecutive ordering
        sorted_errors = sorted(frame_errors, key=lambda e: e.get("frame_number", 0))
        
        # Group by error signature (type + body_part + side)
        error_groups = {}
        for error in sorted_errors:
            signature = self._get_error_signature(error)
            if signature not in error_groups:
                error_groups[signature] = []
            error_groups[signature].append(error)
        
        # Process each error group to find sequences
        sequences = []
        for signature, errors in error_groups.items():
            group_sequences = self._find_sequences_in_group(errors)
            sequences.extend(group_sequences)
        
        return sequences
    
    def _get_error_signature(self, error: Dict) -> str:
        """
        Create a unique signature for an error based on type, body_part, and side.
        Errors with the same signature are candidates for grouping.
        """
        error_type = error.get("type", "unknown")
        body_part = error.get("body_part", "unknown")
        side = error.get("side", "")
        return f"{error_type}_{body_part}_{side}"
    
    def _find_sequences_in_group(self, errors: List[Dict]) -> List[Dict]:
        """
        Find consecutive sequences within a group of same-type errors.
        
        Args:
            errors: List of errors with same signature, sorted by frame_number
        
        Returns:
            List of sequence dicts
        """
        if not errors:
            return []
        
        sequences = []
        current_sequence = [errors[0]]
        
        for i in range(1, len(errors)):
            current_frame = errors[i].get("frame_number", 0)
            prev_frame = errors[i-1].get("frame_number", 0)
            
            # Check if frames are consecutive
            if current_frame == prev_frame + 1:
                current_sequence.append(errors[i])
            else:
                # Sequence break - finalize current sequence if it meets length requirement
                if len(current_sequence) >= self.min_sequence_length:
                    sequences.append(self._create_sequence_from_errors(current_sequence))
                elif len(current_sequence) > 0:
                    # Isolated errors (not part of sequence) are kept as individual errors
                    for error in current_sequence:
                        sequences.append(self._create_single_error_sequence(error))
                
                # Start new sequence
                current_sequence = [errors[i]]
        
        # Handle the last sequence
        if len(current_sequence) >= self.min_sequence_length:
            sequences.append(self._create_sequence_from_errors(current_sequence))
        elif len(current_sequence) > 0:
            # Isolated errors at the end
            for error in current_sequence:
                sequences.append(self._create_single_error_sequence(error))
        
        return sequences
    
    def _create_sequence_from_errors(self, errors: List[Dict]) -> Dict:
        """
        Create a single sequence dict from a list of consecutive errors.
        Aggregates severity using the configured method.
        """
        if not errors:
            return {}
        
        # Extract base error info from first error
        first_error = errors[0]
        
        # Calculate aggregated severity and deduction
        aggregated_severity = self.calculate_sequence_error(errors)
        
        # Use the same weight from the first error
        weight = first_error.get("deduction", 0) / first_error.get("severity", 1) if first_error.get("severity", 0) > 0 else 1.0
        aggregated_deduction = weight * aggregated_severity
        
        sequence = {
            "type": first_error.get("type"),
            "description": first_error.get("description"),
            "severity": aggregated_severity,
            "deduction": aggregated_deduction,
            "body_part": first_error.get("body_part"),
            "start_frame": errors[0].get("frame_number", 0),
            "end_frame": errors[-1].get("frame_number", 0),
            "frame_count": len(errors),
            "start_timestamp": errors[0].get("timestamp", 0.0),
            "end_timestamp": errors[-1].get("timestamp", 0.0),
            "is_sequence": True
        }
        
        # Add side if present
        if "side" in first_error:
            sequence["side"] = first_error["side"]
        
        return sequence
    
    def _create_single_error_sequence(self, error: Dict) -> Dict:
        """
        Convert a single error into a sequence format (for isolated errors).
        """
        sequence = {
            "type": error.get("type"),
            "description": error.get("description"),
            "severity": error.get("severity"),
            "deduction": error.get("deduction"),
            "body_part": error.get("body_part"),
            "start_frame": error.get("frame_number", 0),
            "end_frame": error.get("frame_number", 0),
            "frame_count": 1,
            "start_timestamp": error.get("timestamp", 0.0),
            "end_timestamp": error.get("timestamp", 0.0),
            "is_sequence": False
        }
        
        # Add side if present
        if "side" in error:
            sequence["side"] = error["side"]
        
        return sequence
    
    def calculate_sequence_error(self, errors: List[Dict]) -> float:
        """
        Calculate a single severity value for an entire sequence of errors.
        
        Args:
            errors: List of errors in the sequence
        
        Returns:
            Aggregated severity value
        """
        if not errors:
            return 0.0
        
        severities = [e.get("severity", 0.0) for e in errors]
        
        if self.severity_aggregation == "mean":
            return np.mean(severities)
        elif self.severity_aggregation == "max":
            return np.max(severities)
        elif self.severity_aggregation == "median":
            return np.median(severities)
        else:
            # Default to mean
            return np.mean(severities)
