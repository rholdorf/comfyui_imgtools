# Phase 12: Forward Pose Data Through FaceCropAlign - Research

**Researched:** 2026-03-12
**Domain:** Data forwarding / pipeline plumbing (Python dict passthrough)
**Confidence:** HIGH

## Summary

This phase closes the last remaining gap from the v1.1 re-audit: FaceCropAlign drops the `pose` key when building its `crop_landmarks_out` output, which means the standard node chain (FaceDetect -> FaceCropAlign -> FaceModelMorph) cannot deliver pose data to FaceModelMorph, forcing it to fall back to the Procrustes path instead of using `_compute_pose_aware_delta`.

The fix is surgical: one line addition in `face_crop.py` to forward the `pose` key from the upstream face dict into `crop_landmarks_out`. The existing test fixtures in `conftest.py` lack `pose` keys, so they won't break, but new tests are needed to verify the forwarding behavior and the end-to-end pose-aware pipeline.

**Primary recommendation:** Add `"pose": landmarks[idx].get("pose")` to the `crop_landmarks_out` dict in `face_crop.py` line 85-88, then add targeted tests for pose forwarding and end-to-end pose-aware morph through the standard chain.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| POSE-04 | FaceModelMorph auto-attenuates morph strength for source faces with high yaw | Pose data must reach FaceModelMorph via crop_landmarks for attenuation to trigger; fix is forwarding pose through FaceCropAlign |
| MRPH-01 | User can apply a face model to a source image via FaceModelMorph node using pose-aware delta and TPS warp | FaceModelMorph already implements pose-aware delta (`_compute_pose_aware_delta`), but it only activates when `pose is not None`; currently FaceCropAlign strips pose, so this requirement is unmet through the standard chain |
</phase_requirements>

## Standard Stack

No new libraries or dependencies needed. This is a pure plumbing fix in existing code.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dict | built-in | Data forwarding through node chain | FACE_LANDMARKS is list-of-dicts convention |

### Supporting
None needed.

## Architecture Patterns

### The FACE_LANDMARKS Convention

FACE_LANDMARKS is a list of dicts, each representing a detected face. The canonical schema produced by `extract_landmarks` in `utils/landmarks.py`:

```python
{
    "landmarks": np.ndarray,    # (478, 2) pixel coords
    "landmarks_3d": np.ndarray, # (478, 3) normalized coords
    "pose": dict | None,        # {"pitch", "yaw", "roll", "matrix"} or None
}
```

### The Gap (face_crop.py lines 84-88)

Current code builds `crop_landmarks_out` with only 2 of 3 keys:

```python
crop_landmarks_out = [{
    "landmarks": crop_landmarks,
    "landmarks_3d": landmarks[idx].get("landmarks_3d", np.zeros((478, 3))),
    # MISSING: "pose" key not forwarded
}]
```

### The Fix Pattern

```python
crop_landmarks_out = [{
    "landmarks": crop_landmarks,
    "landmarks_3d": landmarks[idx].get("landmarks_3d", np.zeros((478, 3))),
    "pose": landmarks[idx].get("pose"),
}]
```

This follows the same `.get()` defensive pattern already used for `landmarks_3d`. When pose is not present (v1.0 face dicts), `.get("pose")` returns `None`, which is exactly what FaceModelMorph expects for its Procrustes fallback path.

### Data Flow (After Fix)

```
FaceDetect.detect_faces()
  -> extract_landmarks() produces {landmarks, landmarks_3d, pose}
  -> FaceCropAlign.crop_and_align()
    -> Transforms landmarks to crop space
    -> Forwards pose UNCHANGED (pose is head-relative, not affected by crop/align)
    -> crop_landmarks_out = [{landmarks: ..., landmarks_3d: ..., pose: ...}]
  -> FaceModelMorph.morph()
    -> face.get("pose") returns dict (not None)
    -> _compute_pose_aware_delta() runs (not fallback)
    -> Cosine attenuation applied: cos(yaw) * cos(pitch)
```

### Why Pose Is Not Affected by Crop/Align

Pose (pitch/yaw/roll) comes from MediaPipe's 4x4 facial transformation matrix and represents the 3D head orientation relative to the camera. Cropping and 2D alignment do NOT change the 3D head pose -- they only affect the 2D pixel coordinates. So forwarding pose verbatim is correct.

### Anti-Patterns to Avoid
- **Recomputing pose from cropped image:** Unnecessary and wrong -- pose is a property of the original detection, not the crop
- **Modifying pose based on alignment rotation:** The 2D alignment rotation is for eye leveling, not 3D pose
- **Adding pose as a separate output from FaceCropAlign:** Over-engineering -- the FACE_LANDMARKS dict already has a slot for it

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pose forwarding | Custom pose output port | Dict key in existing FACE_LANDMARKS | Matches existing convention, zero API change |
| Defensive access | KeyError handling | `.get("pose")` | Returns None for old-format dicts without pose |

## Common Pitfalls

### Pitfall 1: Forgetting the Degenerate Crop Path
**What goes wrong:** The `if x2 <= x1 or y2 <= y1` branch sets `crop_landmarks_out = []` (empty list). This is already correct -- FaceModelMorph handles empty landmarks with passthrough.
**How to avoid:** Don't change the degenerate path. The fix only applies to the normal (non-degenerate) code path at line 85.

### Pitfall 2: Test Fixtures Without Pose Data
**What goes wrong:** Existing conftest.py fixtures (`mock_deterministic_landmarks`, `mock_multi_face_landmarks`) do not include `pose` keys. Tests that check FaceCropAlign output won't detect if pose forwarding breaks.
**How to avoid:** Create new test fixtures or modify existing tests to pass face dicts with pose data and verify it appears in output.

### Pitfall 3: Breaking Existing Tests
**What goes wrong:** Adding a `pose` key check to existing assertions could make them fail for fixtures that don't have pose.
**How to avoid:** Add NEW tests for pose forwarding rather than modifying existing test assertions. The fix is additive.

## Code Examples

### Fix in face_crop.py (lines 84-88)

```python
# Source: face_crop.py direct analysis
# Before:
crop_landmarks_out = [{
    "landmarks": crop_landmarks,
    "landmarks_3d": landmarks[idx].get("landmarks_3d", np.zeros((478, 3))),
}]

# After:
crop_landmarks_out = [{
    "landmarks": crop_landmarks,
    "landmarks_3d": landmarks[idx].get("landmarks_3d", np.zeros((478, 3))),
    "pose": landmarks[idx].get("pose"),
}]
```

### Test: Pose Forwarding Through FaceCropAlign

```python
def test_crop_landmarks_forwards_pose(sample_face_image_tensor):
    """FaceCropAlign forwards pose data from upstream face dict."""
    from comfyui_imgtools.face_crop import FaceCropAlign

    pose_data = {"pitch": 5.0, "yaw": -10.0, "roll": 2.0, "matrix": np.eye(4)}
    landmarks = _make_deterministic_landmarks(128.0, 128.0)
    face_input = [{
        "landmarks": landmarks,
        "landmarks_3d": np.zeros((478, 3)),
        "pose": pose_data,
    }]

    node = FaceCropAlign()
    _, _, _, crop_lms = node.crop_and_align(sample_face_image_tensor, face_input)

    assert len(crop_lms) == 1
    assert "pose" in crop_lms[0]
    assert crop_lms[0]["pose"] is pose_data  # same object, not copy
```

### Test: Pose None When Upstream Has No Pose

```python
def test_crop_landmarks_pose_none_when_missing(sample_face_image_tensor):
    """FaceCropAlign outputs pose=None when upstream face has no pose key."""
    from comfyui_imgtools.face_crop import FaceCropAlign

    landmarks = _make_deterministic_landmarks(128.0, 128.0)
    face_input = [{
        "landmarks": landmarks,
        "landmarks_3d": np.zeros((478, 3)),
        # No "pose" key
    }]

    node = FaceCropAlign()
    _, _, _, crop_lms = node.crop_and_align(sample_face_image_tensor, face_input)

    assert crop_lms[0].get("pose") is None
```

### Test: End-to-End Pose-Aware Path

```python
def test_e2e_pose_aware_morph_through_crop():
    """FaceDetect -> FaceCropAlign -> FaceModelMorph uses pose-aware delta."""
    from comfyui_imgtools.face_model_morph import FaceModelMorph

    # Simulate FaceCropAlign output WITH pose
    face_with_pose = _make_synthetic_face(yaw=0.0, pitch=0.0, has_pose=True)
    face_without_pose = _make_synthetic_face(yaw=0.0, pitch=0.0, has_pose=False)

    node = FaceModelMorph()
    model = _make_synthetic_model(offset=0.3)
    img = _make_test_image()
    align_data = _make_align_data()

    # With pose: should use _compute_pose_aware_delta
    result_pose = node.morph(img, model, [face_with_pose], align_data, strength=1.0)
    # Without pose: should use _compute_fallback_delta
    result_no_pose = node.morph(img, model, [face_without_pose], align_data, strength=1.0)

    # Results should differ (different code paths)
    diff = np.abs(result_pose[0][0].numpy() - result_no_pose[0][0].numpy()).mean()
    assert diff > 0.0, "Pose-aware and fallback paths should produce different results"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FaceCropAlign drops pose | FaceCropAlign forwards pose | Phase 12 (this fix) | Enables POSE-04 and MRPH-01 through standard chain |
| FaceModelMorph always falls back to Procrustes via CropAlign chain | FaceModelMorph uses pose-aware delta via CropAlign chain | Phase 12 | Cosine attenuation activates for high-yaw faces |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest in conda env) |
| Config file | tests/conftest.py |
| Quick run command | `conda run -n comfyui python -m pytest tests/test_face_crop.py tests/test_face_model_morph.py -x -v` |
| Full suite command | `conda run -n comfyui python -m pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POSE-04 | Morph attenuation triggers for high-yaw faces through standard chain | unit | `conda run -n comfyui python -m pytest tests/test_face_crop.py -x -v -k pose` | No -- Wave 0 |
| MRPH-01 | Pose-aware delta used (not Procrustes fallback) when pose data available | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py -x -v -k pose_aware` | Partial -- TestPoseAwareDelta exists but doesn't test through CropAlign chain |

### Sampling Rate
- **Per task commit:** `conda run -n comfyui python -m pytest tests/test_face_crop.py tests/test_face_model_morph.py -x -v`
- **Per wave merge:** `conda run -n comfyui python -m pytest tests/ -x -v`
- **Phase gate:** Full suite green (242+ tests) before verify

### Wave 0 Gaps
- [ ] `tests/test_face_crop.py` -- add pose forwarding tests (pose present, pose absent, degenerate crop)
- [ ] `tests/test_face_model_morph.py` -- add end-to-end test verifying pose-aware path triggers through CropAlign output format

## Open Questions

None. The fix is straightforward and well-understood. All code paths are visible and the change is additive.

## Sources

### Primary (HIGH confidence)
- `face_crop.py` lines 84-88 -- direct code inspection of the gap
- `utils/landmarks.py` lines 6-45 -- extract_landmarks produces {landmarks, landmarks_3d, pose}
- `face_model_morph.py` lines 143-175 -- FaceModelMorph reads `face.get("pose")` and branches
- `tests/conftest.py` -- fixtures confirmed to lack `pose` keys
- `tests/test_face_crop.py` -- existing tests confirmed to not check pose forwarding
- `tests/test_face_model_morph.py` -- existing pose tests use synthetic faces directly (bypass CropAlign)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure dict plumbing
- Architecture: HIGH -- data flow fully traced through all 3 files
- Pitfalls: HIGH -- all edge cases identified (degenerate crop, missing pose, fixture gaps)

**Research date:** 2026-03-12
**Valid until:** Indefinite (stable internal plumbing, no external dependencies)
