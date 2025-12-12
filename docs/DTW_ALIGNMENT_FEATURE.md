# DTW Alignment Feature - Tempo Variation Handling

## 📋 Tổng quan (Overview)

Dynamic Time Warping (DTW) là một kỹ thuật căn chỉnh chuỗi thời gian (time series alignment) được tích hợp vào hệ thống để xử lý vấn đề **tempo variation** - khi video test được thực hiện với tốc độ khác so với golden template.

**Dynamic Time Warping (DTW)** is a time series alignment technique integrated into the system to handle **tempo variation** - when test videos are performed at different speeds compared to the golden template.

## 🎯 Vấn đề (Problem)

### Trước khi có DTW (Before DTW)

Hệ thống giả định test video và golden video có cùng tốc độ:
- **Test nhanh hơn 10%** → Tất cả frames bị phạt là "sớm" (early) → ~450 lỗi → Điểm: 0 ❌
- **Test chậm hơn 10%** → Tất cả frames bị phạt là "muộn" (late) → ~450 lỗi → Điểm: 0 ❌

The system assumes test and golden videos have the same speed:
- **Test 10% faster** → All frames penalized as "early" → ~450 errors → Score: 0 ❌
- **Test 10% slower** → All frames penalized as "late" → ~450 errors → Score: 0 ❌

### Sau khi có DTW (After DTW)

DTW căn chỉnh chuỗi frames trước khi so sánh:
- **Test nhanh hơn 10%** → DTW căn chỉnh → Chỉ phát hiện lỗi thực sự → Điểm: 75+ ✅
- **Test chậm hơn 10%** → DTW căn chỉnh → Chỉ phát hiện lỗi thực sự → Điểm: 75+ ✅

DTW aligns frame sequences before comparison:
- **Test 10% faster** → DTW aligns → Only real errors detected → Score: 75+ ✅
- **Test 10% slower** → DTW aligns → Only real errors detected → Score: 75+ ✅

## 🔧 Cài đặt (Installation)

### 1. Dependencies

DTW feature requires `fastdtw` library:

```bash
pip install fastdtw>=0.3.4
```

Or install all requirements:

```bash
pip install -r backend/requirements.txt
```

### 2. Configuration

Edit `backend/app/config.py`:

```python
DTW_CONFIG = {
    "enabled": True,  # Set to True to enable DTW
    "window_size": 50,  # Window size for DTW alignment
    "distance_metric": "euclidean",  # "euclidean", "manhattan", or "cosine"
}
```

**⚠️ Lưu ý (Note):** DTW is **disabled by default** (`enabled: False`) to avoid affecting existing system behavior. Enable it explicitly when needed.

## 💻 Sử dụng (Usage)

### Option 1: Using AIController

```python
from backend.app.services.pose_service import PoseService
from backend.app.controllers.ai_controller import AIController
from backend.app.config import DTW_CONFIG

# Enable DTW
DTW_CONFIG["enabled"] = True

# Initialize controller
pose_service = PoseService()
ai_controller = AIController(pose_service)

# Load golden template
ai_controller.load_golden_template()

# Process video with DTW
test_keypoints_sequence = [...]  # List of keypoints arrays from test video
errors, alignment_info = ai_controller.process_video_with_dtw(test_keypoints_sequence)

# Check alignment info
print(f"Tempo ratio: {alignment_info['tempo_ratio']:.2f}x")
print(f"DTW distance: {alignment_info['dtw_distance']:.2f}")
```

### Option 2: Using DTWAligner Directly

```python
from backend.app.services.dtw_alignment import DTWAligner

# Create aligner
aligner = DTWAligner(window_size=50, distance_metric="euclidean")

# Align sequences
test_sequence = [...]  # List of keypoints arrays [17, 3]
golden_sequence = [...]  # List of keypoints arrays [17, 3]

distance, path = aligner.align_sequences(test_sequence, golden_sequence)

# Get aligned frame mapping
for test_idx in range(len(test_sequence)):
    golden_idx = aligner.get_aligned_frame(test_idx)
    print(f"Test frame {test_idx} → Golden frame {golden_idx}")

# Get alignment statistics
info = aligner.get_alignment_info()
print(f"Tempo ratio: {info['tempo_ratio']:.2f}x")
```

## 📊 Demo

Run the demo script to see DTW in action:

```bash
python demo_dtw_alignment.py
```

This will demonstrate:
1. Same speed alignment (1.0x)
2. 10% faster alignment (1.1x)
3. 10% slower alignment (0.9x)

## 🔍 Cách hoạt động (How It Works)

### 1. Feature Extraction

DTW extracts a feature vector from each pose frame:

- **Angles**: Left/right arm angles, left/right leg angles, head angle (5 features)
- **Heights**: Left/right arm heights, left/right leg heights (4 features)
- **Positions**: Relative positions of wrists and ankles (8 features)

Total: **17+ dimensional feature vector** per frame

### 2. Sequence Alignment

Uses FastDTW algorithm to find optimal alignment path:

```
Test frames:   [T0, T1, T2, T3, ..., T109]  (110 frames, 1.1x faster)
                 |   |   |   |        |
                 ↓   ↓   ↓   ↓        ↓
Golden frames: [G0, G1, G2, G3, ..., G99]   (100 frames, normal)
```

### 3. Frame Mapping

After alignment, each test frame is mapped to the most similar golden frame:

```
Test frame 0   → Golden frame 0
Test frame 25  → Golden frame 25
Test frame 50  → Golden frame 50
Test frame 100 → Golden frame 99
Test frame 109 → Golden frame 99
```

### 4. Error Detection

Errors are detected by comparing **aligned** frame pairs instead of same-index pairs.

## ⚙️ Configuration Options

### window_size (default: 50)

Controls the maximum allowed warping between sequences:
- **Smaller values** (e.g., 20): Faster computation, less flexible alignment
- **Larger values** (e.g., 100): Slower computation, more flexible alignment

Recommended: 50 for videos with ±20% speed variation

### distance_metric (default: "euclidean")

Distance metric for comparing feature vectors:
- **"euclidean"**: Standard Euclidean distance (recommended)
- **"manhattan"**: Manhattan distance (L1 norm)
- **"cosine"**: Cosine similarity (good for normalized features)

## 🧪 Testing

Run the comprehensive test suite:

```bash
python -m pytest backend/tests/test_dtw_alignment.py -v
```

Tests include:
- ✅ Same speed alignment (1:1 mapping)
- ✅ Different speed alignment (1.5x faster)
- ✅ 10% tempo variation (problem statement scenario)
- ✅ Empty sequences handling
- ✅ Missing keypoints handling
- ✅ Alignment monotonicity
- ✅ Different distance metrics

## 📈 Performance

### Computational Complexity

- **Time complexity**: O(N×M) where N = test frames, M = golden frames
- **Space complexity**: O(N×M) for distance matrix
- **FastDTW optimization**: Reduces to O(N) with window constraint

### Typical Performance

| Video Length | Frames | Alignment Time |
|--------------|--------|----------------|
| 10 seconds   | 300    | ~0.2s          |
| 30 seconds   | 900    | ~0.6s          |
| 60 seconds   | 1800   | ~1.5s          |

*(Tested on CPU, times may vary)*

## 🎨 Integration Examples

### Example 1: Batch Processing with DTW

```python
import cv2
from backend.app.services.video_utils import load_video

# Load videos
test_cap, _ = load_video("test_video.mp4")
golden_cap, _ = load_video("golden_video.mp4")

# Extract keypoints
test_keypoints = []
golden_keypoints = []

# ... extract keypoints from both videos ...

# Align and compare
ai_controller = AIController(pose_service)
errors, info = ai_controller.process_video_with_dtw(
    test_keypoints, 
    golden_keypoints
)

print(f"Detected {len(errors)} errors")
print(f"Tempo ratio: {info['tempo_ratio']:.2f}x")
```

### Example 2: Real-time DTW Alignment

For real-time scenarios, accumulate frames and align periodically:

```python
# Accumulate frames
test_buffer = []
golden_buffer = []

while True:
    # ... get frame and keypoints ...
    test_buffer.append(test_keypoints)
    
    # Align every N frames
    if len(test_buffer) >= 30:  # Every 1 second at 30fps
        aligner = DTWAligner(window_size=20)
        distance, path = aligner.align_sequences(test_buffer, golden_buffer)
        # ... use alignment ...
        test_buffer = []
```

## 🐛 Troubleshooting

### Issue: DTW not working

**Solution**: Check if DTW is enabled in config:
```python
from backend.app.config import DTW_CONFIG
print(DTW_CONFIG["enabled"])  # Should be True
```

### Issue: Alignment takes too long

**Solution**: Reduce window_size:
```python
DTW_CONFIG["window_size"] = 20  # Smaller window = faster
```

### Issue: Poor alignment quality

**Solution**: Try different distance metrics:
```python
DTW_CONFIG["distance_metric"] = "manhattan"  # or "cosine"
```

## 📚 References

- [FastDTW Paper](https://cs.fit.edu/~pkc/papers/tdm04.pdf) - Salvador & Chan (2007)
- [DTW Tutorial](https://rtavenar.github.io/blog/dtw.html) - Comprehensive DTW guide
- [SciPy Distance Metrics](https://docs.scipy.org/doc/scipy/reference/spatial.distance.html)

## 🤝 Contributing

When extending DTW functionality:

1. **Add tests** in `backend/tests/test_dtw_alignment.py`
2. **Update documentation** in this file
3. **Maintain backward compatibility** (keep DTW disabled by default)
4. **Profile performance** for large sequences

## 📝 License

Same as parent project (Score-parade)

---

**Created**: 2024-12-12  
**Last Updated**: 2024-12-12  
**Version**: 1.0.0
