# Phase 7: FaceModelBuilder Node - Research

**Researched:** 2026-03-11
**Domain:** ComfyUI node implementation, face landmark averaging, image I/O, visualization
**Confidence:** HIGH

## Summary

Phase 7 assembles existing utilities (pose extraction, frontalization, normalization, model I/O) into a new `FaceModelBuilder` ComfyUI node. The node reads a directory of images, runs MediaPipe face detection on each, rejects extreme poses, computes a weighted average of frontalized+normalized 3D landmarks, and outputs a FACE_MODEL dict, quality report string, and landmark preview image.

The implementation is straightforward because all core math functions already exist in `utils/pose_utils.py` and the persistence layer is in `utils/model_io.py`. The main new code is: (1) directory scanning and image loading via PIL/numpy, (2) orchestrating the per-image pipeline, (3) weighted averaging with cos(yaw)*cos(pitch), (4) quality report string formatting, and (5) landmark preview rendering on a 512x512 canvas using PIL ImageDraw.

**Primary recommendation:** Create a single `face_model_builder.py` module following the established one-module-per-node pattern. The model_io schema needs updating from (478,2) to (478,3) for 3D stddev. Use PIL (already available via ComfyUI/mediapipe) for both image loading and preview rendering.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- STRING input for directory path (connects to existing PathSplitter node)
- Flat directory scan only — no recursive subdirectory traversal
- Accept common formats: jpg, jpeg, png, webp, bmp (filter by extension, skip non-matching silently)
- Minimum 1 valid image, no maximum — single valid image becomes the model directly
- Average 3D frontalized landmarks (478x3) with cos(yaw)*cos(pitch) weighting, then project to 2D (drop Z) for canonical_landmarks
- Per-landmark stddev computed in 3D space (requires model_io schema update from (478,2) to (478,3) — Phase 6 has no downstream consumers yet)
- Head dimensions computed per-image (weighted average), not from final averaged landmarks
- Images with no face detected are logged in quality report but obviously don't contribute to averaging
- Plain text table with aligned columns: File | Status | Yaw | Pitch | Roll | Confidence | Weight
- Sorted by status then filename: ACCEPTED first (by weight descending), then REJECTED (by yaw), then NO FACE
- Summary line at end: total images / accepted / rejected / no face, with yaw/pitch thresholds shown
- Last line: model save path ("Model saved to: /path/to/model.facemodel.npz")
- 512x512 black background canvas for preview
- Show 42 MORPH_CONTROL_INDICES as green dots, connected by white face oval contour lines
- Landmarks plotted in normalized space, scaled to fit canvas
- Minimal text header at top: "FaceModel (N images)"
- No stddev visualization — keep it clean
- Rejection thresholds: yaw +/-45 deg, pitch +/-30 deg (from Phase 5)
- cos(yaw)*cos(pitch) weighting (from Phase 5 requirements)
- Missing transformation matrix: fall back to 2D landmarks, assume frontal pose, image still contributes
- Green dots + white contour matches MediaPipe's green landmark convention

### Claude's Discretion
- Exact dot size and line thickness for preview
- Font choice for header text (PIL default is fine)
- How to scale/center normalized landmarks onto 512x512 canvas
- Internal function decomposition within the builder module
- Whether to save model before or after generating preview

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODL-01 | User can build a canonical face model from a directory of target images via FaceModelBuilder node | Directory scanning, per-image MediaPipe detection, frontalization, normalization, weighted averaging pipeline — all utils exist |
| MODL-02 | FaceModelBuilder auto-rejects extreme-pose images and weights averaging by cos(yaw)*cos(pitch) | `extract_pose_angles()` provides yaw/pitch; thresholds (45/30 deg) and weighting formula defined in context |
| MODL-04 | FaceModelBuilder outputs per-image quality report (used/rejected, yaw/pitch/roll, confidence) | Quality report format fully specified: aligned text table, sort order, summary line |
| MODL-05 | FaceModelBuilder outputs a landmark preview visualization for model validation | 512x512 canvas, MORPH_CONTROL_INDICES (42 points), FACE_OVAL_INDICES contour, PIL ImageDraw |

</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | (existing) | Landmark arrays, weighted averaging | Core math substrate |
| mediapipe | >=0.10.14 | Face detection + 3D landmarks + transformation matrix | Already used by FaceDetect node |
| scipy | (existing) | Rotation class for frontalization | Transitive dep via scikit-image |
| Pillow (PIL) | (existing) | Image loading from disk, preview rendering | Available via ComfyUI runtime |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| torch | (existing) | ComfyUI tensor format for preview output | Converting numpy preview to IMAGE tensor |
| pathlib | stdlib | Path manipulation for directory scanning | File extension filtering |

### No New Dependencies Required
The entire phase can be implemented with existing project dependencies. PIL is available in the ComfyUI runtime (used in tests already). No pip install needed.

## Architecture Patterns

### Module Structure
```
comfyui_imgtools/
├── face_model_builder.py    # NEW — FaceModelBuilder node class
├── utils/
│   ├── model_io.py          # MODIFY — update schema (478,2) -> (478,3) for stddev
│   ├── pose_utils.py         # REUSE — frontalize, normalize, head_dimensions
│   ├── mediapipe_helper.py   # REUSE — get_landmarker (with output_facial_transformation_matrixes=True)
│   ├── landmarks.py          # REUSE — extract_landmarks
│   └── morph_utils.py        # REUSE — MORPH_CONTROL_INDICES, FACE_OVAL_INDICES (via face_mask)
├── __init__.py               # MODIFY — register FaceModelBuilder node
└── tests/
    ├── test_face_model_builder.py  # NEW — unit + integration tests
    └── test_model_io.py            # MODIFY — update for (478,3) stddev schema
```

### Pattern 1: Per-Image Processing Pipeline
**What:** Each image goes through: load -> detect -> extract landmarks -> check pose -> frontalize -> normalize -> accumulate
**When to use:** For every valid image in the directory

```python
# Pipeline per image (pseudocode showing existing function reuse):
from utils.mediapipe_helper import get_landmarker
from utils.landmarks import extract_landmarks
from utils.pose_utils import (
    extract_pose_angles, frontalize_landmarks,
    normalize_landmarks_3d, compute_head_dimensions,
)

# 1. Load image from disk as PIL -> numpy -> MediaPipe Image
# 2. landmarker = get_landmarker(output_facial_transformation_matrixes=True)
# 3. result = landmarker.detect(mp_image)
# 4. faces = extract_landmarks(result, w, h)
# 5. Check pose: if abs(yaw) > 45 or abs(pitch) > 30 -> reject
# 6. weight = cos(radians(yaw)) * cos(radians(pitch))
# 7. frontalized = frontalize_landmarks(face["landmarks_3d"], pose["matrix"])
# 8. normalized, ipd = normalize_landmarks_3d(frontalized)
# 9. head_dims = compute_head_dimensions(face["landmarks_3d"], ipd)
# 10. Accumulate: weighted_sum += weight * normalized; weight_total += weight
```

### Pattern 2: ComfyUI Node Registration (Established)
**What:** Follow exact same pattern as FaceDetect, FaceCropAlign, etc.
**Example from codebase:**
```python
class FaceModelBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {"default": ""}),
            },
            "optional": {
                "yaw_threshold": ("FLOAT", {"default": 45.0, "min": 0.0, "max": 90.0, "step": 1.0}),
                "pitch_threshold": ("FLOAT", {"default": 30.0, "min": 0.0, "max": 90.0, "step": 1.0}),
                "save_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("FACE_MODEL", "STRING", "IMAGE")
    RETURN_NAMES = ("face_model", "quality_report", "preview")
    FUNCTION = "build_model"
    CATEGORY = "imgtools/face"
```

### Pattern 3: FACE_MODEL as Custom Type
**What:** FACE_MODEL is a Python dict passed through ComfyUI's type system. ComfyUI allows arbitrary custom type names as strings — no registration needed.
**Content:** Same structure as `load_face_model()` returns: `{"version", "canonical_landmarks", "head_dimensions", "control_indices", "landmark_stddev"}`

### Anti-Patterns to Avoid
- **Recursive directory traversal:** Context explicitly says flat scan only. Use `Path.iterdir()`, not `Path.rglob()`.
- **Loading all images into memory at once:** Process one at a time, only accumulate landmark arrays. Images can be large.
- **Using OpenCV for image loading:** Project constraint is no OpenCV. Use PIL.
- **Creating MediaPipe landmarker per image:** Reuse the cached landmarker from `get_landmarker()`. It's already singleton-cached.
- **Computing stddev in 2D:** Context says 3D stddev. This requires model_io schema change.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Face detection | Custom detector | `get_landmarker()` + `extract_landmarks()` | Already handles all edge cases |
| Pose extraction | Manual matrix decomposition | `extract_pose_angles()` | Handles scale removal, tested |
| 3D frontalization | Custom rotation math | `frontalize_landmarks()` | Centroid-based, tested |
| IPD normalization | Custom normalization | `normalize_landmarks_3d()` | Handles degenerate cases |
| Head dimensions | Manual bounding box | `compute_head_dimensions()` | Consistent with Phase 5/6 |
| NPZ persistence | Custom file format | `save_face_model()` / `load_face_model()` | Schema-validated, tested |
| Face oval indices | Hardcoded list | Import `FACE_OVAL_INDICES` from `face_mask` | Single source of truth |
| Control point indices | Hardcoded list | Import `MORPH_CONTROL_INDICES` from `morph_utils` | Single source of truth |
| Image to MediaPipe conversion | Manual conversion | Pattern from `face_detection.py` | Proven approach |

## Common Pitfalls

### Pitfall 1: MediaPipe Landmarker Without Transformation Matrix
**What goes wrong:** `get_landmarker()` defaults to `output_facial_transformation_matrixes=False` for backward compatibility. Without this flag, no pose data is available.
**Why it happens:** Phase 5 deliberately kept the default as False.
**How to avoid:** Explicitly call `get_landmarker(output_facial_transformation_matrixes=True)` in the builder.
**Warning signs:** All faces have `pose=None` in their face dict.

### Pitfall 2: Missing Transformation Matrix Fallback
**What goes wrong:** Some images may detect a face but not produce a transformation matrix (older MediaPipe versions, edge cases).
**Why it happens:** `extract_landmarks()` sets `pose=None` when matrix is unavailable.
**How to avoid:** Context decision: "fall back to 2D landmarks, assume frontal pose, image still contributes." Use 2D landmarks (drop Z or use as-is with z=0 assumption), weight=1.0, mark in report.
**Warning signs:** Face dict has `pose=None` despite face being detected.

### Pitfall 3: model_io Schema Change Breaking Tests
**What goes wrong:** Changing `landmark_stddev` from (478,2) to (478,3) breaks existing `test_model_io.py` tests.
**Why it happens:** Tests hardcode expected shapes.
**How to avoid:** Update model_io.py schema AND all tests together. The context notes "Phase 6 has no downstream consumers yet" so this is safe.
**Warning signs:** `test_model_io.py` failures after schema change.

### Pitfall 4: Division by Zero in Weighted Average
**What goes wrong:** If all images are rejected (no valid weights), dividing by zero weight sum.
**Why it happens:** Directory with only extreme-pose images.
**How to avoid:** Check `total_weight > 0` before dividing. Raise a clear error or return empty model with explanation in quality report.
**Warning signs:** All images in report show REJECTED status.

### Pitfall 5: PIL Image Mode for MediaPipe
**What goes wrong:** MediaPipe expects RGB numpy arrays. RGBA or grayscale images from disk cause errors.
**Why it happens:** PNG files may have alpha channels, some images may be grayscale.
**How to avoid:** Always `img.convert("RGB")` after PIL open, before converting to numpy.
**Warning signs:** MediaPipe detection fails on specific image formats.

### Pitfall 6: Preview Landmark Scaling
**What goes wrong:** Normalized landmarks are centered at origin with IPD=1.0. Plotting directly on 512x512 canvas puts everything in one pixel.
**Why it happens:** Normalized space is roughly [-2, 2] range, canvas is [0, 512].
**How to avoid:** After averaging, compute bounding box of the 42 control points, add padding (10-15%), then scale+translate to fit canvas. Use the 42 MORPH_CONTROL_INDICES for bounding box, not all 478.
**Warning signs:** Preview shows dots clustered in one corner or off-canvas.

## Code Examples

### Image Loading from Directory (PIL)
```python
from pathlib import Path
from PIL import Image
import numpy as np

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

def scan_images(directory: str) -> list[Path]:
    """Flat scan of directory for supported image files."""
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Directory not found: {directory}")

    images = []
    for p in sorted(dir_path.iterdir()):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            images.append(p)
    return images

def load_image_as_mediapipe(path: Path):
    """Load image file and convert to MediaPipe Image format."""
    import mediapipe as mp
    img = Image.open(path).convert("RGB")
    img_np = np.array(img, dtype=np.uint8)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=img_np), img_np.shape[1], img_np.shape[0]
```

### Weighted Averaging of 3D Landmarks
```python
import numpy as np
import math

def compute_weighted_average(accepted_data: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Compute weighted average of normalized 3D landmarks.

    Each entry in accepted_data has: normalized_3d (478,3), weight (float), head_dims (dict)
    Returns: (averaged_landmarks_3d (478,3), stddev_3d (478,3))
    """
    weights = np.array([d["weight"] for d in accepted_data])
    total_weight = weights.sum()

    # Weighted mean
    landmarks_stack = np.stack([d["normalized_3d"] for d in accepted_data])  # (N, 478, 3)
    w = weights[:, None, None]  # (N, 1, 1)
    weighted_mean = (landmarks_stack * w).sum(axis=0) / total_weight  # (478, 3)

    # Weighted stddev
    diffs = landmarks_stack - weighted_mean[None, :, :]  # (N, 478, 3)
    weighted_var = (w * diffs**2).sum(axis=0) / total_weight  # (478, 3)
    stddev = np.sqrt(weighted_var)  # (478, 3)

    return weighted_mean, stddev
```

### Preview Rendering with PIL ImageDraw
```python
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def render_preview(canonical_2d: np.ndarray, control_indices: list[int],
                   oval_indices: list[int], n_images: int) -> np.ndarray:
    """Render 512x512 landmark preview image.

    Returns: numpy array (512, 512, 3) uint8
    """
    canvas_size = 512
    img = Image.new("RGB", (canvas_size, canvas_size), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Header text
    draw.text((10, 10), f"FaceModel ({n_images} images)", fill=(255, 255, 255))

    # Scale landmarks to fit canvas with padding
    ctrl_pts = canonical_2d[control_indices]
    margin = 50  # pixels padding
    x_min, y_min = ctrl_pts.min(axis=0)
    x_max, y_max = ctrl_pts.max(axis=0)
    x_range = x_max - x_min
    y_range = y_max - y_min

    usable = canvas_size - 2 * margin
    scale = usable / max(x_range, y_range)

    # Transform: normalized -> canvas coords
    def to_canvas(pts_2d):
        centered = pts_2d - np.array([x_min, y_min])
        scaled = centered * scale + margin
        # Center in canvas
        offset_x = (canvas_size - x_range * scale) / 2 - margin + margin
        offset_y = (canvas_size - y_range * scale) / 2 - margin + margin
        scaled[:, 0] += offset_x - margin
        scaled[:, 1] += offset_y - margin
        return scaled

    canvas_pts = to_canvas(canonical_2d)

    # Draw face oval contour (white lines connecting oval points in order)
    oval_canvas = canvas_pts[oval_indices]
    for i in range(len(oval_canvas)):
        p1 = tuple(oval_canvas[i].astype(int))
        p2 = tuple(oval_canvas[(i + 1) % len(oval_canvas)].astype(int))
        draw.line([p1, p2], fill=(255, 255, 255), width=1)

    # Draw control points as green dots
    for idx in control_indices:
        x, y = canvas_pts[idx]
        r = 3  # dot radius
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(0, 255, 0))

    return np.array(img, dtype=np.uint8)
```

### Quality Report Generation
```python
def format_quality_report(results: list[dict], save_path: str,
                          yaw_thresh: float, pitch_thresh: float) -> str:
    """Format per-image quality report as aligned text table.

    Each result dict has: filename, status, yaw, pitch, roll, confidence, weight
    """
    # Sort: ACCEPTED (by weight desc), REJECTED (by yaw), NO FACE
    status_order = {"ACCEPTED": 0, "REJECTED": 1, "NO FACE": 2}

    def sort_key(r):
        s = status_order.get(r["status"], 3)
        if r["status"] == "ACCEPTED":
            return (s, -r["weight"])
        elif r["status"] == "REJECTED":
            return (s, abs(r.get("yaw", 0)))
        return (s, r["filename"])

    results_sorted = sorted(results, key=sort_key)

    # Build aligned table
    lines = []
    header = f"{'File':<30} {'Status':<10} {'Yaw':>6} {'Pitch':>6} {'Roll':>6} {'Conf':>6} {'Weight':>7}"
    lines.append(header)
    lines.append("-" * len(header))

    for r in results_sorted:
        yaw_s = f"{r.get('yaw', 0):>5.1f}°" if r["status"] != "NO FACE" else "   N/A"
        pitch_s = f"{r.get('pitch', 0):>5.1f}°" if r["status"] != "NO FACE" else "   N/A"
        roll_s = f"{r.get('roll', 0):>5.1f}°" if r["status"] != "NO FACE" else "   N/A"
        conf_s = f"{r.get('confidence', 0):>5.2f}" if r["status"] != "NO FACE" else "   N/A"
        weight_s = f"{r.get('weight', 0):>6.4f}" if r["status"] == "ACCEPTED" else "      -"
        lines.append(f"{r['filename']:<30} {r['status']:<10} {yaw_s} {pitch_s} {roll_s} {conf_s} {weight_s}")

    # Summary
    accepted = sum(1 for r in results if r["status"] == "ACCEPTED")
    rejected = sum(1 for r in results if r["status"] == "REJECTED")
    no_face = sum(1 for r in results if r["status"] == "NO FACE")
    lines.append("")
    lines.append(f"Total: {len(results)} | Accepted: {accepted} | Rejected: {rejected} | No face: {no_face}")
    lines.append(f"Thresholds: yaw={yaw_thresh}°, pitch={pitch_thresh}°")
    lines.append(f"Model saved to: {save_path}")

    return "\n".join(lines)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| (478,2) stddev in model_io | (478,3) stddev for 3D space | Phase 7 | Schema change needed in model_io.py |
| 2D landmark averaging | 3D frontalized averaging -> 2D projection | Phase 7 | More accurate canonical model |
| Single target image for morph | Multi-image averaged model | Phase 7 | New capability, main feature |

**Important schema change:** `model_io.py` must update:
- `_SCHEMA["landmark_stddev"]` from `("f", (478, 2))` to `("f", (478, 3))`
- `_SCHEMA["canonical_landmarks"]` stays (478, 2) — the 3D average is projected to 2D before saving
- `save_face_model()` and `load_face_model()` signature/docs updated
- `MODEL_VERSION` should bump to "2" since shape changes are breaking
- Existing test data in `test_model_io.py` must be updated

## Open Questions

1. **Model version bump**
   - What we know: Schema changes from (478,2) to (478,3) for stddev are breaking
   - What's unclear: Should version go to "2" or stay "1" since no downstream consumers exist?
   - Recommendation: Bump to "2" for correctness. No backward compat needed (context says no consumers yet).

2. **Save path default behavior**
   - What we know: Model needs to be saved as .facemodel.npz
   - What's unclear: Where to save when no explicit save_path is provided
   - Recommendation: Default to `{directory}/face_model.facemodel.npz` (save alongside source images). User can override via save_path input.

3. **Confidence value source**
   - What we know: Quality report includes "Confidence" column
   - What's unclear: MediaPipe's `FaceLandmarkerResult` provides detection confidence per face, but `extract_landmarks()` doesn't currently return it
   - Recommendation: Extend face detection to capture confidence, or use `min_face_detection_confidence` threshold as proxy. The `result.face_landmarks` list ordering already implies confidence filtering. May need to access `result.face_blendshapes` or detection score from the underlying result. Investigate at implementation time — could use detection confidence from MediaPipe result object.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none (uses default discovery) |
| Quick run command | `conda run -n comfyui pytest tests/test_face_model_builder.py -x -v` |
| Full suite command | `conda run -n comfyui pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODL-01 | Build model from directory of images | unit | `conda run -n comfyui pytest tests/test_face_model_builder.py::TestBuildModel -x` | No - Wave 0 |
| MODL-02 | Reject extreme poses, weight by cos(yaw)*cos(pitch) | unit | `conda run -n comfyui pytest tests/test_face_model_builder.py::TestPoseFiltering -x` | No - Wave 0 |
| MODL-04 | Quality report with per-image status | unit | `conda run -n comfyui pytest tests/test_face_model_builder.py::TestQualityReport -x` | No - Wave 0 |
| MODL-05 | Landmark preview visualization | unit | `conda run -n comfyui pytest tests/test_face_model_builder.py::TestPreviewImage -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `conda run -n comfyui pytest tests/test_face_model_builder.py tests/test_model_io.py -x -v`
- **Per wave merge:** `conda run -n comfyui pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_face_model_builder.py` — covers MODL-01, MODL-02, MODL-04, MODL-05
- [ ] Update `tests/test_model_io.py` — update for (478,3) stddev schema change

## Sources

### Primary (HIGH confidence)
- Existing codebase: `utils/pose_utils.py`, `utils/model_io.py`, `utils/landmarks.py`, `utils/mediapipe_helper.py` — all functions verified by reading source
- Existing codebase: `utils/morph_utils.py` (MORPH_CONTROL_INDICES), `utils/face_mask.py` (FACE_OVAL_INDICES) — verified by reading source
- Existing codebase: `__init__.py`, `face_detection.py` — node registration pattern verified
- Existing tests: `tests/test_model_io.py`, `tests/test_pose_utils.py`, `tests/conftest.py` — test patterns verified

### Secondary (MEDIUM confidence)
- PIL ImageDraw for preview rendering — standard Python library, well-known API
- ComfyUI custom type strings (FACE_MODEL) — based on established pattern in codebase (FACE_LANDMARKS already used)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project, no new deps
- Architecture: HIGH - follows established patterns from existing nodes, all util functions verified
- Pitfalls: HIGH - identified from reading actual code and understanding data flow
- Preview rendering: MEDIUM - PIL ImageDraw approach is straightforward but exact scaling math needs validation at impl time

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable domain, no external dependencies changing)
