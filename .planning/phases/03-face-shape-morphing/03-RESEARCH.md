# Phase 3: Face Shape Morphing - Research

**Researched:** 2026-03-10
**Domain:** Thin-Plate Spline image warping, MediaPipe landmark subsetting, ComfyUI node design
**Confidence:** HIGH

## Summary

Phase 3 implements a FaceShapeMorph ComfyUI node that warps a source face to match a target face's proportions using Thin-Plate Spline (TPS) warping. The core technical approach is well-supported: scikit-image 0.24.0 (the installed version) provides `ThinPlateSplineTransform` with a working `estimate(dst, src)` + `warp()` pipeline. Benchmarks show ~170ms for TPS estimation and ~550ms for warping a 512x512 image with 77 control points -- acceptable for a ComfyUI node.

The main implementation tasks are: (1) updating FaceCropAlign to output crop-space landmarks, (2) selecting ~60-67 control points from MediaPipe's 478 landmarks spanning face oval, eye corners, eyebrow endpoints, nose outline, and lip contour, (3) normalizing landmarks by inter-eye distance before computing the warp displacement, and (4) generating a feathered warp mask using `skimage.filters.gaussian`.

**Primary recommendation:** Use `skimage.transform.ThinPlateSplineTransform.estimate()` with ~67 face landmark control points plus ~12 boundary anchor points. Normalize by inter-eye distance for proportional matching. Keep implementation in a single `face_morph.py` file with helpers in `utils/morph_utils.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Both source and target go through FaceCropAlign first -- morph node takes two cropped face IMAGEs + two FACE_LANDMARKS + source ALIGN_DATA
- FaceCropAlign needs a new output: single-face landmarks transformed to crop space (so morph node doesn't need face_index selection)
- ALIGN_DATA passes through the morph node as an output for Phase 4 compositing
- Only parameter beyond the inputs: strength FLOAT slider -- no extra toggles or region controls for v1
- Full proportional match -- contour AND internal feature positions move to match target
- Features shift position/spacing to match target proportions, but each feature's internal shape stays coherent
- Strength slider controls how far all points move: 0.0 = source, 0.5 = halfway, 1.0 = full target proportions
- Linear interpolation: `morphed_pt = source_pt + strength * (target_pt - source_pt)`
- Strength capped at 0.0-1.0, no overshoot
- Warp mask output is soft/feathered (Gaussian-blurred edges, ~5-10% of face size), not binary
- Normalize both landmark sets by inter-eye distance before computing warp
- On invalid/missing landmarks or TPS failure: return source face unmodified + full-face mask + align_data passthrough
- Add corner/edge anchor points (4 corners + ~4-8 edge midpoints) to prevent TPS from distorting crop borders

### Claude's Discretion
- Debug/visualization output (warp grid overlay or similar)
- Exact control point subset selection (~60 from 478 landmarks)
- Whether to resize output canvas or keep source crop dimensions
- TPS implementation approach (scipy RBF, custom, etc.)

### Deferred Ideas (OUT OF SCOPE)
- Region-selective morphing weights (jaw, forehead, cheeks individually) -- MORPH-06 in v2
- Landmark debug visualization overlay -- MORPH-07 in v2
- Overshoot/exaggeration (strength > 1.0) -- potential v2 feature
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MORPH-01 | Node warps source face shape to match target face proportions using TPS | ThinPlateSplineTransform API verified working in skimage 0.24.0; estimate(dst, src) + warp() pipeline |
| MORPH-02 | Strength parameter (0.0-1.0) controls morph intensity | Linear interpolation of control points before TPS estimation; trivial math |
| MORPH-03 | Node uses ~60 face contour landmarks (not all 478) for efficient warping | 67 control points identified: 36 oval + 4 eye corners + 6 eyebrow + 8 nose + 13 lip |
| MORPH-04 | Interior facial features (eyes, nose, mouth) are anchored to prevent distortion | Internal feature points included as control points that move coherently; TPS smoothness preserves local structure |
| MORPH-05 | Node outputs morphed face image and warp mask | warp() returns warped image; generate_face_mask() + gaussian() creates feathered mask |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-image | 0.24.0 | TPS warping + Gaussian blur | Already installed; project constraint (no OpenCV) |
| numpy | (installed) | Landmark math, interpolation | Already used throughout project |
| torch | (installed) | ComfyUI tensor I/O | Required for ComfyUI nodes |

### Key APIs
| API | Module | Purpose |
|-----|--------|---------|
| `ThinPlateSplineTransform` | `skimage.transform` | Non-linear TPS warp estimation |
| `warp()` | `skimage.transform` | Apply TPS transform to image |
| `gaussian()` | `skimage.filters` | Feather mask edges |
| `polygon2mask()` | `skimage.draw` | Already used for face mask generation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| skimage TPS | scipy.interpolate.RBFInterpolator | More flexible but requires manual image warping loop; skimage integrates with warp() natively |
| skimage TPS | Custom TPS implementation | No benefit; skimage handles the linear algebra correctly |
| skimage gaussian | scipy.ndimage.gaussian_filter | Either works; skimage already imported |

## Architecture Patterns

### Recommended Project Structure
```
comfyui_imgtools/
├── face_morph.py           # FaceShapeMorph node (new)
├── face_crop.py            # FaceCropAlign node (modified - add landmark output)
├── face_detection.py       # FaceDetect node (unchanged)
├── utils/
│   ├── morph_utils.py      # Control point selection, normalization, TPS helpers (new)
│   ├── face_mask.py        # FACE_OVAL_INDICES, generate_face_mask() (existing)
│   ├── alignment.py        # compute_eye_centers(), etc. (existing)
│   └── landmarks.py        # extract_landmarks() (existing)
└── __init__.py             # Register FaceShapeMorph (modified)
```

### Pattern 1: Control Point Selection
**What:** Extract a curated subset of ~67 landmark indices from the full 478 for TPS warping
**When to use:** Always -- using all 478 would be expensive and over-determined
**Recommended indices (67 total):**

| Region | Count | Indices |
|--------|-------|---------|
| Face oval | 36 | `FACE_OVAL_INDICES` (already defined in face_mask.py) |
| Eye corners | 4 | 33, 133 (right inner/outer), 362, 263 (left inner/outer) |
| Eyebrow endpoints | 6 | 46, 55, 107 (right), 276, 285, 336 (left) |
| Nose outline | 8 | 1, 4, 5, 48, 115, 220, 275, 440 |
| Lip contour | 13 | 0, 13, 14, 17, 61, 78, 82, 87, 267, 291, 308, 312, 317 |

Plus ~12 boundary anchor points (4 corners + 8 edge midpoints) that map to themselves.

**Example:**
```python
# Source: MediaPipe face_mesh_connections verified indices
MORPH_CONTROL_INDICES = sorted(set(
    FACE_OVAL_INDICES +  # 36 contour
    [33, 133, 362, 263] +  # eye corners
    [46, 55, 107, 276, 285, 336] +  # eyebrow key points
    [1, 4, 5, 48, 115, 220, 275, 440] +  # nose outline
    [0, 13, 14, 17, 61, 78, 82, 87, 267, 291, 308, 312, 317]  # lip contour
))
# Total: 67 unique indices
```

### Pattern 2: Inter-Eye Distance Normalization
**What:** Scale both source and target landmarks so inter-eye distance = 1.0 before computing displacement
**When to use:** Always -- ensures proportional transfer regardless of face size
**Example:**
```python
def normalize_landmarks(landmarks_px, eye_centers):
    left_eye, right_eye = eye_centers
    ied = np.linalg.norm(left_eye - right_eye)
    if ied < 1e-6:
        return landmarks_px, 1.0  # fallback
    center = (left_eye + right_eye) / 2.0
    normalized = (landmarks_px - center) / ied
    return normalized, ied
```

### Pattern 3: TPS Warp Pipeline
**What:** Full pipeline from landmarks to warped image
**When to use:** Core morph operation
**Example:**
```python
from skimage.transform import ThinPlateSplineTransform, warp

def compute_morph_warp(source_lms, target_lms, strength, img_shape):
    # 1. Select control points
    src_pts = source_lms[MORPH_CONTROL_INDICES]
    tgt_pts = target_lms[MORPH_CONTROL_INDICES]

    # 2. Normalize by inter-eye distance
    src_norm, src_ied = normalize_landmarks(src_pts, compute_eye_centers(source_lms))
    tgt_norm, tgt_ied = normalize_landmarks(tgt_pts, compute_eye_centers(target_lms))

    # 3. Interpolate by strength (in normalized space)
    morphed_norm = src_norm + strength * (tgt_norm - src_norm)

    # 4. Denormalize back to source pixel space
    left_eye, right_eye = compute_eye_centers(source_lms)
    center = (left_eye + right_eye) / 2.0
    morphed_px = morphed_norm * src_ied + center

    # 5. Add boundary anchors (map to themselves)
    h, w = img_shape[:2]
    anchors = _get_boundary_anchors(w, h)
    src_with_anchors = np.vstack([src_pts, anchors])
    dst_with_anchors = np.vstack([morphed_px, anchors])

    # 6. Estimate TPS (note: dst, src order for warp's inverse convention)
    tps = ThinPlateSplineTransform()
    tps.estimate(dst_with_anchors, src_with_anchors)

    return tps
```

### Pattern 4: Feathered Warp Mask
**What:** Generate a soft mask indicating the warped face region
**When to use:** Always -- Phase 4 compositing needs this
**Example:**
```python
from skimage.filters import gaussian

def generate_feathered_mask(landmarks_px, img_h, img_w):
    # Binary mask from face oval
    mask = generate_face_mask(landmarks_px, img_h, img_w)
    # Feather edges: sigma = ~5-10% of face height
    face_size = max(img_h, img_w)
    sigma = face_size * 0.07  # 7% of face size
    feathered = gaussian(mask, sigma=sigma)
    return feathered.astype(np.float32)
```

### Pattern 5: Graceful Degradation
**What:** Return source image unmodified on any error
**When to use:** On invalid landmarks, TPS failure, or any exception
**Example:**
```python
try:
    # ... morph logic ...
except Exception:
    # Return source unmodified + full face mask + passthrough align_data
    return (source_image, align_data, full_face_mask)
```

### Anti-Patterns to Avoid
- **Using all 478 landmarks as control points:** Over-determined TPS, slow (~4x), can produce artifacts from noisy interior points
- **Not adding boundary anchors:** TPS will distort the image edges/corners, producing black triangles
- **Comparing landmarks in absolute pixel space without normalization:** Would transfer size differences, not proportions
- **Using `tps.inverse`:** NotImplementedError in skimage 0.24.0 -- not supported for TPS

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TPS warping | Custom TPS solver | `skimage.transform.ThinPlateSplineTransform` | Handles kernel computation, linear algebra, numerical stability |
| Image warping | Per-pixel coordinate mapping loop | `skimage.transform.warp()` | Handles interpolation, boundary modes, multi-channel |
| Mask feathering | Custom distance transform + falloff | `skimage.filters.gaussian()` on binary mask | Simple, correct, one line |
| Face mask polygon | Custom polygon fill | `skimage.draw.polygon2mask()` | Already used in project |

**Key insight:** The entire TPS pipeline (estimate + warp) is 2 function calls in scikit-image. The implementation complexity is in the landmark wrangling, not the math.

## Common Pitfalls

### Pitfall 1: TPS estimate() argument order
**What goes wrong:** `estimate(src, dst)` instead of `estimate(dst, src)` causes the warp to go in the wrong direction
**Why it happens:** `warp()` applies the inverse transform, so TPS must map from destination to source space
**How to avoid:** Always call `tps.estimate(dst, src)` -- "where each destination pixel came from in the source"
**Warning signs:** Face shape changes in the opposite direction (gets more different instead of more similar)

### Pitfall 2: Missing boundary anchors
**What goes wrong:** TPS extrapolation distorts corners/edges of the crop, creating black regions or stretching
**Why it happens:** TPS has no constraint on behavior outside the convex hull of control points
**How to avoid:** Add 4 corner points + 8 edge midpoints that map to themselves (identity anchors)
**Warning signs:** Black triangles in corners, stretched edges in output

### Pitfall 3: Size-dependent landmark comparison
**What goes wrong:** Morphing transfers absolute size differences rather than shape proportions
**Why it happens:** Comparing pixel coordinates directly when source/target crops are different sizes
**How to avoid:** Normalize both landmark sets by inter-eye distance, compute displacement in normalized space, then denormalize back to source pixel space
**Warning signs:** Face appears to shrink or grow rather than change shape

### Pitfall 4: TPS with too many control points
**What goes wrong:** Slow computation, potential numerical instability with near-colinear points
**Why it happens:** Using all 478 landmarks or too many densely-packed points in one region
**How to avoid:** Use curated ~67 points spread across face regions; benchmark shows 77 points = ~715ms total
**Warning signs:** Warp takes >2 seconds, or produces wavy artifacts near dense point clusters

### Pitfall 5: Not handling TPS estimation failure
**What goes wrong:** `np.linalg.solve` can fail with singular matrices if control points are degenerate
**Why it happens:** Near-duplicate points, all points colinear, or very few points
**How to avoid:** Wrap TPS estimation in try/except; if `estimate()` returns False, fall back to source passthrough
**Warning signs:** LinAlgError exceptions, `estimate()` returning False

### Pitfall 6: Forgetting to warp the mask
**What goes wrong:** Mask doesn't align with the warped face
**Why it happens:** Generating mask from source landmarks then applying warp only to the image
**How to avoid:** Generate the feathered mask from the morphed (interpolated) landmark positions, not the original source landmarks. The mask should represent where the morphed face IS, not where the source face WAS
**Warning signs:** Mask edges don't follow the morphed face contour

## Code Examples

### FaceCropAlign Update -- Adding Crop-Space Landmarks Output
```python
# In face_crop.py, update RETURN_TYPES and crop_and_align:
RETURN_TYPES = ("IMAGE", "ALIGN_DATA", "MASK", "FACE_LANDMARKS")
RETURN_NAMES = ("cropped_face", "align_data", "face_mask", "crop_landmarks")

# In crop_and_align(), after computing crop_landmarks (already done at line 74-76):
# Package as single-face list matching FACE_LANDMARKS format
crop_landmarks_out = [{
    "landmarks": crop_landmarks,
    "landmarks_3d": landmarks[idx].get("landmarks_3d", np.zeros((478, 3))),
}]

return (cropped_tensor, align_data, mask_tensor, crop_landmarks_out)
```

### FaceShapeMorph Node Structure
```python
class FaceShapeMorph:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_image": ("IMAGE",),
                "target_image": ("IMAGE",),
                "source_landmarks": ("FACE_LANDMARKS",),
                "target_landmarks": ("FACE_LANDMARKS",),
                "source_align_data": ("ALIGN_DATA",),
                "strength": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "ALIGN_DATA")
    RETURN_NAMES = ("morphed_face", "warp_mask", "align_data")
    FUNCTION = "morph"
    CATEGORY = "imgtools/face"
```

### TPS Warp with Boundary Anchors
```python
def _get_boundary_anchors(width, height):
    """Generate boundary anchor points: 4 corners + 8 edge midpoints."""
    w, h = width - 1, height - 1
    return np.array([
        [0, 0], [w, 0], [0, h], [w, h],           # corners
        [w/2, 0], [w/2, h], [0, h/2], [w, h/2],   # edge midpoints
        [w/4, 0], [3*w/4, 0], [0, h/4], [0, 3*h/4],  # quarter points
    ], dtype=np.float64)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ThinPlateSplineTransform()` then `.estimate()` | `ThinPlateSplineTransform.from_estimate()` | skimage 0.26.0 (Dec 2025) | Project uses 0.24.0, so use old API |
| scipy.interpolate.Rbf (thin-plate) | scipy.interpolate.RBFInterpolator | scipy 1.7+ | Not relevant -- use skimage TPS directly |

**Version note:** The project uses scikit-image 0.24.0. The `estimate()` instance method is the correct API. Do NOT use `from_estimate()` class method (added in 0.26.0).

## Open Questions

1. **Canvas resizing vs. keeping source dimensions**
   - What we know: The morph shifts face shape, potentially pushing content near crop edges
   - What's unclear: Whether keeping source crop dimensions could clip morphed content
   - Recommendation: Keep source crop dimensions. The padding in FaceCropAlign (default 30%) provides buffer. Phase 4 compositing is simpler with matching dimensions.

2. **Debug visualization output**
   - What we know: Context.md lists this as Claude's discretion
   - Recommendation: Skip for v1. Add a simple warp grid overlay as a future enhancement (MORPH-07 is deferred anyway). Keep the node focused on its core job.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed, configured in pyproject.toml) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `conda run -n comfyui pytest tests/test_face_morph.py -x` |
| Full suite command | `conda run -n comfyui pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MORPH-01 | TPS warp transforms source face toward target | unit | `conda run -n comfyui pytest tests/test_face_morph.py::TestMorphWarp -x` | Wave 0 |
| MORPH-02 | Strength 0.0 = no change, 1.0 = full morph, 0.5 = halfway | unit | `conda run -n comfyui pytest tests/test_face_morph.py::TestStrength -x` | Wave 0 |
| MORPH-03 | Uses ~67 control points (not all 478) | unit | `conda run -n comfyui pytest tests/test_morph_utils.py::TestControlPoints -x` | Wave 0 |
| MORPH-04 | Interior features anchored (eyes/nose/mouth move coherently) | unit | `conda run -n comfyui pytest tests/test_face_morph.py::TestFeatureCoherence -x` | Wave 0 |
| MORPH-05 | Outputs morphed image + feathered warp mask | unit | `conda run -n comfyui pytest tests/test_face_morph.py::TestOutputs -x` | Wave 0 |
| N/A | FaceCropAlign outputs crop-space landmarks | unit | `conda run -n comfyui pytest tests/test_face_crop.py::TestCropLandmarks -x` | Wave 0 |
| N/A | Graceful degradation on bad input | unit | `conda run -n comfyui pytest tests/test_face_morph.py::TestGracefulDegradation -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `conda run -n comfyui pytest tests/test_face_morph.py tests/test_morph_utils.py -x`
- **Per wave merge:** `conda run -n comfyui pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_face_morph.py` -- covers MORPH-01, MORPH-02, MORPH-04, MORPH-05, graceful degradation
- [ ] `tests/test_morph_utils.py` -- covers MORPH-03 (control point selection, normalization, boundary anchors)
- [ ] Update `tests/test_face_crop.py` -- add tests for new crop-space landmarks output

## Sources

### Primary (HIGH confidence)
- scikit-image 0.24.0 installed version -- TPS API verified working via live test in conda env
- MediaPipe face_mesh_connections -- landmark indices extracted from installed package
- Existing codebase -- face_crop.py, face_mask.py, alignment.py patterns

### Secondary (MEDIUM confidence)
- [scikit-image TPS example (0.24.x)](https://scikit-image.org/docs/0.24.x/auto_examples/transform/plot_tps_deformation.html) -- API usage patterns
- [scikit-image TPS source (v0.25.0)](https://github.com/scikit-image/scikit-image/blob/v0.25.0/skimage/transform/_thin_plate_splines.py) -- internal behavior (estimate needs min 3 points, no inverse support)
- [scikit-image 0.26.0 release notes](https://scikit-image.org/docs/stable/release_notes/release_0.26.html) -- confirmed from_estimate is 0.26+ only

### Tertiary (LOW confidence)
- None -- all key claims verified against installed packages or official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- scikit-image TPS tested live in project's conda env
- Architecture: HIGH -- follows established project patterns, landmark indices verified from installed MediaPipe
- Pitfalls: HIGH -- TPS argument order and boundary anchor issues verified through testing
- Control points: MEDIUM -- 67-point selection is well-reasoned but optimal subset is somewhat subjective

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable libraries, unlikely to change)
