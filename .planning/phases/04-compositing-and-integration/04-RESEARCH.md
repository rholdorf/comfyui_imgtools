# Phase 4: Compositing and Integration - Research

**Researched:** 2026-03-10
**Domain:** Image compositing, affine inverse transforms, alpha blending (scikit-image)
**Confidence:** HIGH

## Summary

Phase 4 builds a FaceComposite node that reverses the crop/align transform from FaceCropAlign and alpha-blends the morphed face back into the original image using the warp_mask from FaceShapeMorph. The core technical challenge is the inverse affine transform -- placing a cropped, rotated face region back into its original position and orientation.

The existing codebase provides all necessary building blocks. `utils/alignment.py` uses `skimage.transform.AffineTransform` with `warp(inverse_map=transform.inverse)` for forward alignment. The reverse operation uses the same `warp()` function but passes `transform` directly (not `.inverse`) as the `inverse_map` parameter. The `align_data` dict from FaceCropAlign contains `transform_matrix` (3x3 ndarray), `crop_box` (x1,y1,x2,y2), and `original_size` (w,h) -- everything needed for reversal.

**Primary recommendation:** Composite in original image space. Place morphed face and warp_mask at crop_box position in full-size canvases, reverse-warp both using `AffineTransform(matrix=transform_matrix)` passed directly as `inverse_map`, then alpha blend with the original image.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use warp_mask from FaceShapeMorph as-is -- no additional feathering in the composite node
- Alpha blend per-pixel: `result = original * (1 - mask) + morphed * mask`
- No external mask input -- warp_mask is the only blending mask
- scikit-image only, no OpenCV (Poisson clone deferred to COMP-05 in v2)
- 4 inputs: `original_image` (IMAGE), `morphed_face` (IMAGE), `warp_mask` (MASK), `align_data` (ALIGN_DATA)
- 2 outputs: `composited_image` (IMAGE), `face_region_mask` (MASK)
- No blend opacity/strength parameter -- morph intensity controlled upstream
- Single image only (batch=1)
- Expand composite region slightly beyond crop_box to prevent rotation artifacts at edges
- Reconstruct inverse transform from align_data's transform_matrix -- no upstream changes needed
- On invalid/corrupted align_data (singular matrix, missing keys): return original image unmodified + empty mask

### Claude's Discretion
- Whether to blend in crop space or original image space (mask timing)
- Inverse transform reconstruction approach
- Exact crop region expansion amount for rotation safety
- Pixel diff tolerance metric for round-trip tests

### Deferred Ideas (OUT OF SCOPE)
- Poisson seamless blending option (cv2.seamlessClone) -- COMP-05 in v2
- Blend opacity slider on composite node
- External mask input (user-painted or from another node)
- Integration test with real MediaPipe detection
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 | Node composites morphed face back into original image | Reverse affine transform + crop_box placement pattern verified with scikit-image |
| COMP-02 | Feathered mask blending for smooth face-to-background transition | warp_mask from FaceShapeMorph already feathered; alpha blend formula confirmed |
| COMP-03 | Reverse alignment transform to match original face orientation | `warp(canvas, inverse_map=transform)` reverses `warp(img, inverse_map=transform.inverse)` |
| COMP-04 | Node outputs full composited image and face region mask | Alpha-blended result + reverse-transformed mask in original image space |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-image | (existing) | `AffineTransform`, `warp()` for inverse transform | Already used in alignment.py; project constraint |
| numpy | (existing) | Array operations, alpha blending | Already used everywhere |
| torch | (existing) | Tensor I/O for ComfyUI interface | Required by ComfyUI |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| skimage.draw.polygon2mask | (existing) | Generate face_region_mask in original space | For COMP-04 output |
| skimage.filters.gaussian | (existing) | Already used in morph_utils for feathering | Not needed here (mask comes pre-feathered) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Per-pixel alpha blend | cv2.seamlessClone (Poisson) | Better seam hiding but requires OpenCV; deferred to COMP-05 |

**Installation:**
No new dependencies required. All libraries already in use.

## Architecture Patterns

### Recommended Project Structure
```
comfyui_imgtools/
├── face_composite.py     # NEW: FaceComposite node class
├── face_morph.py          # Upstream: provides morphed_face, warp_mask, align_data
├── face_crop.py           # Upstream: provides align_data format
├── utils/
│   ├── alignment.py       # Reuse: AffineTransform, warp patterns
│   └── face_mask.py       # Reuse: generate_face_mask for face_region_mask output
└── tests/
    └── test_face_composite.py  # NEW: composite node tests
```

### Pattern 1: Reverse Transform via warp()
**What:** The forward alignment uses `warp(img, inverse_map=transform.inverse)`. To reverse, pass `transform` itself (not `.inverse`) as `inverse_map`.
**When to use:** Reversing the crop/align operation to place face back in original orientation.
**Example:**
```python
# Source: verified experimentally with skimage.transform.warp
from skimage.transform import AffineTransform, warp

# Reconstruct transform from align_data
transform = AffineTransform(matrix=align_data["transform_matrix"])

# Forward (in FaceCropAlign):
# aligned = warp(img, inverse_map=transform.inverse, ...)

# Reverse (in FaceComposite):
# Pass transform directly -- warp's inverse_map parameter means
# "given output coord, map to input coord". transform maps original->aligned,
# so it maps output(original) -> input(aligned), which is exactly what we want.
reversed_img = warp(canvas, inverse_map=transform, output_shape=(orig_h, orig_w),
                    order=1, mode="constant", cval=0.0, preserve_range=True)
```

### Pattern 2: Canvas Placement + Reverse Transform
**What:** Place crop-space content into a full-size aligned-space canvas at crop_box, then reverse-transform.
**When to use:** Mapping morphed face from crop space back to original image space.
**Example:**
```python
# Place morphed face at crop_box position in full-size canvas
orig_w, orig_h = align_data["original_size"]
x1, y1, x2, y2 = align_data["crop_box"]

canvas = np.zeros((orig_h, orig_w, 3), dtype=np.float64)
canvas[y1:y2, x1:x2] = morphed_face_np

mask_canvas = np.zeros((orig_h, orig_w), dtype=np.float64)
mask_canvas[y1:y2, x1:x2] = warp_mask_np

# Reverse-transform both
transform = AffineTransform(matrix=align_data["transform_matrix"])
reversed_face = warp(canvas, inverse_map=transform, output_shape=(orig_h, orig_w), ...)
reversed_mask = warp(mask_canvas, inverse_map=transform, output_shape=(orig_h, orig_w), ...)

# Alpha blend
result = original * (1 - reversed_mask[..., None]) + reversed_face * reversed_mask[..., None]
```

### Pattern 3: Graceful Degradation (_passthrough)
**What:** Return original image unmodified + empty mask when inputs are invalid.
**When to use:** Invalid align_data, singular transform matrix, dimension mismatches.
**Example:**
```python
# Matches face_morph.py:129 pattern
@staticmethod
def _passthrough(original_image, h, w):
    empty_mask = torch.zeros(1, h, w, dtype=torch.float32)
    return (original_image, empty_mask)
```

### Anti-Patterns to Avoid
- **Blending in crop space then reverse-transforming:** Blending must happen in original image space so the feathered mask edges align with the background properly.
- **Using transform.inverse for reverse warp:** The `inverse_map` parameter already inverts the mapping. Pass `transform` directly, not `transform.inverse`.
- **Ignoring dimension mismatches:** morphed_face dimensions must match crop_box dimensions (y2-y1, x2-x1). If they don't, return passthrough.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Inverse affine transform | Manual matrix inversion | `AffineTransform(matrix=params)` + pass as `inverse_map` to `warp()` | scikit-image handles interpolation, edge cases |
| Singular matrix detection | Manual determinant check | `try: AffineTransform(matrix=m).inverse` catches `LinAlgError` | Tested: skimage raises `LinAlgError` on singular matrices |
| Face region mask in original space | Manual polygon transformation | `generate_face_mask()` from `utils/face_mask.py` on reversed landmarks, OR reverse-transform the warp_mask | Already implemented and tested |

**Key insight:** The reverse transform is just `warp()` with different arguments, not a separate algorithm. The same function handles both directions.

## Common Pitfalls

### Pitfall 1: Wrong inverse_map Direction
**What goes wrong:** Using `transform.inverse` for reverse warp produces a double-inversion (applies forward transform again).
**Why it happens:** `warp()`'s `inverse_map` parameter name is confusing. It means "map from output coords to input coords."
**How to avoid:** For reverse warp, pass the original `transform` object directly. Forward used `transform.inverse` as inverse_map, so reverse uses `transform`.
**Warning signs:** Face appears rotated further instead of returning to upright position.

### Pitfall 2: Interpolation Loss on Round-Trip
**What goes wrong:** Double bilinear interpolation (forward warp + reverse warp) causes ~0.18 RMSE in face region even at strength=0.
**Why it happens:** Each warp step samples between pixels, losing sub-pixel information. Two warps compound the error.
**How to avoid:** Accept this as inherent. For round-trip tests, use a generous tolerance (RMSE < 0.05 for no-rotation, < 0.25 for rotated faces). The feathered mask blending hides most artifacts in practice.
**Warning signs:** Pixel-perfect round-trip tests failing on rotated faces.

### Pitfall 3: Crop Box Dimension Mismatch
**What goes wrong:** morphed_face dimensions don't match crop_box dimensions (e.g., FaceShapeMorph changed output size).
**Why it happens:** Upstream node could resize or the crop_box could be corrupted.
**How to avoid:** Validate `morphed_face.shape[1:3] == (y2-y1, x2-x1)` before placement. Return passthrough if mismatched.
**Warning signs:** IndexError or array shape mismatch when placing morphed face at crop_box.

### Pitfall 4: Edge Artifacts from Crop Boundary
**What goes wrong:** After reverse rotation, the edges of the crop region show hard lines where the crop box was.
**Why it happens:** Pixels at the crop boundary have zero-valued neighbors outside the box. Bilinear interpolation blends with zeros.
**How to avoid:** The feathered warp_mask from FaceShapeMorph already fades to zero before reaching crop edges (Gaussian sigma = 7% of face size). This naturally hides crop boundary artifacts. Additionally, expand the composite region slightly (5-10px) beyond crop_box to provide context for interpolation.
**Warning signs:** Visible rectangular outline around the face in the composited result.

### Pitfall 5: LinAlgError from Singular Transform Matrix
**What goes wrong:** `AffineTransform(matrix=corrupted_matrix).inverse` raises `numpy.linalg.LinAlgError`.
**Why it happens:** align_data could be corrupted or from a degenerate detection.
**How to avoid:** Wrap matrix reconstruction in try/except. On `LinAlgError` or missing keys, return passthrough.
**Warning signs:** Uncaught exception crashes the ComfyUI workflow.

## Code Examples

### FaceComposite Node Structure
```python
# Source: pattern from face_morph.py + alignment.py in this project
class FaceComposite:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "original_image": ("IMAGE",),
                "morphed_face": ("IMAGE",),
                "warp_mask": ("MASK",),
                "align_data": ("ALIGN_DATA",),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("composited_image", "face_region_mask")
    FUNCTION = "composite"
    CATEGORY = "imgtools/face"
```

### Inverse Transform + Alpha Blend
```python
# Source: verified experimentally with skimage 0.22+
from skimage.transform import AffineTransform, warp

def _reverse_and_blend(self, original_np, morphed_np, mask_np, align_data):
    orig_w, orig_h = align_data["original_size"]
    x1, y1, x2, y2 = align_data["crop_box"]

    # Expand crop region slightly for interpolation safety
    margin = 5
    ex1 = max(0, x1 - margin)
    ey1 = max(0, y1 - margin)
    ex2 = min(orig_w, x2 + margin)
    ey2 = min(orig_h, y2 + margin)

    # Place morphed face in full-size aligned-space canvas
    canvas = np.zeros((orig_h, orig_w, 3), dtype=np.float64)
    canvas[y1:y2, x1:x2] = morphed_np

    # Place mask in full-size canvas
    mask_canvas = np.zeros((orig_h, orig_w), dtype=np.float64)
    mask_canvas[y1:y2, x1:x2] = mask_np

    # Reconstruct and apply inverse transform
    transform = AffineTransform(matrix=align_data["transform_matrix"])
    reversed_face = warp(canvas, inverse_map=transform,
                         output_shape=(orig_h, orig_w),
                         order=1, mode="constant", cval=0.0,
                         preserve_range=True)
    reversed_mask = warp(mask_canvas, inverse_map=transform,
                         output_shape=(orig_h, orig_w),
                         order=1, mode="constant", cval=0.0,
                         preserve_range=True)

    # Alpha blend
    mask_3ch = reversed_mask[..., np.newaxis]
    result = original_np * (1 - mask_3ch) + reversed_face * mask_3ch

    return result, reversed_mask
```

### Graceful Degradation with Validation
```python
# Source: pattern from face_morph.py in this project
def composite(self, original_image, morphed_face, warp_mask, align_data):
    h, w = original_image.shape[1], original_image.shape[2]
    try:
        # Validate align_data keys
        required_keys = ["transform_matrix", "crop_box", "original_size"]
        if not all(k in align_data for k in required_keys):
            return self._passthrough(original_image, h, w)

        # Validate transform matrix is invertible
        transform = AffineTransform(matrix=align_data["transform_matrix"])
        _ = transform.inverse  # raises LinAlgError if singular

        # Validate dimensions
        x1, y1, x2, y2 = align_data["crop_box"]
        crop_h, crop_w = y2 - y1, x2 - x1
        if morphed_face.shape[1] != crop_h or morphed_face.shape[2] != crop_w:
            return self._passthrough(original_image, h, w)

        # ... proceed with compositing ...
    except (KeyError, ValueError, np.linalg.LinAlgError):
        return self._passthrough(original_image, h, w)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| cv2.warpAffine for transforms | skimage.transform.warp | Project constraint | No OpenCV dependency |
| cv2.seamlessClone for blending | Alpha blend with feathered mask | Deferred to v2 | Simpler, no cv2 needed |
| Manual matrix math for inverse | AffineTransform(matrix=params) | scikit-image built-in | Handles edge cases automatically |

## Open Questions

1. **Crop region expansion amount**
   - What we know: Experimental testing shows 5-10px margin provides interpolation context at crop boundaries.
   - What's unclear: Whether 5px or 10px is optimal. The feathered mask already handles most edge artifacts.
   - Recommendation: Use 5px. The warp_mask feathering (sigma = 7% of face) already fades to zero well before crop edges, so expansion is a secondary safety measure.

2. **Round-trip test tolerance**
   - What we know: No-rotation round-trip is exact (RMSE = 0.0). Rotated face round-trip has ~0.18 RMSE in face region due to double interpolation.
   - What's unclear: Whether to test the full pipeline or just the composite node in isolation.
   - Recommendation: Test composite node with identity transform (RMSE < 0.001), and separately test with rotation (RMSE < 0.25). Full pipeline test at strength=0 with no rotation should be near-exact.

3. **face_region_mask output generation**
   - What we know: Could either (a) reverse-transform the warp_mask and threshold it, or (b) use `generate_face_mask()` on reverse-transformed landmarks.
   - What's unclear: Which gives a more useful mask for downstream consumers.
   - Recommendation: Use the reverse-transformed warp_mask directly (already computed for alpha blending). It represents the actual blended region, which is more useful than a binary face oval.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_face_composite.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-01 | Composites morphed face at correct position | unit | `pytest tests/test_face_composite.py::TestCompositing -x` | No -- Wave 0 |
| COMP-02 | Feathered mask blending (smooth transitions) | unit | `pytest tests/test_face_composite.py::TestBlending -x` | No -- Wave 0 |
| COMP-03 | Reverse alignment transform | unit | `pytest tests/test_face_composite.py::TestReverseTransform -x` | No -- Wave 0 |
| COMP-04 | Outputs composited image + face_region_mask | unit | `pytest tests/test_face_composite.py::TestOutputs -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_face_composite.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_face_composite.py` -- covers COMP-01 through COMP-04
- [ ] Test fixtures: deterministic align_data with identity and rotated transforms, synthetic morphed face images, feathered mask arrays

*(No framework gaps -- pytest infrastructure already configured in pyproject.toml)*

## Sources

### Primary (HIGH confidence)
- `utils/alignment.py` -- AffineTransform usage, warp() with inverse_map pattern
- `face_crop.py` -- align_data dict structure (transform_matrix, crop_box, original_size)
- `face_morph.py` -- FaceShapeMorph output format, _passthrough pattern, warp_mask generation
- `utils/morph_utils.py` -- generate_feathered_mask implementation details
- Experimental verification -- tested `warp()` reverse transform, singular matrix handling, and round-trip RMSE in ComfyUI conda environment

### Secondary (MEDIUM confidence)
- scikit-image AffineTransform API -- `AffineTransform(matrix=params)` reconstruction, `.inverse` property behavior, `LinAlgError` on singular matrices (verified experimentally)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed, all patterns verified in existing code
- Architecture: HIGH -- reverse transform approach verified experimentally with measured RMSE
- Pitfalls: HIGH -- each pitfall verified through experimentation or code inspection

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, no moving targets)
