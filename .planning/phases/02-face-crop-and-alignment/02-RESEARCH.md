# Phase 2: Face Crop and Alignment - Research

**Researched:** 2026-03-10
**Domain:** Face cropping, affine alignment, mask generation using MediaPipe landmarks + scikit-image + numpy
**Confidence:** HIGH

## Summary

This phase takes the FACE_LANDMARKS output from Phase 1's FaceDetect node and builds a new node (FaceCrop or FaceCropAlign) that crops a face region with configurable padding, aligns tilted faces to upright orientation using eye positions, allows face selection by index, and outputs the cropped image, alignment transform data, and a face mask.

The core math is straightforward: compute rotation angle from left/right eye positions using `arctan2`, build a 2x3 affine matrix, apply it with `skimage.transform.warp`, crop the result, and generate a mask from the face oval landmarks using `skimage.draw.polygon2mask`. All dependencies (numpy, scikit-image) are already approved in PLAT-02. No new dependencies are needed.

**Primary recommendation:** Build a single `FaceCropAlign` node that consumes FACE_LANDMARKS from FaceDetect, uses eye center landmarks for alignment, and outputs (IMAGE, ALIGN_DATA, MASK) as three separate outputs.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | (bundled with ComfyUI) | Affine matrix math, landmark manipulation | Already used in Phase 1 |
| scikit-image | >=0.20 | `transform.AffineTransform`, `transform.warp`, `draw.polygon2mask` | Approved in PLAT-02, pure Python, no CUDA dependency |
| torch | (bundled with ComfyUI) | IMAGE tensor I/O (ComfyUI convention) | Already used in Phase 1 |
| mediapipe | >=0.10.14 | Not directly used in this phase (landmarks come from Phase 1 FaceDetect) | Indirect dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `skimage.transform.AffineTransform` | 0.20+ | Build rotation+translation+scale matrix from eye positions | Core alignment computation |
| `skimage.transform.warp` | 0.20+ | Apply affine transform to image array | Image rotation/alignment |
| `skimage.draw.polygon2mask` | 0.20+ | Generate binary face mask from face oval landmark polygon | Mask output |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| skimage.transform.warp | Pure numpy affine + scipy.ndimage.affine_transform | More manual code, same result |
| skimage.draw.polygon2mask | Manual numpy polygon fill | polygon2mask is a one-liner, no reason to hand-roll |

**Installation:**
```bash
pip install scikit-image>=0.20
```
(Already satisfied via PLAT-02 dependencies)

## Architecture Patterns

### Recommended Project Structure
```
comfyui_imgtools/
  face_crop.py          # New FaceCropAlign node
  utils/
    alignment.py        # compute_eye_angle, build_alignment_transform, apply_alignment
    face_mask.py        # generate_face_mask from oval landmarks
    landmarks.py        # (existing) extract_landmarks, draw_landmarks_on_image
    mediapipe_helper.py # (existing) get_landmarker, comfyui_to_mediapipe
  tests/
    test_face_crop.py       # FaceCropAlign node convention + integration tests
    test_alignment.py       # Unit tests for alignment math
    test_face_mask.py       # Unit tests for mask generation
```

### Pattern 1: Eye-Based Alignment Transform
**What:** Compute rotation angle from eye center positions, build affine matrix to rotate face upright, apply to image.
**When to use:** Every time a face needs alignment before cropping.
**Example:**
```python
import numpy as np
from skimage.transform import AffineTransform, warp

# MediaPipe landmark indices for eye centers
# Right eye center: average of right eye contour landmarks
# Left eye center: average of left eye contour landmarks
RIGHT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
LEFT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]

def compute_eye_centers(landmarks_px):
    """Get (x, y) center of each eye from 478-point landmarks array."""
    left_eye = landmarks_px[LEFT_EYE_INDICES].mean(axis=0)
    right_eye = landmarks_px[RIGHT_EYE_INDICES].mean(axis=0)
    return left_eye, right_eye

def compute_alignment_angle(left_eye, right_eye):
    """Rotation angle (radians) to make eyes horizontal."""
    dy = right_eye[1] - left_eye[1]
    dx = right_eye[0] - left_eye[0]
    return np.arctan2(dy, dx)  # negative to correct tilt

def build_alignment_transform(landmarks_px, img_width, img_height):
    """Build AffineTransform that rotates face upright around face center."""
    left_eye, right_eye = compute_eye_centers(landmarks_px)
    angle = compute_alignment_angle(left_eye, right_eye)

    # Rotate around midpoint between eyes
    center = (left_eye + right_eye) / 2.0

    # Build transform: translate center to origin, rotate, translate back
    tform = AffineTransform(
        rotation=-angle,
        translation=(-center[0], -center[1])
    )
    # Compose with translate-back
    tform_back = AffineTransform(translation=(center[0], center[1]))
    full_transform = tform_back + tform  # skimage composes with +

    return full_transform, angle
```

### Pattern 2: Padded Face Crop
**What:** After alignment, compute bounding box from transformed landmarks, expand by padding factor, crop.
**When to use:** Extracting the face region with controllable context.
**Example:**
```python
def compute_padded_crop_box(landmarks_px, transform, padding_factor, img_w, img_h):
    """Compute crop box from transformed landmarks with padding.

    Args:
        landmarks_px: (478, 2) array of landmark pixel coords
        transform: AffineTransform used for alignment
        padding_factor: float, e.g. 0.3 means 30% padding on each side
        img_w, img_h: image dimensions for clamping

    Returns:
        (x1, y1, x2, y2) crop coordinates
    """
    # Transform landmarks to aligned space
    aligned_lms = transform(landmarks_px)

    # Bounding box of all landmarks
    x_min, y_min = aligned_lms.min(axis=0)
    x_max, y_max = aligned_lms.max(axis=0)

    # Add padding
    w = x_max - x_min
    h = y_max - y_min
    pad_x = w * padding_factor
    pad_y = h * padding_factor

    x1 = max(0, int(x_min - pad_x))
    y1 = max(0, int(y_min - pad_y))
    x2 = min(img_w, int(x_max + pad_x))
    y2 = min(img_h, int(y_max + pad_y))

    return (x1, y1, x2, y2)
```

### Pattern 3: Face Mask from Oval Landmarks
**What:** Generate a binary mask using the face oval contour landmark indices.
**When to use:** Output a mask that downstream nodes can use for compositing.
**Example:**
```python
from skimage.draw import polygon2mask

FACE_OVAL_INDICES = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323,
    361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
    176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
    162, 21, 54, 103, 67, 109
]

def generate_face_mask(landmarks_px, img_height, img_width):
    """Generate binary face mask from face oval landmarks.

    Args:
        landmarks_px: (478, 2) array with (x, y) pixel coordinates
        img_height, img_width: image dimensions

    Returns:
        numpy array (H, W) float32 mask, 0.0 or 1.0
    """
    oval_points = landmarks_px[FACE_OVAL_INDICES]
    # polygon2mask expects (row, col) = (y, x)
    polygon_rc = oval_points[:, ::-1]  # swap x,y to y,x
    mask = polygon2mask((img_height, img_width), polygon_rc)
    return mask.astype(np.float32)
```

### Pattern 4: ALIGN_DATA Custom Type for Downstream
**What:** Store alignment transform data as a dict so Phase 4 (Compositing) can reverse it.
**When to use:** The alignment transform, crop box, and original dimensions must be passed downstream for COMP-03.
**Example:**
```python
# ALIGN_DATA structure (custom ComfyUI type)
align_data = {
    "rotation_angle": float,       # radians, the alignment rotation applied
    "rotation_center": (float, float),  # (x, y) center of rotation
    "crop_box": (int, int, int, int),   # (x1, y1, x2, y2) in aligned image
    "original_size": (int, int),        # (width, height) of source image
    "transform_matrix": np.ndarray,     # 3x3 homogeneous matrix for full inverse
}
```

### Anti-Patterns to Avoid
- **Using OpenCV for transforms:** Project constraint PLAT-02 limits deps to MediaPipe + scikit-image. Do NOT add cv2 dependency.
- **Hardcoding single landmark for eye center:** Use the mean of all eye contour landmarks, not a single index. Single points are noisy.
- **Modifying the FaceDetect node:** Phase 2 should consume FACE_LANDMARKS from Phase 1 as-is. Add new node, do not modify existing.
- **Returning the transform as a matrix-only:** Downstream nodes need crop box and original size too. Use a dict.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Affine image transformation | Manual pixel-by-pixel rotation | `skimage.transform.warp` + `AffineTransform` | Handles interpolation, boundary conditions, sub-pixel accuracy |
| Polygon mask fill | Scanline fill algorithm | `skimage.draw.polygon2mask` | One-liner, correct edge handling |
| Rotation matrix math | Custom trig from scratch | `skimage.transform.AffineTransform(rotation=angle)` | Handles composition, inversion, homogeneous coords |
| Landmark coordinate transform | Manual matrix multiply | `AffineTransform.__call__(coords)` | Handles (N, 2) arrays directly |

**Key insight:** scikit-image's transform module handles the entire pipeline (build matrix, transform points, warp image, compose transforms, invert for reverse) with tested, optimized code. The only custom math is `arctan2` for the eye angle.

## Common Pitfalls

### Pitfall 1: Coordinate Order Confusion (x,y vs row,col)
**What goes wrong:** scikit-image uses (row, col) = (y, x) for image indexing, but landmarks are stored as (x, y). Mixing these up produces rotated/flipped results.
**Why it happens:** numpy image arrays are indexed [row, col] = [y, x], but geometric coordinates are (x, y).
**How to avoid:** Always convert explicitly. `polygon2mask` takes (row, col). `AffineTransform` operates on (x, y) = (col, row). Document which convention each function uses.
**Warning signs:** Mask appears mirrored or in wrong position; aligned face is rotated 90 degrees.

### Pitfall 2: Rotation Direction
**What goes wrong:** Face rotates further from upright instead of toward upright.
**Why it happens:** `arctan2` returns the angle OF the tilt. You need to rotate by the NEGATIVE of that angle to correct it. Also, image y-axis is flipped (down is positive).
**How to avoid:** Test with a known tilted face image. The angle from `arctan2(dy, dx)` where dy = right_eye_y - left_eye_y should be negated for the correction rotation.
**Warning signs:** Face tilts more after "alignment."

### Pitfall 3: Crop Coordinates Out of Bounds
**What goes wrong:** After rotation, some landmark positions may land outside the original image bounds, causing negative indices or indices beyond image size.
**Why it happens:** Rotation can move pixels outside the original canvas.
**How to avoid:** Clamp crop coordinates to [0, img_dimension]. Consider using `output_shape` parameter in `warp()` to expand the canvas if needed.
**Warning signs:** Black borders in cropped output, or IndexError.

### Pitfall 4: Transform Composition Order
**What goes wrong:** Applying translate then rotate gives different results than rotate then translate.
**Why it happens:** Affine transforms are not commutative.
**How to avoid:** The standard pattern is: (1) translate center to origin, (2) rotate, (3) translate back. In skimage, compose with `+` operator: `tform_back + tform_rotate + tform_to_origin`.
**Warning signs:** Face appears in wrong position after alignment.

### Pitfall 5: Losing Transform Data for Compositing
**What goes wrong:** Phase 4 (COMP-03) needs to reverse the alignment, but the transform data is lost.
**Why it happens:** Only outputting the cropped image without the transform metadata.
**How to avoid:** Output ALIGN_DATA as a separate output containing the full transform matrix, crop box, rotation angle, and original image dimensions.
**Warning signs:** Cannot reverse alignment in Phase 4.

### Pitfall 6: Face Index Out of Range
**What goes wrong:** User selects face_index=2 but only 1 face detected. Node crashes.
**Why it happens:** No bounds checking on the face index input.
**How to avoid:** Clamp face_index to valid range, or return empty/error gracefully. Use `min(face_index, len(faces) - 1)` with clear behavior documented.
**Warning signs:** IndexError in node execution.

## Code Examples

### Complete FaceCropAlign Node Skeleton
```python
# Source: Project conventions from Phase 1 FaceDetect pattern
class FaceCropAlign:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "landmarks": ("FACE_LANDMARKS",),
            },
            "optional": {
                "face_index": ("INT", {"default": 0, "min": 0, "max": 9, "step": 1}),
                "padding": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05}),
                "align": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "ALIGN_DATA", "MASK")
    RETURN_NAMES = ("cropped_face", "align_data", "face_mask")
    FUNCTION = "crop_and_align"
    CATEGORY = "imgtools/face"

    def crop_and_align(self, image, landmarks, face_index=0, padding=0.3, align=True):
        # 1. Select face by index (clamped)
        # 2. Compute alignment transform from eye positions (if align=True)
        # 3. Apply transform to image with skimage.transform.warp
        # 4. Compute padded crop box from transformed landmarks
        # 5. Crop the aligned image
        # 6. Generate face mask from oval landmarks (in crop space)
        # 7. Build ALIGN_DATA dict for downstream reversal
        # 8. Convert outputs to ComfyUI tensor format
        pass
```

### Affine Transform Application with skimage
```python
# Source: scikit-image docs - skimage.transform.warp
from skimage.transform import AffineTransform, warp

def apply_alignment(img_np, transform, output_shape=None):
    """Apply alignment transform to image.

    Args:
        img_np: (H, W, 3) uint8 or float32 array
        transform: AffineTransform instance
        output_shape: optional (H, W) for output canvas size

    Returns:
        Aligned image as float64 array (H, W, 3)
    """
    # warp expects float input, returns float
    if img_np.dtype == np.uint8:
        img_float = img_np.astype(np.float64) / 255.0
    else:
        img_float = img_np.astype(np.float64)

    aligned = warp(
        img_float,
        inverse_map=transform.inverse,
        output_shape=output_shape or img_float.shape[:2],
        order=1,           # bilinear interpolation
        mode='constant',   # black fill for out-of-bounds
        cval=0.0,
        preserve_range=True
    )
    return aligned
```

### ComfyUI Tensor Conversions
```python
# Source: Phase 1 existing patterns in face_detection.py
import torch
import numpy as np

def tensor_to_numpy(image_tensor):
    """ComfyUI IMAGE tensor [B, H, W, C] float32 -> numpy (H, W, 3) float64."""
    return image_tensor[0].cpu().numpy().astype(np.float64)

def numpy_to_tensor(img_np):
    """numpy (H, W, 3) float -> ComfyUI IMAGE tensor [1, H, W, C] float32."""
    return torch.from_numpy(img_np.astype(np.float32)).unsqueeze(0)

def mask_to_tensor(mask_np):
    """numpy (H, W) float -> ComfyUI MASK tensor [1, H, W] float32."""
    return torch.from_numpy(mask_np.astype(np.float32)).unsqueeze(0)
```

## MediaPipe Landmark Index Reference

Key landmark indices used in this phase (verified from MediaPipe face_mesh_connections.py source):

| Feature | Indices | Usage |
|---------|---------|-------|
| Right eye contour | 33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246 | Mean = right eye center for alignment |
| Left eye contour | 362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398 | Mean = left eye center for alignment |
| Right iris center | 468 | Alternative single-point eye center (less stable) |
| Left iris center | 473 | Alternative single-point eye center (less stable) |
| Face oval | 10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109 | Face mask polygon |

**Note on "left" vs "right":** MediaPipe uses the subject's perspective. "Left eye" = subject's left eye = viewer's right side of image.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| dlib 68-point landmarks | MediaPipe 478-point landmarks | ~2022 | More precise eye contours, iris tracking, face oval |
| OpenCV affine warp | scikit-image AffineTransform + warp | N/A (project constraint) | Avoids cv2 dependency per PLAT-02 |
| Single eye corner for alignment | Mean of full eye contour | Best practice | More robust to individual landmark noise |

**Deprecated/outdated:**
- `mediapipe.solutions.face_mesh` (legacy API): Use `mediapipe.tasks.python.vision.FaceLandmarker` instead (already done in Phase 1)

## Open Questions

1. **Canvas expansion during rotation**
   - What we know: Rotating an image can move content outside the original bounds. `warp()` supports `output_shape` to expand canvas.
   - What's unclear: Whether expanding the canvas is needed or if clamping crop coordinates is sufficient for typical face tilt angles (<30 degrees).
   - Recommendation: Start with same-size output and clamp. If tests show clipping issues with tilted faces, expand canvas.

2. **ALIGN_DATA serialization**
   - What we know: ComfyUI custom types are passed as Python objects between nodes in a workflow.
   - What's unclear: Whether ALIGN_DATA needs to be JSON-serializable for workflow saving/loading, or if it is purely in-memory.
   - Recommendation: Use a dict with numpy arrays. If serialization is needed later, add a conversion method. Keep the numpy matrix for computational efficiency.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DET-02 | Node crops face region with configurable padding margin | Padded crop box computation from transformed landmarks. `padding` float input (0.0-1.0) controls expansion. Landmarks bounding box + padding factor -> crop coordinates. |
| DET-03 | Node aligns tilted/rotated faces to upright orientation based on eye positions | Eye center computation from LEFT_EYE_INDICES/RIGHT_EYE_INDICES means, `arctan2` for angle, `skimage.transform.AffineTransform` + `warp` for rotation. |
| DET-04 | User can select which face to process by index when multiple faces detected | `face_index` INT input clamped to `[0, len(faces)-1]`. FACE_LANDMARKS from FaceDetect is a list of face dicts. |
| DET-05 | Node outputs cropped face image, alignment transform data, and face mask | Three outputs: IMAGE (cropped aligned face), ALIGN_DATA (dict with transform matrix, crop box, original size), MASK (from face oval polygon via `polygon2mask`). |
</phase_requirements>

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (configured in pyproject.toml) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/ -x -m "not slow"` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DET-02 | Crop face with configurable padding | unit | `python -m pytest tests/test_alignment.py::test_padded_crop_box -x` | No - Wave 0 |
| DET-02 | Padding=0 gives tight crop, padding=1 gives 2x expansion | unit | `python -m pytest tests/test_alignment.py::test_padding_range -x` | No - Wave 0 |
| DET-03 | Tilted face aligned to upright | unit | `python -m pytest tests/test_alignment.py::test_alignment_angle -x` | No - Wave 0 |
| DET-03 | Already-upright face unchanged | unit | `python -m pytest tests/test_alignment.py::test_zero_angle -x` | No - Wave 0 |
| DET-04 | face_index selects correct face | unit | `python -m pytest tests/test_face_crop.py::test_face_index_selection -x` | No - Wave 0 |
| DET-04 | Out-of-range index clamped gracefully | unit | `python -m pytest tests/test_face_crop.py::test_face_index_clamped -x` | No - Wave 0 |
| DET-05 | Node returns (IMAGE, ALIGN_DATA, MASK) | unit | `python -m pytest tests/test_face_crop.py::test_output_types -x` | No - Wave 0 |
| DET-05 | Mask shape matches cropped image | unit | `python -m pytest tests/test_face_mask.py::test_mask_shape -x` | No - Wave 0 |
| DET-05 | ALIGN_DATA contains required fields | unit | `python -m pytest tests/test_face_crop.py::test_align_data_fields -x` | No - Wave 0 |
| ALL | Full integration with real face image | integration (slow) | `python -m pytest tests/test_face_crop.py -m slow -v` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -m "not slow"`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_alignment.py` -- covers DET-02, DET-03 (alignment math unit tests)
- [ ] `tests/test_face_mask.py` -- covers DET-05 mask generation
- [ ] `tests/test_face_crop.py` -- covers DET-04, DET-05 node-level tests (add FaceCropAlign tests)
- [ ] `tests/conftest.py` -- add `mock_multi_face_landmarks` fixture (two faces for index testing)

*(Existing test infrastructure from Phase 1 covers pytest config and basic fixtures)*

## Sources

### Primary (HIGH confidence)
- [MediaPipe face_mesh_connections.py](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/python/solutions/face_mesh_connections.py) - FACEMESH_LEFT_EYE, FACEMESH_RIGHT_EYE, FACEMESH_FACE_OVAL landmark indices
- [scikit-image transform docs](https://scikit-image.org/docs/stable/api/skimage.transform.html) - AffineTransform class, warp function signatures and parameters
- [scikit-image draw docs](https://scikit-image.org/docs/stable/api/skimage.draw.html) - polygon2mask function for mask generation
- [MediaPipe face landmark indices gist](https://gist.github.com/Asadullah-Dal17/fd71c31bac74ee84e6a31af50fa62961) - Complete face region landmark index lists

### Secondary (MEDIUM confidence)
- [PyImageSearch face alignment](https://pyimagesearch.com/2017/05/22/face-alignment-with-opencv-and-python/) - Alignment algorithm pattern (arctan2 from eye positions, affine warp)
- [GeeksforGeeks face alignment](https://www.geeksforgeeks.org/computer-vision/python-opencv-getrotationmatrix2d-function/) - Rotation matrix formula verification

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - scikit-image and numpy are verified, already approved deps
- Architecture: HIGH - alignment math (arctan2 + affine transform) is well-established computer vision
- Pitfalls: HIGH - coordinate order and rotation direction issues are well-documented
- Landmark indices: HIGH - verified from official MediaPipe source file

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, no fast-moving deps)
