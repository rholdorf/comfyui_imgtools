# Phase 8: FaceModelMorph Node - Research

**Researched:** 2026-03-11
**Domain:** ComfyUI node implementation — pose-aware face model morphing with TPS warp
**Confidence:** HIGH

## Summary

FaceModelMorph is a new ComfyUI node that replaces the target_image/target_landmarks pair of FaceShapeMorph with a pre-built FACE_MODEL dict. The core algorithmic challenge is **denormalization**: converting the model's IPD-normalized canonical landmarks into a pixel-space delta that can be applied to the source face via TPS warp. The user has locked the denormalization strategy (frontalize source 3D landmarks, normalize by IPD, compute delta in normalized space, scale delta back by source IED, apply to pixel landmarks) with a Procrustes fallback when pose data is unavailable.

All infrastructure exists: `pose_utils.py` provides frontalization and normalization, `morph_utils.py` provides TPS warp computation (`compute_morph_warp` pattern), delta symmetrization, boundary anchors, and feathered mask generation. The node follows the exact same output contract as `FaceShapeMorph` (IMAGE, MASK, ALIGN_DATA) for drop-in replacement.

**Primary recommendation:** Build a single `face_model_morph.py` module containing the `FaceModelMorph` class, with the pose-aware delta computation as a utility function (either inline or in `morph_utils.py`). Reuse `_symmetrize_delta`, `_get_boundary_anchors`, `generate_feathered_mask`, and the TPS warp pattern from `compute_morph_warp` but **do not call** `compute_morph_warp` directly (the delta computation pipeline is fundamentally different).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Pose attenuation curve:** `effective_strength = user_strength * cos(yaw) * cos(pitch)` — same formula as model building weights. No floor. If source face has pose=None, apply full strength with no attenuation.
- **Node input design:** Required: source_image (IMAGE), face_model (FACE_MODEL), source_landmarks (FACE_LANDMARKS), source_align_data (ALIGN_DATA), strength (FLOAT 0.0-1.0, default 0.5, step 0.05). Optional: symmetrize (BOOLEAN, default False). No target_image input. No file path alternative. Require external landmarks from FaceDetect.
- **Denormalization strategy:** Normalize source to model space (not denormalize model to pixel). Pipeline: frontalize source 3D landmarks -> normalize by IPD -> compute delta in normalized space -> scale delta back to pixels by source IED -> apply to original pixel landmarks. Fallback (no pose data): use Procrustes alignment between model 2D and source 2D pixel coords. Always apply `_symmetrize_delta()` on pixel-space delta.
- **Strength and attenuation interaction:** Multiply: effective = user_strength * cos(yaw) * cos(pitch). Head scale from model head_dimensions vs source head dimensions (IPD-normalized). head_scale passed through align_data["head_scale"].
- **MRPH-03 symmetrize toggle:** Forces model to bilateral symmetry BEFORE delta computation; `_symmetrize_delta` cleans residual asymmetry AFTER. Two separate symmetrization concerns.
- **Drop-in replacement:** Same RETURN_TYPES (IMAGE, MASK, ALIGN_DATA), same RETURN_NAMES, same strength defaults as FaceShapeMorph.

### Claude's Discretion
- Internal function decomposition (single module vs separate morph util functions)
- Exact eye center computation method for source IED measurement
- How to handle edge cases within the warp (degenerate landmarks, near-zero IED)
- Whether to reuse `compute_morph_warp` or write a new model-specific warp function
- TPS boundary anchor placement (reuse existing `_get_boundary_anchors`)

### Deferred Ideas (OUT OF SCOPE)
- LoadFaceModel node (load .facemodel.npz from disk path) — future
- Effective strength output for debugging — future optional output
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MRPH-01 | User can apply a face model to a source image via FaceModelMorph node using pose-aware delta and TPS warp | Full pipeline documented: frontalize -> normalize -> delta -> scale -> TPS warp. All building blocks exist in pose_utils.py and morph_utils.py. New: delta computation logic and node class. |
| MRPH-02 | FaceModelMorph passes head dimensions from model to FaceComposite for correct scaling | Pattern established in FaceShapeMorph: `out_align_data["head_scale"] = float(head_scale)`. Model provides head_dimensions dict; source head dims computed via `compute_head_dimensions()`. |
| MRPH-03 | FaceModelMorph exposes a symmetrize toggle (default off) for the canonical model | Model's canonical_landmarks (478,2) symmetrized using mirror pairs from `_MORPH_MIRROR_PAIRS` before delta computation. Separate from `_symmetrize_delta` on the output delta. |
| POSE-04 | FaceModelMorph auto-attenuates morph strength for source faces with high yaw | `effective_strength = user_strength * cos(yaw) * cos(pitch)` using source face pose dict. Fallback: full strength if pose=None. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | (existing) | Landmark math, delta computation, array ops | Already used throughout |
| torch | (existing) | ComfyUI tensor I/O | Required for IMAGE/MASK types |
| scikit-image | (existing) | TPS warp (`ThinPlateSplineTransform`, `warp`) | Project constraint: no OpenCV |
| scipy | (existing) | `Rotation` class in pose_utils | Transitive dep via scikit-image |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| math | stdlib | `cos`, `radians` for pose attenuation | Attenuation calculation |

No new dependencies required.

## Architecture Patterns

### Recommended Project Structure
```
comfyui_imgtools/
├── face_model_morph.py     # NEW: FaceModelMorph node class
├── face_morph.py           # EXISTING: FaceShapeMorph (reference)
├── face_model_builder.py   # EXISTING: produces FACE_MODEL
├── __init__.py             # MODIFY: register FaceModelMorph
├── utils/
│   ├── morph_utils.py      # EXISTING: reuse TPS helpers
│   ├── pose_utils.py       # EXISTING: frontalize, normalize, head_dims
│   └── alignment.py        # EXISTING: compute_eye_centers for IED
└── tests/
    └── test_face_model_morph.py  # NEW: node + pipeline tests
```

### Pattern 1: Pose-Aware Delta Computation (Primary Path)
**What:** When source face has pose data (3D landmarks + transformation matrix), compute shape delta in IPD-normalized space.
**When to use:** Source face has `pose` dict with `matrix` key and `landmarks_3d` available.
**Pipeline:**
```python
# 1. Frontalize source 3D landmarks
src_front = frontalize_landmarks(src_3d, pose["matrix"])

# 2. Normalize by IPD (source)
src_norm, src_ipd = normalize_landmarks_3d(src_front)

# 3. Project to 2D for comparison with model
src_norm_2d = src_norm[:, :2]  # (478, 2)

# 4. Extract control points
model_ctrl = model_canonical[MORPH_CONTROL_INDICES]   # (42, 2)
src_ctrl = src_norm_2d[MORPH_CONTROL_INDICES]          # (42, 2)

# 5. Delta in normalized space
norm_delta = model_ctrl - src_ctrl  # (42, 2)

# 6. Scale delta back to pixel space using source IED
src_eye_centers = compute_eye_centers(src_lms_px)
src_ied = np.linalg.norm(src_eye_centers[0] - src_eye_centers[1])
px_delta = norm_delta * src_ied  # (42, 2)

# 7. Apply to pixel-space source control points
src_ctrl_px = src_lms_px[MORPH_CONTROL_INDICES]
# 8. Symmetrize delta
px_delta = _symmetrize_delta(px_delta, src_ctrl_px)

# 9. Attenuate by pose
effective_strength = strength * math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))
morphed_ctrl = src_ctrl_px + effective_strength * px_delta
```

### Pattern 2: Procrustes Fallback (No Pose Data)
**What:** When source face lacks pose data, use Procrustes alignment between model 2D and source 2D pixel coordinates.
**When to use:** Source face has `pose=None`.
**Pipeline:**
```python
# Use existing procrustes_align to align model control points to source
model_ctrl = model_canonical[MORPH_CONTROL_INDICES]
src_ctrl_px = src_lms_px[MORPH_CONTROL_INDICES]

# Need to scale model to source pixel space first via IED
src_eye_centers = compute_eye_centers(src_lms_px)
src_ied = np.linalg.norm(src_eye_centers[0] - src_eye_centers[1])

# Scale + translate model to approximate source position
model_scaled = model_ctrl * src_ied + src_eye_midpoint

# Procrustes align (removes rotation, normalizes scale)
aligned_model, scale_ratio = procrustes_align(src_ctrl_px, model_scaled)

# Delta and symmetrize
delta = aligned_model - src_ctrl_px
delta = _symmetrize_delta(delta, src_ctrl_px)
morphed_ctrl = src_ctrl_px + strength * delta  # full strength, no attenuation
```

### Pattern 3: Model Symmetrization (MRPH-03)
**What:** Force canonical model landmarks to bilateral symmetry before delta computation.
**When to use:** User toggles `symmetrize=True`.
**Implementation:**
```python
def _symmetrize_model(canonical_2d):
    """Force canonical landmarks to bilateral symmetry.

    For each mirror pair, average their X-distances from midline
    and Y positions. For midline points, zero X offset from center.
    """
    sym = canonical_2d.copy()
    # Use same _MORPH_MIRROR_PAIRS and _MORPH_MIDLINE_INDICES
    ctrl_pos = {lm_id: lm_id for lm_id in range(478)}  # direct index

    # Compute midline X from midline landmarks
    midline_x = np.mean([sym[idx, 0] for idx in _MORPH_MIDLINE_INDICES])

    for lm_a, lm_b in _MORPH_MIRROR_PAIRS:
        # Average distance from midline
        dist_a = abs(sym[lm_a, 0] - midline_x)
        dist_b = abs(sym[lm_b, 0] - midline_x)
        avg_dist = (dist_a + dist_b) / 2

        # Assign: left of midline gets -avg_dist, right gets +avg_dist
        if sym[lm_a, 0] < sym[lm_b, 0]:
            sym[lm_a, 0] = midline_x - avg_dist
            sym[lm_b, 0] = midline_x + avg_dist
        else:
            sym[lm_a, 0] = midline_x + avg_dist
            sym[lm_b, 0] = midline_x - avg_dist

        # Average Y
        avg_y = (sym[lm_a, 1] + sym[lm_b, 1]) / 2
        sym[lm_a, 1] = avg_y
        sym[lm_b, 1] = avg_y

    # Midline points: snap to midline X
    for idx in _MORPH_MIDLINE_INDICES:
        sym[idx, 0] = midline_x

    return sym
```

**Note:** The mirror pairs in `_MORPH_MIRROR_PAIRS` are indexed by landmark ID, not by control point index. Model symmetrization should operate on all 478 landmarks (or at least the control indices), so the pairs map directly.

### Pattern 4: Head Scale Computation
**What:** Compute head_scale from model vs source head dimensions.
**Implementation:**
```python
# Source head dimensions (from source 3D landmarks)
src_head_dims = compute_head_dimensions(src_3d, src_ipd)

# Model head dimensions (from FACE_MODEL dict)
model_head_dims = face_model["head_dimensions"]

# Scale ratio (model / source) — use width as primary metric
head_scale_raw = model_head_dims["width"] / src_head_dims["width"]

# Interpolate by effective_strength
head_scale = 1.0 + effective_strength * (head_scale_raw - 1.0)
```

### Pattern 5: Node Structure (Follow FaceShapeMorph)
**What:** ComfyUI node class with identical output contract.
```python
class FaceModelMorph:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_image": ("IMAGE",),
                "face_model": ("FACE_MODEL",),
                "source_landmarks": ("FACE_LANDMARKS",),
                "source_align_data": ("ALIGN_DATA",),
                "strength": ("FLOAT", {
                    "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05,
                }),
            },
            "optional": {
                "symmetrize": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "ALIGN_DATA")
    RETURN_NAMES = ("morphed_face", "warp_mask", "align_data")
    FUNCTION = "morph"
    CATEGORY = "imgtools/face"
```

### Anti-Patterns to Avoid
- **Calling compute_morph_warp directly:** The existing function assumes two sets of pixel landmarks and uses Procrustes internally. The model morph pipeline is fundamentally different (normalized space delta). Write a new warp function.
- **Denormalizing model to pixel space:** The user explicitly locked "normalize source to model space" — do NOT scale model landmarks to pixel coordinates.
- **Applying attenuation as a floor:** User specified no floor; let cosine go to near-zero.
- **Adding extra outputs:** Keep (IMAGE, MASK, ALIGN_DATA) — no effective_strength output.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TPS warp estimation | Custom spline solver | `ThinPlateSplineTransform` from scikit-image | Numerical stability, boundary handling |
| 3D landmark frontalization | Manual rotation matrix math | `frontalize_landmarks()` from pose_utils | Already tested, handles scale removal |
| IPD normalization | Custom centering/scaling | `normalize_landmarks_3d()` from pose_utils | Handles degenerate IPD edge case |
| Delta symmetrization | New symmetrization logic | `_symmetrize_delta()` from morph_utils | Already handles mirror pairs and midline |
| Boundary anchors | Custom edge pinning | `_get_boundary_anchors()` from morph_utils | Tested, prevents TPS edge distortion |
| Feathered mask | Custom mask generation | `generate_feathered_mask()` from morph_utils | Gaussian-blurred face oval mask |
| Eye center computation | Manual index lookup | `compute_eye_centers()` from alignment.py | Uses 16-landmark average per eye |
| Head dimensions | Custom bounding box | `compute_head_dimensions()` from pose_utils | IPD-normalized, consistent with model |

**Key insight:** Almost all building blocks exist. The new code is primarily **orchestration** — connecting existing utilities in the right order with the new delta computation pipeline.

## Common Pitfalls

### Pitfall 1: IED vs IPD Confusion
**What goes wrong:** Using 2D inter-eye distance (IED from `compute_eye_centers`) when 3D inter-pupillary distance (IPD from `normalize_landmarks_3d`) is needed, or vice versa.
**Why it happens:** IED is 2D pixel-space (from eye contour means), IPD is 3D (from iris center landmarks 468/473). The delta scaling uses IED (pixel space), while normalization uses IPD (3D space).
**How to avoid:** Delta computed in IPD-normalized space must be scaled back by source **IED** (2D pixel distance between eyes) for application to pixel landmarks. Use `compute_eye_centers` for IED, `normalize_landmarks_3d` for IPD.
**Warning signs:** Morphed face appears grossly scaled or offset.

### Pitfall 2: Model Landmarks are 2D, Source Has 3D
**What goes wrong:** Trying to compare 3D source landmarks directly with 2D model canonical landmarks.
**Why it happens:** `canonical_landmarks` in FACE_MODEL is (478, 2) — the Z column was dropped during model building. Source has (478, 3) for 3D.
**How to avoid:** Project source normalized 3D landmarks to 2D (`src_norm[:, :2]`) before computing delta against model.
**Warning signs:** Shape mismatch errors or nonsensical deltas.

### Pitfall 3: Mirror Pair Indices for Model Symmetrization
**What goes wrong:** Using `_MORPH_MIRROR_PAIRS` which are indices into MORPH_CONTROL_INDICES (positional), not raw landmark IDs, when operating on full 478-landmark arrays.
**Why it happens:** `_MORPH_MIRROR_PAIRS` stores pairs as raw landmark IDs (e.g., (338, 109)), but `_symmetrize_delta` maps them through `ctrl_pos = {lm_id: i for i, lm_id in enumerate(MORPH_CONTROL_INDICES)}` to get positional indices. When symmetrizing the full model (478 landmarks), the pairs are direct landmark indices.
**How to avoid:** For model symmetrization operating on full 478-point array, use landmark IDs directly as array indices. For delta symmetrization (42 control points), continue using the existing `_symmetrize_delta` which does the mapping internally.

### Pitfall 4: TPS Estimation Failure on Nearly-Identical Points
**What goes wrong:** TPS estimation returns False when source and destination points are nearly identical (low strength, similar face shapes).
**Why it happens:** Near-duplicate points after strength interpolation cause numerical instability.
**How to avoid:** Reuse the near-duplicate removal pattern from `compute_morph_warp` (min distance check, keep_mask filtering).
**Warning signs:** `tps.estimate()` returns False; passthrough triggered unexpectedly.

### Pitfall 5: Head Scale When Source Has No Pose
**What goes wrong:** Cannot compute `compute_head_dimensions` without 3D landmarks and IPD.
**Why it happens:** Fallback path (pose=None) still has `landmarks_3d` available from the face dict but no frontalization was done.
**How to avoid:** For the fallback path, compute head dimensions directly from the raw 3D landmarks (same as `process_image` does for no-pose faces). If landmarks_3d is all zeros (synthetic test data), default head_scale to 1.0.

### Pitfall 6: Cosine of Degrees vs Radians
**What goes wrong:** Passing degree values directly to `math.cos()` instead of converting to radians first.
**Why it happens:** Pose dict stores yaw/pitch in degrees.
**How to avoid:** Always use `math.cos(math.radians(yaw))`.

## Code Examples

### Complete Node morph() Method Structure
```python
def morph(self, source_image, face_model, source_landmarks,
          source_align_data, strength=0.5, symmetrize=False):
    h, w = source_image.shape[1], source_image.shape[2]

    try:
        # Validate inputs
        if not source_landmarks or len(source_landmarks) == 0:
            return self._passthrough(source_image, h, w, source_align_data)

        face = source_landmarks[0]
        src_lms_px = face["landmarks"]        # (478, 2) pixel coords
        src_3d = face["landmarks_3d"]          # (478, 3)
        pose = face.get("pose")                # dict or None

        # IED check
        src_eye_centers = compute_eye_centers(src_lms_px)
        src_ied = float(np.linalg.norm(src_eye_centers[0] - src_eye_centers[1]))
        if src_ied < 1e-6:
            return self._passthrough(source_image, h, w, source_align_data)

        # Get model canonical landmarks
        model_canonical = face_model["canonical_landmarks"]  # (478, 2)
        if symmetrize:
            model_canonical = _symmetrize_model(model_canonical)

        # Compute delta (pose-aware or fallback)
        if pose is not None:
            px_delta, effective_strength, head_scale = self._compute_pose_aware_delta(
                src_lms_px, src_3d, pose, model_canonical, face_model, strength, src_ied, src_eye_centers
            )
        else:
            px_delta, effective_strength, head_scale = self._compute_fallback_delta(
                src_lms_px, src_3d, model_canonical, face_model, strength, src_ied, src_eye_centers
            )

        # Apply TPS warp (same pattern as compute_morph_warp tail)
        src_ctrl_px = src_lms_px[MORPH_CONTROL_INDICES]
        morphed_ctrl = src_ctrl_px + effective_strength * px_delta

        # Boundary anchors + TPS estimation
        anchors = _get_boundary_anchors(w, h)
        src_with_anchors = np.vstack([src_ctrl_px, anchors])
        dst_with_anchors = np.vstack([morphed_ctrl, anchors])

        # Near-duplicate removal
        # ... (same as compute_morph_warp)

        tps = ThinPlateSplineTransform()
        success = tps.estimate(dst_with_anchors, src_with_anchors)
        if success is False:
            return self._passthrough(source_image, h, w, source_align_data)

        # Warp + mask + align_data (same as FaceShapeMorph)
        img_np = source_image[0].cpu().numpy().astype(np.float64)
        warped = warp(img_np, inverse_map=tps, output_shape=(h, w), ...)

        # Feathered mask from morphed landmarks
        morphed_full_lms = src_lms_px.copy()
        for i, ctrl_idx in enumerate(MORPH_CONTROL_INDICES):
            morphed_full_lms[ctrl_idx] = morphed_ctrl[i]
        mask_np = generate_feathered_mask(morphed_full_lms, h, w)

        out_align_data = dict(source_align_data)
        out_align_data["head_scale"] = float(head_scale)

        # Convert to tensors and return
        ...
    except Exception:
        return self._passthrough(source_image, h, w, source_align_data)
```

### FACE_MODEL Dict Structure (Runtime)
```python
# As produced by FaceModelBuilder and consumed by FaceModelMorph:
face_model = {
    "version": "2",
    "canonical_landmarks": np.ndarray,    # (478, 2) float64, IPD-normalized 2D
    "head_dimensions": {                  # IPD-normalized head bbox
        "width": float,
        "height": float,
        "depth": float,
    },
    "control_indices": np.ndarray,         # (42,) int64, same as MORPH_CONTROL_INDICES
    "landmark_stddev": np.ndarray,         # (478, 3) float64, per-landmark 3D stddev
}
```

### FACE_LANDMARKS Dict Structure (Source Input)
```python
# As produced by FaceDetect:
source_landmarks = [
    {
        "landmarks": np.ndarray,      # (478, 2) float64, pixel coordinates
        "landmarks_3d": np.ndarray,    # (478, 3) float64, normalized coordinates
        "pose": {                       # or None
            "pitch": float,             # degrees
            "yaw": float,               # degrees
            "roll": float,              # degrees
            "matrix": np.ndarray,       # (4, 4) transformation matrix
        },
    }
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Two-image morph (FaceShapeMorph) | Model-based morph (FaceModelMorph) | Phase 8 (now) | Multi-image statistical model replaces single target |
| 2D Procrustes only | 3D frontalize + normalize + Procrustes fallback | Phase 5 | Better pose invariance |
| No pose attenuation | cos(yaw)*cos(pitch) attenuation | Phase 7 (building) / Phase 8 (morphing) | Prevents artifacts on profile views |

## Open Questions

1. **Model symmetrization scope**
   - What we know: MRPH-03 symmetrize toggle operates on `canonical_landmarks` (478, 2). Mirror pairs exist in `_MORPH_MIRROR_PAIRS` (42 control points only — 20 pairs + 2 midline).
   - What's unclear: Should symmetrization apply to all 478 landmarks or only the 42 control points? Since delta is computed only at control points, symmetrizing only control indices should suffice.
   - Recommendation: Symmetrize only the control point subset of canonical_landmarks. This is simpler and the non-control landmarks are never used in delta computation.

2. **Eye midpoint for IED scaling origin**
   - What we know: `compute_eye_centers` returns eye contour means (16 landmarks each). `normalize_landmarks_3d` uses iris centers (468, 473).
   - What's unclear: When scaling delta from normalized to pixel space, should we use the same origin (eye midpoint) or is origin-independent scaling sufficient?
   - Recommendation: The delta is a displacement vector, so scaling by IED magnitude is origin-independent. No centering needed for the delta itself.

3. **Head scale when no 3D landmarks available**
   - What we know: Fallback path still has `landmarks_3d` from FaceDetect (always populated).
   - What's unclear: Whether `landmarks_3d` quality is sufficient for head dimensions without frontalization.
   - Recommendation: Use raw `landmarks_3d` with IPD from `normalize_landmarks_3d` for fallback head dimensions. This matches what `process_image` does in model_builder.py for no-pose faces.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none — `pytest tests/ -x -v` from project root |
| Quick run command | `conda run -n comfyui pytest tests/test_face_model_morph.py -x -v` |
| Full suite command | `conda run -n comfyui pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MRPH-01 | Model morph produces visible warp at strength=1.0 | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestMorphOutput -x` | No — Wave 0 |
| MRPH-01 | Strength=0 returns source unchanged | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestStrength -x` | No — Wave 0 |
| MRPH-01 | Pose-aware delta path produces valid TPS warp | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestPoseAwareDelta -x` | No — Wave 0 |
| MRPH-01 | Procrustes fallback path (pose=None) produces valid warp | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestFallbackPath -x` | No — Wave 0 |
| MRPH-02 | head_scale present in output align_data | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestAlignData -x` | No — Wave 0 |
| MRPH-03 | symmetrize=True modifies model before delta | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestSymmetrize -x` | No — Wave 0 |
| POSE-04 | High yaw reduces effective morph (near-zero change) | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestPoseAttenuation -x` | No — Wave 0 |
| N/A | Node registered in NODE_CLASS_MAPPINGS | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestRegistration -x` | No — Wave 0 |
| N/A | INPUT_TYPES matches specification | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestConventions -x` | No — Wave 0 |
| N/A | RETURN_TYPES matches FaceShapeMorph exactly | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestConventions -x` | No — Wave 0 |
| N/A | Graceful passthrough on invalid inputs | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestGracefulDegradation -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `conda run -n comfyui pytest tests/test_face_model_morph.py -x -v`
- **Per wave merge:** `conda run -n comfyui pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_face_model_morph.py` — all MRPH-01/02/03 and POSE-04 tests
- [ ] Synthetic FACE_MODEL fixture (deterministic canonical_landmarks + head_dimensions)
- [ ] Synthetic source_landmarks fixture with pose data (3D landmarks + transformation matrix)

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `face_morph.py`, `morph_utils.py`, `pose_utils.py`, `model_io.py`, `model_builder.py`, `alignment.py`, `landmarks.py`, `face_composite.py`, `__init__.py`
- Direct code inspection of `tests/test_face_morph.py`, `tests/test_face_model_builder.py`, `tests/conftest.py`
- CONTEXT.md locked decisions from user discussion session

### Secondary (MEDIUM confidence)
- Algorithm design for denormalization pipeline — verified against existing function signatures and data shapes

### Tertiary (LOW confidence)
- Model symmetrization implementation — detailed algorithm is a recommendation, not verified against real model data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all existing
- Architecture: HIGH — follows established patterns with well-understood extensions
- Pitfalls: HIGH — derived from direct code inspection and data type analysis
- Delta computation: MEDIUM — math is sound but needs synthetic data validation (noted as blocker in STATE.md)

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable domain, no external dependency changes expected)
