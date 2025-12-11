"""
Demo script to visualize temporal smoothing effects on pose estimation

This script demonstrates how temporal smoothing reduces noise in angle
measurements from pose estimation keypoints.
"""
import numpy as np
import matplotlib.pyplot as plt
from backend.app.services.temporal_smoothing import TemporalSmoother


def generate_noisy_signal(num_frames=100, base_angle=45.0, noise_level=10.0, spikes=[30, 60]):
    """
    Generate a synthetic angle measurement signal with noise and spikes
    
    Args:
        num_frames: Number of frames to generate
        base_angle: Base angle value
        noise_level: Standard deviation of Gaussian noise
        spikes: Frame indices where large spikes occur
        
    Returns:
        Array of noisy angle measurements
    """
    np.random.seed(42)
    
    # Generate base signal with Gaussian noise
    signal = base_angle + np.random.normal(0, noise_level, num_frames)
    
    # Add spikes (simulating temporary occlusions or detection errors)
    for spike_frame in spikes:
        if spike_frame < num_frames:
            signal[spike_frame] += 30.0  # Large positive spike
    
    return signal


def apply_smoothing(signal, window_size=5, method="moving_average"):
    """
    Apply temporal smoothing to a signal
    
    Args:
        signal: Input signal array
        window_size: Smoothing window size
        method: "moving_average" or "median"
        
    Returns:
        Smoothed signal array
    """
    smoother = TemporalSmoother(window_size=window_size, method=method)
    smoothed = []
    
    for value in signal:
        smoother.add_value(value)
        smoothed_value = smoother.get_smoothed_value()
        if smoothed_value is not None:
            smoothed.append(smoothed_value)
        else:
            # Before window is full, use original value
            smoothed.append(value)
    
    return np.array(smoothed)


def calculate_error_detections(signal, threshold=15.0, golden_mean=45.0):
    """
    Count how many frames would trigger an error based on threshold
    
    Args:
        signal: Signal to check
        threshold: Error threshold
        golden_mean: Expected value
        
    Returns:
        Number of error detections
    """
    errors = np.abs(signal - golden_mean) > threshold
    return np.sum(errors)


def visualize_smoothing():
    """Create visualization comparing original vs smoothed signals"""
    print("🎯 Temporal Smoothing Demo\n")
    print("=" * 60)
    
    # Generate noisy signal
    num_frames = 100
    base_angle = 45.0
    noise_level = 10.0
    spikes = [30, 60]
    
    print(f"Generating signal:")
    print(f"  - {num_frames} frames")
    print(f"  - Base angle: {base_angle}°")
    print(f"  - Noise level: ±{noise_level}°")
    print(f"  - Spikes at frames: {spikes}")
    print()
    
    original_signal = generate_noisy_signal(num_frames, base_angle, noise_level, spikes)
    
    # Apply different smoothing methods
    smoothed_ma = apply_smoothing(original_signal, window_size=5, method="moving_average")
    smoothed_median = apply_smoothing(original_signal, window_size=5, method="median")
    
    # Calculate statistics
    threshold = 15.0
    original_errors = calculate_error_detections(original_signal, threshold, base_angle)
    ma_errors = calculate_error_detections(smoothed_ma, threshold, base_angle)
    median_errors = calculate_error_detections(smoothed_median, threshold, base_angle)
    
    original_variance = np.var(original_signal)
    ma_variance = np.var(smoothed_ma)
    median_variance = np.var(smoothed_median)
    
    print("📊 Results:")
    print("-" * 60)
    print(f"{'Method':<20} {'Errors':>10} {'Variance':>15} {'Reduction':>15}")
    print("-" * 60)
    print(f"{'Original':<20} {original_errors:>10} {original_variance:>15.2f} {'—':>15}")
    print(f"{'Moving Average':<20} {ma_errors:>10} {ma_variance:>15.2f} {f'{(1-ma_errors/original_errors)*100:.1f}%':>15}")
    print(f"{'Median Filter':<20} {median_errors:>10} {median_variance:>15.2f} {f'{(1-median_errors/original_errors)*100:.1f}%':>15}")
    print("-" * 60)
    print()
    
    print("✅ Benefits:")
    print(f"  - False positives reduced by: {(1-ma_errors/original_errors)*100:.1f}%")
    print(f"  - Variance reduced by: {(1-ma_variance/original_variance)*100:.1f}%")
    print(f"  - Latency added: 167ms (5 frames @ 30fps)")
    print()
    
    # Create visualization
    try:
        plt.figure(figsize=(14, 8))
        
        # Plot signals
        plt.subplot(2, 1, 1)
        frames = np.arange(num_frames)
        plt.plot(frames, original_signal, 'o-', alpha=0.5, label='Original (noisy)', markersize=3)
        plt.plot(frames, smoothed_ma, 's-', alpha=0.7, label='Moving Average', markersize=3)
        plt.plot(frames, smoothed_median, '^-', alpha=0.7, label='Median Filter', markersize=3)
        plt.axhline(y=base_angle, color='g', linestyle='--', alpha=0.5, label='Target')
        plt.axhline(y=base_angle+threshold, color='r', linestyle=':', alpha=0.3, label='Error Threshold')
        plt.axhline(y=base_angle-threshold, color='r', linestyle=':', alpha=0.3)
        
        plt.xlabel('Frame')
        plt.ylabel('Angle (degrees)')
        plt.title('Temporal Smoothing Effect on Pose Angle Measurements')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Plot error detections
        plt.subplot(2, 1, 2)
        original_errors_mask = np.abs(original_signal - base_angle) > threshold
        ma_errors_mask = np.abs(smoothed_ma - base_angle) > threshold
        median_errors_mask = np.abs(smoothed_median - base_angle) > threshold
        
        plt.plot(frames, original_errors_mask.astype(int), 'o-', alpha=0.5, label='Original Errors', markersize=3)
        plt.plot(frames, ma_errors_mask.astype(int), 's-', alpha=0.7, label='MA Errors', markersize=3)
        plt.plot(frames, median_errors_mask.astype(int), '^-', alpha=0.7, label='Median Errors', markersize=3)
        
        plt.xlabel('Frame')
        plt.ylabel('Error Detected (1=Yes, 0=No)')
        plt.title('Error Detection: Original vs Smoothed')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylim(-0.1, 1.1)
        
        plt.tight_layout()
        
        # Save figure
        output_path = '/tmp/temporal_smoothing_demo.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"📈 Visualization saved to: {output_path}")
        
    except Exception as e:
        print(f"⚠️  Could not create visualization: {e}")
        print("   (This is optional - the demo results above are still valid)")


if __name__ == "__main__":
    visualize_smoothing()
