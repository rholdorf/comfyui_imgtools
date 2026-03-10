# Phase 1: Environment and Detection - Research

**Researched:** 2026-03-10
**Domain:** MediaPipe Face Landmarker on macOS Apple Silicon + ComfyUI node conventions
**Confidence:** HIGH

## Summary

MediaPipe Face Landmarker 0.10.18 is already installed and functional in the ComfyUI conda environment (Python 3.12.7 on Apple Silicon). The previously identified risk of Python 3.14 incompatibility is a non-issue -- ComfyUI runs in a `ComfyUI` conda env with Python 3.12.7, not the system Python 3.14. The full detection pipeline (torch tensor -> numpy uint8 -> mp.Image -> FaceLandmarkerResult with 478 landmarks) has been verified end-to-end.

The task model file is 3.6MB, downloadable from Google's CDN. The Face Landmarker API uses the `mediapipe.tasks.python.vision` module (not the legacy `mediapipe.solutions.face_mesh` which is deprecated and only returns 468 landmarks). ComfyUI custom types are simply string names in RETURN_TYPES tuples -- no registration required.

**Primary recommendation:** Implement a FaceDetect node using `mediapipe.tasks.python.vision.FaceLandmarker` with lazy model loading, auto-download, and graceful import-time checking. Use the new Tasks API exclusively.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use the **Full** Face Landmarker model (~3.6MB actual) -- auto-download from Google's CDN, store in models/ subfolder
- Detect **all faces** in image; face index selection deferred to Phase 2
- No face detected: return empty FACE_LANDMARKS and count=0, no error
- **Custom FACE_LANDMARKS type** for landmark data output
- Output a **debug/preview IMAGE** with landmarks drawn (optional output)
- Output a **face count INT**
- **Separate file**: face_detection.py (not in nodes.py)
- **utils/ subfolder** for helpers (mediapipe_helper.py, landmarks.py)
- Node display names **prefixed "ImgTools"** (e.g., "ImgTools Face Detect")
- **requirements.txt** with minimum version pins (e.g., mediapipe>=0.10.14)
- **Only MediaPipe** in Phase 1 (scikit-image deferred to Phase 3)
- **Import-time check with warning**: try import, print warning if fails, don't crash

### Claude's Discretion
- ComfyUI CATEGORY namespace for face nodes (e.g., "face/detection" vs "image/face/detection")

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DET-01 | Node detects face landmarks using MediaPipe Face Landmarker (478 points) | MediaPipe 0.10.18 verified working in ComfyUI conda env; Tasks API returns 478 NormalizedLandmarks per face; full pipeline tested |
| PLAT-01 | All nodes run on macOS with Apple Silicon (no CUDA-only dependencies) | Verified: MediaPipe uses XNNPACK CPU delegate on Apple Silicon; no CUDA dependency; Metal GL context available |
| PLAT-02 | Dependencies limited to MediaPipe + scikit-image (+ existing ComfyUI deps) | Only mediapipe needed for Phase 1; already installed; requirements.txt with minimum pin |
| PLAT-03 | Nodes follow ComfyUI conventions (INPUT_TYPES, RETURN_TYPES, IMAGE tensors) | Existing codebase patterns documented; IMAGE tensor is [batch, H, W, C] float32 [0,1]; custom types are just string names |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mediapipe | >=0.10.14 (0.10.18 installed) | Face landmark detection (478 points) | Google's official face mesh solution; runs on CPU; Apple Silicon compatible |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| torch | 2.3.1 (installed) | IMAGE tensor format | ComfyUI's native tensor format; already present |
| numpy | 1.26.4 (installed) | Array conversion bridge | torch <-> mediapipe conversion; already present |
| Pillow | (installed) | Image I/O if needed | Already a ComfyUI dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mediapipe.tasks.python.vision.FaceLandmarker | mediapipe.solutions.face_mesh (legacy) | Legacy API: only 468 landmarks, deprecated, different API surface -- do NOT use |

**Installation (requirements.txt):**
```
mediapipe>=0.10.14
```

## Architecture Patterns

### Recommended Project Structure
```
comfyui_imgtools/
  __init__.py           # Updated: import + register face detection node
  nodes.py              # Existing nodes (untouched)
  face_detection.py     # New: FaceDetect node class
  utils/
    __init__.py
    mediapipe_helper.py # Model download, lazy loading, landmarker wrapper
    landmarks.py        # Landmark data structures, drawing utilities
  models/               # Auto-created; stores face_landmarker.task
  requirements.txt      # New: mediapipe>=0.10.14
  tests/
    __init__.py
    conftest.py         # Shared fixtures (sample images, mock landmarks)
    test_face_detection.py
    test_mediapipe_helper.py
```

### Pattern 1: Torch-to-MediaPipe Conversion Bridge
**What:** Convert ComfyUI IMAGE tensors to MediaPipe mp.Image format and back.
**When to use:** At node entry (input processing) and exit (output creation).
**Example:**
```python
# Source: Verified in ComfyUI conda env 2026-03-10
import torch
import numpy as np
import mediapipe as mp

def comfyui_to_mediapipe(image_tensor):
    """Convert ComfyUI IMAGE tensor to MediaPipe Image.

    Args:
        image_tensor: torch tensor [batch, H, W, C], float32, [0, 1]
    Returns:
        mp.Image (SRGB, uint8) for first image in batch
    """
    img_np = (image_tensor[0].cpu().numpy() * 255).astype(np.uint8)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=img_np)
```

### Pattern 2: Lazy Model Loading with Auto-Download
**What:** Download model on first use, cache the FaceLandmarker instance globally.
**When to use:** First invocation of face detection node.
**Example:**
```python
# Source: Verified end-to-end in ComfyUI conda env
import os
import urllib.request
from mediapipe.tasks.python import BaseOptions, vision

_landmarker = None
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

def get_landmarker():
    global _landmarker
    if _landmarker is None:
        model_dir = os.path.join(os.path.dirname(__file__), "models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "face_landmarker.task")
        if not os.path.exists(model_path):
            print("[ImgTools] Downloading MediaPipe Face Landmarker model...")
            urllib.request.urlretrieve(MODEL_URL, model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=10,
        )
        _landmarker = vision.FaceLandmarker.create_from_options(options)
    return _landmarker
```

### Pattern 3: ComfyUI Node Class Convention
**What:** Standard node class structure matching existing codebase patterns.
**When to use:** Every node definition.
**Example:**
```python
# Source: Existing nodes.py pattern in this project
class FaceDetect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "min_detection_confidence": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05
                }),
            }
        }

    RETURN_TYPES = ("FACE_LANDMARKS", "IMAGE", "INT")
    RETURN_NAMES = ("landmarks", "preview", "face_count")
    FUNCTION = "detect_faces"
    CATEGORY = "imgtools/face"  # Recommendation for Claude's discretion

    def detect_faces(self, image, min_detection_confidence=0.5):
        # ... implementation ...
        return (landmarks_data, preview_image, face_count)
```

### Pattern 4: Custom FACE_LANDMARKS Data Format
**What:** Python list of dicts, each containing a numpy array of landmark coordinates.
**When to use:** Output from detection node, input to future morph node.
**Example:**
```python
# FACE_LANDMARKS is a list of face dicts, one per detected face
# Each face dict contains denormalized pixel coordinates
face_landmarks_output = [
    {
        "landmarks": np.array([[x0, y0], [x1, y1], ...]),  # shape (478, 2), pixel coords
        "landmarks_3d": np.array([[x0, y0, z0], ...]),      # shape (478, 3), normalized + depth
    },
    # ... one entry per face
]
# When no faces detected: empty list []
```

### Pattern 5: Landmark Visualization for Debug Preview
**What:** Draw detected landmarks on image for visual verification.
**When to use:** Creating the optional preview IMAGE output.
**Example:**
```python
import numpy as np

def draw_landmarks_on_image(img_np, face_landmarks_list, img_width, img_height):
    """Draw landmarks as small dots on image copy.

    Args:
        img_np: numpy array (H, W, 3) uint8
        face_landmarks_list: list of MediaPipe NormalizedLandmarkList
        img_width, img_height: image dimensions for denormalization
    Returns:
        numpy array (H, W, 3) uint8 with landmarks drawn
    """
    result = img_np.copy()
    for face_lms in face_landmarks_list:
        for lm in face_lms:
            x = int(lm.x * img_width)
            y = int(lm.y * img_height)
            # Draw a small 2x2 dot
            result[max(0,y-1):y+1, max(0,x-1):x+1] = [0, 255, 0]  # green
    return result
```

### Anti-Patterns to Avoid
- **Legacy mediapipe.solutions.face_mesh:** Deprecated API, only 468 landmarks (not 478), different interface. Use `mediapipe.tasks.python.vision.FaceLandmarker` exclusively.
- **Creating new FaceLandmarker per invocation:** Model loading takes ~100ms. Cache globally via lazy loading pattern.
- **Storing detection results in global state:** ComfyUI nodes are stateless. Only cache the model, never results.
- **Normalizing landmarks to [0,1] in output:** Store as pixel coordinates (denormalized) in FACE_LANDMARKS -- downstream nodes need pixel coords for warping.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Face landmark detection | Custom CNN/dlib detector | MediaPipe Face Landmarker | 478 precise landmarks, pre-trained, runs on CPU, <30ms |
| Model file management | Custom download/caching | urllib.request.urlretrieve + os.path.exists check | Simple, reliable, no extra deps |
| Landmark visualization | Complex OpenCV drawing pipeline | Simple numpy pixel painting (dots) | Phase 1 only needs basic debug preview; no need for face mesh connections drawing |

**Key insight:** MediaPipe handles all the heavy lifting. The node implementation is primarily conversion glue (torch <-> numpy <-> mp.Image) and ComfyUI convention compliance.

## Common Pitfalls

### Pitfall 1: Using Legacy MediaPipe API
**What goes wrong:** Import `mediapipe.solutions.face_mesh` instead of `mediapipe.tasks.python.vision.FaceLandmarker`. Get 468 landmarks instead of 478, deprecated warnings.
**Why it happens:** Most online tutorials still reference the legacy API.
**How to avoid:** Always use `from mediapipe.tasks.python import vision` and `vision.FaceLandmarker`.
**Warning signs:** Import from `mediapipe.solutions`, result has `.multi_face_landmarks` instead of `.face_landmarks`.

### Pitfall 2: Forgetting to Convert Tensor to uint8
**What goes wrong:** Pass float32 [0,1] numpy array to mp.Image. MediaPipe expects uint8 [0,255].
**Why it happens:** ComfyUI IMAGE tensors are float32.
**How to avoid:** Always multiply by 255 and cast: `(tensor.numpy() * 255).astype(np.uint8)`.
**Warning signs:** All-black detection results or assertion errors from MediaPipe.

### Pitfall 3: Not Handling Empty Detection Results
**What goes wrong:** Index into `result.face_landmarks[0]` when no faces detected. IndexError crashes node.
**Why it happens:** Assuming at least one face always present.
**How to avoid:** Check `len(result.face_landmarks) == 0` first. Return empty list and count=0.
**Warning signs:** Crashes on images without faces or with faces too small/blurry.

### Pitfall 4: num_faces Default of 1
**What goes wrong:** Only one face detected in multi-face images.
**Why it happens:** FaceLandmarkerOptions defaults `num_faces=1`.
**How to avoid:** Set `num_faces` to a reasonable maximum (e.g., 10) in options.
**Warning signs:** Always getting face_count=1 even with multiple visible faces.

### Pitfall 5: Model Path Relative to Wrong Directory
**What goes wrong:** Model file not found when ComfyUI loads the extension.
**Why it happens:** Using `__file__` relative path but cwd differs from extension directory.
**How to avoid:** Use `os.path.dirname(os.path.abspath(__file__))` as base. For utils/mediapipe_helper.py, navigate up to extension root.
**Warning signs:** FileNotFoundError on first run after model download.

### Pitfall 6: Crashing ComfyUI on Missing MediaPipe
**What goes wrong:** `import mediapipe` at module level crashes the entire ComfyUI server if mediapipe is not installed.
**Why it happens:** Python import errors propagate up and prevent extension loading.
**How to avoid:** Wrap import in try/except at extension load time. Print clear warning with install instructions. Only fail at node execution time if actually used.
**Warning signs:** ComfyUI fails to start after adding the extension.

## Code Examples

### Complete Detection Flow (Verified)
```python
# Source: Verified end-to-end in ComfyUI conda env (Python 3.12.7, mediapipe 0.10.18)
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

# Create landmarker
options = vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="models/face_landmarker.task"),
    running_mode=vision.RunningMode.IMAGE,
    num_faces=10,
    min_face_detection_confidence=0.5,
    min_face_presence_confidence=0.5,
)
landmarker = vision.FaceLandmarker.create_from_options(options)

# Convert ComfyUI tensor to mp.Image
img_np = (image_tensor[0].cpu().numpy() * 255).astype(np.uint8)  # [H,W,3] uint8
mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_np)

# Detect
result = landmarker.detect(mp_image)

# Access results
num_faces = len(result.face_landmarks)
for face_idx, face_lms in enumerate(result.face_landmarks):
    # face_lms is a list of 478 NormalizedLandmark objects
    # Each has .x, .y (normalized [0,1]) and .z (relative depth)
    landmarks_px = np.array([
        [lm.x * img_np.shape[1], lm.y * img_np.shape[0]]
        for lm in face_lms
    ])  # shape (478, 2), pixel coordinates
```

### __init__.py Registration Pattern
```python
# Source: Existing __init__.py pattern in this project
from .nodes import ImageDimensionFitter, ImagePaddingCalculator, PathSplitter

# Conditional import for face detection
try:
    from .face_detection import FaceDetect
    _face_nodes_available = True
except ImportError as e:
    print(f"[ImgTools] Warning: Face detection nodes unavailable. {e}")
    print("[ImgTools] Install mediapipe: pip install mediapipe>=0.10.14")
    _face_nodes_available = False

NODE_CLASS_MAPPINGS = {
    "ImageDimensionFitter": ImageDimensionFitter,
    "ImagePaddingCalculator": ImagePaddingCalculator,
    "PathSplitter": PathSplitter,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageDimensionFitter": "Image Dimension Fitter",
    "ImagePaddingCalculator": "Image Padding Calculator",
    "PathSplitter": "Path Splitter",
}

if _face_nodes_available:
    NODE_CLASS_MAPPINGS["FaceDetect"] = FaceDetect
    NODE_DISPLAY_NAME_MAPPINGS["FaceDetect"] = "ImgTools Face Detect"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| mediapipe.solutions.face_mesh | mediapipe.tasks.python.vision.FaceLandmarker | MediaPipe 0.10.x (2023) | 478 landmarks (vs 468), unified Tasks API, better perf |
| Manual model download | Auto-download from CDN in code | Standard practice | No manual setup required |
| dlib face landmarks (68 points) | MediaPipe (478 points) | N/A | Far more precise contour, no compiled C++ dep |

**Deprecated/outdated:**
- `mediapipe.solutions.face_mesh`: Legacy API. Use Tasks API (`mediapipe.tasks.python.vision`).
- `mediapipe.solutions.drawing_utils`: Still functional but not needed for simple dot visualization.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 |
| Config file | none -- see Wave 0 |
| Quick run command | `conda run -n ComfyUI pytest tests/ -x -q` |
| Full suite command | `conda run -n ComfyUI pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DET-01 | Detect 478 face landmarks from image | integration | `conda run -n ComfyUI pytest tests/test_face_detection.py::test_detect_landmarks_count -x` | Wave 0 |
| DET-01 | Return structured FACE_LANDMARKS data | unit | `conda run -n ComfyUI pytest tests/test_face_detection.py::test_landmarks_data_structure -x` | Wave 0 |
| DET-01 | Handle no-face images gracefully | unit | `conda run -n ComfyUI pytest tests/test_face_detection.py::test_no_face_returns_empty -x` | Wave 0 |
| PLAT-01 | MediaPipe runs without CUDA | smoke | `conda run -n ComfyUI pytest tests/test_mediapipe_helper.py::test_landmarker_creation -x` | Wave 0 |
| PLAT-02 | Only mediapipe as new dependency | manual-only | Verify requirements.txt contents | N/A |
| PLAT-03 | Node follows ComfyUI conventions | unit | `conda run -n ComfyUI pytest tests/test_face_detection.py::test_node_conventions -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `conda run -n ComfyUI pytest tests/ -x -q`
- **Per wave merge:** `conda run -n ComfyUI pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` -- package init
- [ ] `tests/conftest.py` -- shared fixtures (sample test image with face, mock landmark data, ComfyUI-format tensor fixture)
- [ ] `tests/test_face_detection.py` -- covers DET-01, PLAT-03
- [ ] `tests/test_mediapipe_helper.py` -- covers PLAT-01 (model download, landmarker creation)
- [ ] `pytest.ini` or `pyproject.toml` [tool.pytest] section -- test configuration

## Open Questions

1. **CATEGORY namespace recommendation**
   - What we know: Existing nodes use "image/transform" and "utils". Impact Pack uses "ImpactPack". No enforced convention.
   - Recommendation: Use `"imgtools/face"` -- short, namespaced to this extension, groups all face nodes together. Consistent with "ImgTools" display name prefix.

2. **Batch image handling**
   - What we know: ComfyUI IMAGE tensors have batch dimension [B, H, W, C]. Current nodes process batch[0] implicitly via shape operations.
   - What's unclear: Should face detection process all images in a batch or just the first?
   - Recommendation: Process only `image[0]` for Phase 1 (single image detection). Batch support can be added later. Document this limitation.

## Sources

### Primary (HIGH confidence)
- [MediaPipe Face Landmarker Python Guide](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python) -- API usage, configuration options
- [MediaPipe FaceLandmarker API Reference](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarker) -- class reference
- Local verification in ComfyUI conda env (Python 3.12.7, mediapipe 0.10.18, torch 2.3.1) -- all code examples tested
- Existing codebase: `nodes.py`, `__init__.py` -- ComfyUI node conventions

### Secondary (MEDIUM confidence)
- [MediaPipe Face Landmarker Overview](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) -- model details, 478 landmarks
- Project ARCHITECTURE.md research -- landmark indices, TPS patterns (for forward-compatibility)

### Tertiary (LOW confidence)
- None -- all findings verified locally

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- mediapipe 0.10.18 tested and working in actual ComfyUI env
- Architecture: HIGH -- patterns derived from existing codebase + verified API
- Pitfalls: HIGH -- pitfalls identified from actual API testing and documentation
- Validation: MEDIUM -- test structure proposed but no existing tests to build on

**Key risk resolved:** Python 3.14 incompatibility is NOT an issue. ComfyUI runs in conda env with Python 3.12.7 where mediapipe 0.10.18 is already installed.

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable libraries, no fast-moving dependencies)
