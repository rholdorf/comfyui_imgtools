# Phase 10: Enable Pose Data Pipeline - Research

**Researched:** 2026-03-11
**Domain:** MediaPipe pose data integration / FaceDetect-to-FaceModelMorph wiring
**Confidence:** HIGH

## Summary

Phase 10 addresses two integration gaps identified in the v1.1 milestone audit: (1) FaceDetect never enables `output_facial_transformation_matrixes=True` when calling `get_landmarker()`, so all face dicts have `pose: None`, and (2) FaceModelMorph's `_compute_pose_aware_delta` method is never reached at runtime because of gap (1). Both pieces of code already exist and are individually tested -- the problem is purely a wiring issue in `face_detection.py` line 41-43.

The fix is minimal: add `output_facial_transformation_matrixes=True` to the `get_landmarker()` call in `FaceDetect.detect_faces()`, then verify end-to-end that pose data flows through and triggers the pose-aware morph path. The existing `extract_landmarks()` function in `utils/landmarks.py` already has `hasattr` guard logic to extract pose from the result when transformation matrices are available (lines 35-38). The existing `FaceModelMorph` already branches on `pose is not None` (line 162) and calls `_compute_pose_aware_delta`.

**Primary recommendation:** One-line change in `face_detection.py` + integration test validating pose data flows end-to-end and attenuation is measurably active.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| POSE-04 | FaceModelMorph auto-attenuates morph strength for source faces with high yaw | `_compute_pose_aware_delta` already implements cosine attenuation (line 274-277 of face_model_morph.py). Currently dead code because FaceDetect never emits pose data. Enabling `output_facial_transformation_matrixes=True` activates this path. |
| MRPH-01 | User can apply a face model to a source image via FaceModelMorph node using pose-aware delta and TPS warp | FaceModelMorph already has full implementation. Currently always falls back to Procrustes because `pose` is always `None`. Fixing FaceDetect enables the pose-aware delta path. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mediapipe | >=0.10.14 | Face landmark detection + 4x4 transformation matrix | Already in use; `output_facial_transformation_matrixes` param already supported in `get_landmarker()` |
| scipy | (transitive) | `Rotation` for pose extraction/frontalization | Already in use via `pose_utils.py` |
| numpy | (transitive) | Landmark array operations | Already in use everywhere |
| pytest | (dev) | Test framework | Already in use; 231 tests exist |

### Supporting
No new libraries needed. This phase is purely wiring existing code.

### Alternatives Considered
None -- all code already exists.

## Architecture Patterns

### Current Data Flow (BROKEN)
```
FaceDetect.detect_faces()
  -> get_landmarker(min_detection_confidence=X)     # NO transformation matrix flag
  -> result.facial_transformation_matrixes = []     # empty because not requested
  -> extract_landmarks() sees empty list -> pose=None
  -> face dict: {"landmarks": ..., "landmarks_3d": ..., "pose": None}

FaceModelMorph.morph()
  -> pose = face.get("pose")  # None
  -> falls through to _compute_fallback_delta()     # Procrustes, no attenuation
```

### Fixed Data Flow (TARGET)
```
FaceDetect.detect_faces()
  -> get_landmarker(min_detection_confidence=X, output_facial_transformation_matrixes=True)
  -> result.facial_transformation_matrixes = [4x4 ndarray, ...]
  -> extract_landmarks() extracts pose via extract_pose_angles()
  -> face dict: {"landmarks": ..., "landmarks_3d": ..., "pose": {"pitch": ..., "yaw": ..., "roll": ..., "matrix": ...}}

FaceModelMorph.morph()
  -> pose = face.get("pose")  # dict with angles + matrix
  -> calls _compute_pose_aware_delta()              # frontalization + cosine attenuation
```

### Key Code Locations
| File | Line(s) | What to Change |
|------|---------|---------------|
| `face_detection.py` | 41-43 | Add `output_facial_transformation_matrixes=True` to `get_landmarker()` call |
| `utils/landmarks.py` | 34-38 | NO CHANGE NEEDED -- already has `hasattr` guard and extraction logic |
| `face_model_morph.py` | 162-175 | NO CHANGE NEEDED -- already branches on `pose is not None` |
| `utils/mediapipe_helper.py` | 18-19 | NO CHANGE NEEDED -- already accepts the parameter |

### Landmarker Cache Invalidation
`get_landmarker()` caches the landmarker instance and only recreates when params differ (line 40 of `mediapipe_helper.py`). Since we're adding a new parameter to the call, the cached `_landmarker_params` tuple will mismatch and a new landmarker will be created automatically. This is correct behavior. However, note that any other code calling `get_landmarker()` without this flag would create a DIFFERENT cached instance -- currently only `FaceDetect` calls it, so no conflict.

### Anti-Patterns to Avoid
- **Adding a user-facing toggle for pose output:** The audit makes clear this should always be enabled. Don't add a UI toggle -- just hardcode `True`.
- **Changing extract_landmarks signature:** The function already handles the optional transformation matrix gracefully. Don't refactor it.
- **Breaking v1.0 FaceShapeMorph:** FaceShapeMorph (the two-image morph node) does not use pose data at all. It gets landmarks from FaceDetect but ignores `pose`. Ensure it remains unaffected.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pose extraction | Custom rotation math | Existing `extract_pose_angles()` in `pose_utils.py` | Already handles scale removal via cbrt(det), uses SciPy Rotation |
| Frontalization | Manual matrix inversion | Existing `frontalize_landmarks()` in `pose_utils.py` | Already tested with 12+ test cases |
| Cosine attenuation | New attenuation logic | Existing code in `_compute_pose_aware_delta()` lines 274-277 | `cos(yaw) * cos(pitch)` already implemented |

**Key insight:** Every piece of pose-aware logic is already implemented and tested in isolation. This phase is exclusively about enabling the pipeline connection.

## Common Pitfalls

### Pitfall 1: Landmarker Cache Staleness in Tests
**What goes wrong:** If a test creates a landmarker without `output_facial_transformation_matrixes=True` first (e.g., from `conftest.py` or another test), the cached landmarker may not have transformation matrix output enabled.
**Why it happens:** `get_landmarker()` caches globally with `_landmarker` / `_landmarker_params`.
**How to avoid:** Integration tests that need real pose data must call `get_landmarker(output_facial_transformation_matrixes=True)` or use FaceDetect directly. Unit tests already use synthetic pose dicts (bypassing FaceDetect), so this mainly affects `@pytest.mark.slow` integration tests.
**Warning signs:** `result.facial_transformation_matrixes` is empty despite expecting data.

### Pitfall 2: MediaPipe Transformation Matrix Not Always Available
**What goes wrong:** Some face detections may not produce a transformation matrix even when `output_facial_transformation_matrixes=True`.
**Why it happens:** MediaPipe may fail to estimate the matrix for low-confidence detections.
**How to avoid:** `extract_landmarks()` already handles this with the `hasattr` guard and length check (line 35-38). The face dict will have `pose=None` for those faces, and FaceModelMorph will gracefully fall back to Procrustes.
**Warning signs:** N/A -- already handled.

### Pitfall 3: Import Path Issue in landmarks.py
**What goes wrong:** `utils/landmarks.py` line 3 uses `from utils.pose_utils import extract_pose_angles` -- a non-relative import that works in the test environment (where `utils/` is on the path) but might fail in a different import context.
**Why it happens:** Historical import style inconsistency.
**How to avoid:** This import currently works because tests add the package root to `sys.path`. If it breaks, change to `from .pose_utils import extract_pose_angles`. But since it's been working through all phases, no change needed unless tests fail.
**Warning signs:** ImportError on `utils.pose_utils` in `landmarks.py`.

### Pitfall 4: Breaking Existing Tests
**What goes wrong:** Changing FaceDetect's default behavior could break existing integration tests that don't expect pose data.
**Why it happens:** `test_face_detection.py` tests validate landmark structure but don't currently check for `pose` key.
**How to avoid:** Existing tests don't assert `pose is None`, so they should be unaffected. The `pose` key is already set in `extract_landmarks()` -- it's just always `None` currently. After the fix, it will be a dict for detected faces. No test assertions will break because none assert `pose is None`.

## Code Examples

### The One-Line Fix (face_detection.py)
```python
# BEFORE (line 41-43):
landmarker = get_landmarker(
    min_detection_confidence=min_detection_confidence
)

# AFTER:
landmarker = get_landmarker(
    min_detection_confidence=min_detection_confidence,
    output_facial_transformation_matrixes=True,
)
```

### Integration Test Pattern: Verify Pose Data Flows
```python
@pytest.mark.slow
def test_face_detect_emits_pose_data(self, real_face_tensor):
    """FaceDetect produces non-None pose dict for detected faces."""
    from comfyui_imgtools.face_detection import FaceDetect

    node = FaceDetect()
    landmarks, preview, face_count = node.detect_faces(real_face_tensor)

    assert face_count >= 1
    face = landmarks[0]
    assert "pose" in face
    assert face["pose"] is not None
    assert "yaw" in face["pose"]
    assert "pitch" in face["pose"]
    assert "roll" in face["pose"]
    assert "matrix" in face["pose"]
    assert face["pose"]["matrix"].shape == (4, 4)
```

### Integration Test Pattern: Pose-Aware Path Exercised
```python
@pytest.mark.slow
def test_pose_aware_morph_exercised(self, real_face_tensor):
    """FaceModelMorph uses _compute_pose_aware_delta when pose data is present."""
    from comfyui_imgtools.face_detection import FaceDetect
    from comfyui_imgtools.face_model_morph import FaceModelMorph

    # Detect face (now with pose data)
    detect_node = FaceDetect()
    landmarks, _, _ = detect_node.detect_faces(real_face_tensor)
    assert landmarks[0]["pose"] is not None

    # The existing unit test test_high_yaw_minimal_morph already validates
    # attenuation with synthetic pose dicts. Here we just verify the path
    # is reachable with real FaceDetect output.
```

### Integration Test Pattern: Yaw Attenuation Measurable
```python
def test_high_yaw_attenuates_morph(self):
    """Morph displacement at yaw=80 is less than at yaw=0."""
    # This test already exists in test_face_model_morph.py::TestPoseAttenuation
    # ::test_high_yaw_minimal_morph using synthetic pose dicts.
    # For Phase 10, add an integration-level version using real FaceDetect
    # output if possible, or verify the synthetic test still passes.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| FaceDetect without transformation matrix | FaceDetect with `output_facial_transformation_matrixes=True` | Phase 10 (this phase) | Enables pose-aware morphing pipeline |
| Always Procrustes fallback | Pose-aware delta with cosine attenuation | Phase 8 (code), Phase 10 (activation) | Better morph quality for non-frontal faces |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest, via conda env) |
| Config file | implicit (tests/ directory) |
| Quick run command | `conda run -n comfyui python -m pytest tests/ -x -v --ignore=tests/test_face_detection.py -k "not slow"` |
| Full suite command | `conda run -n comfyui python -m pytest tests/ -x -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POSE-04 | FaceDetect emits pose data; FaceModelMorph attenuates at high yaw | integration (slow) | `conda run -n comfyui python -m pytest tests/test_face_detection.py -x -v -k "pose"` | New test needed |
| POSE-04 | Cosine attenuation math | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py::TestPoseAttenuation -x -v` | Exists (4 tests) |
| MRPH-01 | Pose-aware delta produces valid warp | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py::TestPoseAwareDelta -x -v` | Exists (2 tests) |
| MRPH-01 | Full pipeline with pose data | integration | `conda run -n comfyui python -m pytest tests/test_integration_pipeline.py -x -v` | Exists but uses synthetic pose, needs update or new test |

### Sampling Rate
- **Per task commit:** `conda run -n comfyui python -m pytest tests/ -x -v -k "not slow"`
- **Per wave merge:** `conda run -n comfyui python -m pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_face_detection.py` -- add test asserting `pose` is not None for detected faces (slow/integration)
- [ ] `tests/test_face_detection.py` -- add test asserting pose dict has expected keys (yaw, pitch, roll, matrix)
- [ ] `tests/test_integration_pipeline.py` -- add test verifying pose-aware morph path is exercised end-to-end (can use mock or real detection)

## Open Questions

1. **Performance impact of enabling transformation matrices**
   - What we know: `output_facial_transformation_matrixes=True` adds a 4x4 matrix computation per face. Likely negligible compared to landmark detection itself.
   - What's unclear: Exact overhead has not been benchmarked.
   - Recommendation: Accept the overhead -- it's standard for pose-aware face processing and the landmarker is already the bottleneck.

2. **Whether to add a user toggle for pose-aware vs Procrustes path**
   - What we know: The audit explicitly flags the missing pose data as a bug, not a feature choice. The fallback path exists for backward compat when pose data is unavailable.
   - What's unclear: Whether any user would prefer Procrustes over pose-aware.
   - Recommendation: No toggle. Always enable transformation matrices. FaceModelMorph already gracefully falls back to Procrustes when pose is None.

## Sources

### Primary (HIGH confidence)
- **Codebase inspection** -- `face_detection.py`, `utils/mediapipe_helper.py`, `utils/landmarks.py`, `face_model_morph.py`, `utils/pose_utils.py` -- all read in full
- **v1.1 Milestone Audit** -- `.planning/v1.1-MILESTONE-AUDIT.md` -- explicitly documents the gap and fix
- **Existing tests** -- `test_face_model_morph.py` (28 tests), `test_face_detection.py` (6 tests), `test_integration_pipeline.py` (2 tests) -- verified test coverage

### Secondary (MEDIUM confidence)
- None needed -- this is a codebase wiring fix, not a new technology integration

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all code exists
- Architecture: HIGH -- one-line change with clear data flow analysis
- Pitfalls: HIGH -- exhaustive code reading reveals no hidden gotchas beyond landmarker caching

**Research date:** 2026-03-11
**Valid until:** indefinite -- this is a codebase-specific wiring fix, not subject to external API changes
