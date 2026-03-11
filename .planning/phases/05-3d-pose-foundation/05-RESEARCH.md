# Phase 5: 3D Pose Foundation - Research

**Researched:** 2026-03-11
**Domain:** 3D head pose extraction, landmark frontalization, IPD normalization
**Confidence:** HIGH

## Summary

This phase adds infrastructure to extract head pose (pitch/yaw/roll) from MediaPipe's 4x4 facial transformation matrix, frontalize 3D landmarks by inverting the rotation, and normalize by inter-pupil distance (IPD) for cross-image comparability. All new code lives in a new `utils/pose_utils.py` module; existing v1.0 code is minimally modified (only `mediapipe_helper.py` to enable the matrix output and `landmarks.py` to extract it into the face dict).

MediaPipe's `facial_transformation_matrixes` output is a `List[np.ndarray]` where each element is a 4x4 row-major numpy array representing a rigid transform (scale + rotation + translation) from canonical face model to detected face. SciPy's `Rotation.from_matrix()` and `.as_euler()` provide the exact decomposition needed. Both libraries are already installed (MediaPipe 0.10.18, SciPy 1.12.0).

**Primary recommendation:** Use `scipy.spatial.transform.Rotation.from_matrix(mat[:3,:3])` to extract the 3x3 rotation, then `.as_euler('XYZ', degrees=True)` for pitch/yaw/roll. Frontalize by applying the inverse rotation to 3D landmarks. IPD normalization uses 3D Euclidean distance between iris center landmarks (indices 468, 473).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Extend existing face dict with `pose` key containing pitch/yaw/roll angles AND raw 4x4 transformation matrix
- Non-breaking addition -- existing workflows ignore the new key
- Yaw rejection threshold: +/-45 degrees; Pitch rejection threshold: +/-30 degrees
- Frontalization accuracy target: ~2-3% IPD mean landmark error
- cos(yaw)*cos(pitch) weighting for model averaging
- Keep frontalized landmarks in 3D, project to 2D on demand
- Store both 3D frontalized landmarks AND pre-computed 2D projection in canonical model
- Missing transformation matrix: fall back to 2D landmarks (assume frontal), log warning
- All images rejected: clear error with guidance showing best candidate angles
- Rejection messages include actual angles: "image_03.jpg: REJECTED (yaw=52, threshold=45)"
- Input validation at external boundary only (data from MediaPipe), internal functions trust each other
- New `utils/pose_utils.py` module -- v1.0 morph_utils.py untouched
- IPD measured in 3D Euclidean space
- Head dimensions estimation (bounding box from landmarks) in pose_utils.py

### Claude's Discretion
- SciPy Rotation API usage for matrix decomposition
- Exact frontalization algorithm (de-rotation math)
- Internal function signatures and helper organization within pose_utils.py
- Test fixture design for frontalization accuracy validation

### Deferred Ideas (OUT OF SCOPE)
- Pose axis visualization on FaceDetect preview -- Phase 9
- Expression normalization via blendshapes -- v1.2 (MENH-02)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| POSE-01 | Extract pitch/yaw/roll from MediaPipe's 4x4 transformation matrix | SciPy Rotation.from_matrix() -> as_euler() decomposition; matrix format verified from MediaPipe source |
| POSE-02 | Frontalize 3D landmarks by de-rotating to canonical frontal pose | Inverse rotation via Rotation.inv().apply() on landmarks_3d array; MediaPipe right-handed coordinate system documented |
| POSE-03 | Normalize landmarks by inter-pupil distance for cross-image comparability | 3D Euclidean IPD from iris center indices 468/473; normalize_landmarks_3d() pattern analogous to existing 2D version |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scipy.spatial.transform.Rotation | 1.12.0 | 3x3 rotation matrix decomposition to Euler angles, inverse rotation | Already installed as transitive dep; replaces cv2.solvePnP per project constraint |
| mediapipe | 0.10.18 | Face detection with `output_facial_transformation_matrixes=True` | Already used; just enabling an existing option |
| numpy | (existing) | Matrix math, 3D landmark arrays | Already the core math library |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | (existing) | Test framework for pose_utils | All unit tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SciPy Rotation | Manual Euler decomposition | Error-prone gimbal lock handling; SciPy handles edge cases |
| SciPy Rotation | cv2.Rodrigues + solvePnP | Project constraint: no OpenCV |

**Installation:**
```bash
# No new dependencies needed. SciPy and MediaPipe already installed.
```

## Architecture Patterns

### Recommended Project Structure
```
utils/
├── pose_utils.py          # NEW: All Phase 5 logic
├── mediapipe_helper.py    # MODIFIED: enable transformation matrix output
├── landmarks.py           # MODIFIED: extract matrix into face dict
├── morph_utils.py         # UNCHANGED
├── alignment.py           # UNCHANGED
├── face_mask.py           # UNCHANGED
└── __init__.py            # UNCHANGED
```

### Pattern 1: Matrix Decomposition
**What:** Extract rotation and translation from MediaPipe's 4x4 homogeneous matrix
**When to use:** POSE-01 -- extracting pose angles from any detected face

The MediaPipe `facial_transformation_matrixes` output is `List[np.ndarray]`, each a 4x4 row-major numpy array. The matrix is a rigid transform (uniform scale + rotation + translation) from canonical face model to detected face. Bottom row is always `[0, 0, 0, 1]`.

```python
# Source: MediaPipe source code (face_landmarker.py lines 2917-2925)
# and SciPy docs (scipy.spatial.transform.Rotation)
from scipy.spatial.transform import Rotation
import numpy as np

def extract_pose_angles(transform_matrix: np.ndarray) -> dict:
    """Extract pitch, yaw, roll from a 4x4 transformation matrix.

    Args:
        transform_matrix: 4x4 numpy array from MediaPipe facial_transformation_matrixes

    Returns:
        Dict with 'pitch', 'yaw', 'roll' in degrees, plus 'matrix' (the raw 4x4).
    """
    # Extract 3x3 rotation (top-left), removing scale
    rot_with_scale = transform_matrix[:3, :3]
    # Remove uniform scale: divide by determinant^(1/3)
    scale = np.cbrt(np.linalg.det(rot_with_scale))
    rot_pure = rot_with_scale / scale

    r = Rotation.from_matrix(rot_pure)
    # XYZ intrinsic: pitch (X), yaw (Y), roll (Z)
    pitch, yaw, roll = r.as_euler('XYZ', degrees=True)

    return {
        'pitch': float(pitch),
        'yaw': float(yaw),
        'roll': float(roll),
        'matrix': transform_matrix,
    }
```

**Key detail:** The matrix may contain uniform scale. Extract it via `det(R)^(1/3)` before creating a pure rotation for Euler decomposition. SciPy's `from_matrix()` expects a proper rotation matrix (det=1).

### Pattern 2: Landmark Frontalization (De-rotation)
**What:** Remove head rotation from 3D landmarks to produce canonical frontal landmarks
**When to use:** POSE-02 -- normalizing landmarks for cross-pose comparison

```python
def frontalize_landmarks(landmarks_3d: np.ndarray, transform_matrix: np.ndarray) -> np.ndarray:
    """De-rotate 3D landmarks to canonical frontal pose.

    The transform_matrix maps canonical -> detected. To frontalize,
    apply the inverse rotation to the 3D landmarks.

    Args:
        landmarks_3d: (478, 3) normalized 3D landmarks from MediaPipe
        transform_matrix: 4x4 transformation matrix

    Returns:
        (478, 3) frontalized 3D landmarks
    """
    rot_with_scale = transform_matrix[:3, :3]
    translation = transform_matrix[:3, 3]
    scale = np.cbrt(np.linalg.det(rot_with_scale))
    rot_pure = rot_with_scale / scale

    r = Rotation.from_matrix(rot_pure)
    r_inv = r.inv()

    # Center landmarks, remove rotation, re-center
    centroid = landmarks_3d.mean(axis=0)
    centered = landmarks_3d - centroid
    frontalized = r_inv.apply(centered) + centroid

    return frontalized
```

### Pattern 3: 3D IPD Normalization
**What:** Scale landmarks so inter-pupil distance equals 1.0
**When to use:** POSE-03 -- making landmarks from different face sizes comparable

```python
# Iris center indices in MediaPipe 478-landmark model
LEFT_IRIS_CENTER = 468
RIGHT_IRIS_CENTER = 473

def normalize_landmarks_3d(landmarks_3d: np.ndarray) -> tuple[np.ndarray, float]:
    """Normalize 3D landmarks by inter-pupil distance.

    Args:
        landmarks_3d: (478, 3) 3D landmarks

    Returns:
        Tuple of (normalized_landmarks, ipd) where IPD=1.0 in normalized space.
    """
    left_iris = landmarks_3d[LEFT_IRIS_CENTER]
    right_iris = landmarks_3d[RIGHT_IRIS_CENTER]
    ipd = float(np.linalg.norm(left_iris - right_iris))

    if ipd < 1e-8:
        return landmarks_3d.copy(), 1.0

    midpoint = (left_iris + right_iris) / 2.0
    normalized = (landmarks_3d - midpoint) / ipd
    return normalized, ipd
```

### Pattern 4: Face Dict Extension
**What:** Non-breaking extension of the face dict with pose data
**When to use:** Integration point between existing v1.0 code and new Phase 5 code

```python
# In landmarks.py extract_landmarks():
# BEFORE (v1.0):
faces.append({
    "landmarks": landmarks_px,
    "landmarks_3d": landmarks_3d,
})

# AFTER (v1.1):
pose = None
if (result.facial_transformation_matrixes and
    i < len(result.facial_transformation_matrixes)):
    pose = extract_pose_angles(result.facial_transformation_matrixes[i])

faces.append({
    "landmarks": landmarks_px,
    "landmarks_3d": landmarks_3d,
    "pose": pose,  # None if matrix not available
})
```

### Anti-Patterns to Avoid
- **Hand-rolling Euler angle extraction:** Never manually decompose a rotation matrix into angles -- gimbal lock, sign errors, and convention mismatches are extremely common. Use SciPy Rotation.
- **Modifying morph_utils.py:** All new 3D/pose code goes in pose_utils.py. The v1.0 pipeline must remain untouched.
- **Assuming matrix is pure rotation:** MediaPipe's matrix includes uniform scale. Always extract and divide out scale before creating a Rotation object.
- **Using 2D eye centers for 3D IPD:** The v1.0 `compute_eye_centers()` averages 2D pixel contour points. For pose-invariant IPD, use 3D iris centers (indices 468, 473).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Euler angle extraction | Manual trigonometry from matrix elements | `Rotation.from_matrix().as_euler()` | Gimbal lock, sign conventions, 24 possible orders |
| Rotation inverse | Manual matrix transpose / inversion | `Rotation.inv()` | Numerical stability, correctness guarantees |
| Rotation application | Manual matrix-vector multiply | `Rotation.apply(vectors)` | Handles batch operations, internally optimized |
| Scale extraction from 4x4 | Manual SVD or norm computation | `np.cbrt(np.linalg.det(R[:3,:3]))` | For uniform scale this is exact and simple |

**Key insight:** SciPy's Rotation class handles all the edge cases (gimbal lock, numerical stability, proper/improper rotation detection) that are extremely easy to get wrong with manual implementations.

## Common Pitfalls

### Pitfall 1: Euler Angle Convention Mismatch
**What goes wrong:** Different systems use different Euler angle conventions. 'xyz' (lowercase, extrinsic) vs 'XYZ' (uppercase, intrinsic) give different results. Using the wrong one produces incorrect pitch/yaw/roll.
**Why it happens:** SciPy supports both intrinsic and extrinsic rotations; MediaPipe docs don't specify which convention they use internally.
**How to avoid:** Use intrinsic 'XYZ' convention (uppercase) which maps naturally to pitch(X)/yaw(Y)/roll(Z) in the camera coordinate frame. Validate with known poses (e.g., a face turned 45 degrees should give ~45 degree yaw).
**Warning signs:** Angles that seem swapped (pitch where yaw should be) or have unexpected signs.

### Pitfall 2: Scale in Transformation Matrix
**What goes wrong:** MediaPipe's 4x4 matrix contains uniform scale along with rotation. Passing the 3x3 sub-matrix directly to `Rotation.from_matrix()` without removing scale produces incorrect results or errors.
**Why it happens:** The matrix maps from canonical face model (in centimeters) to detected face in metric space. Scale encodes face size/distance.
**How to avoid:** Always extract scale via `det(R)^(1/3)` and divide it out before creating a Rotation.
**Warning signs:** `Rotation.from_matrix()` may warn about non-orthogonal matrix, or angles appear exaggerated.

### Pitfall 3: Coordinate System Confusion
**What goes wrong:** MediaPipe uses a right-handed coordinate system with camera at origin, looking along -Z. The landmarks_3d from `face_landmarks` use normalized image coordinates (x,y in [0,1], z is relative depth). These are NOT in the same coordinate frame as the transformation matrix.
**Why it happens:** MediaPipe has two coordinate systems: normalized image space (for landmarks) and metric 3D space (for the transformation matrix).
**How to avoid:** For frontalization, apply the inverse rotation to the landmarks_3d normalized coordinates. The rotation still correctly describes the head orientation even though the landmark coordinates are in normalized space.
**Warning signs:** Frontalized landmarks that are wildly displaced or scaled incorrectly.

### Pitfall 4: Landmarker Cache Invalidation
**What goes wrong:** The current `get_landmarker()` caches based on `(min_detection_confidence, min_presence_confidence)`. Adding `output_facial_transformation_matrixes=True` changes the landmarker config but may not invalidate the cache.
**Why it happens:** The cache key doesn't include the new parameter.
**How to avoid:** Add `output_facial_transformation_matrixes` to the cache key tuple in `_landmarker_params`.
**Warning signs:** Matrix output is empty despite enabling the option (using a stale cached landmarker).

### Pitfall 5: Missing Transformation Matrix for Some Faces
**What goes wrong:** In rare cases, MediaPipe may return landmarks but no transformation matrix for a face (e.g., very low confidence geometry).
**Why it happens:** The geometry pipeline is separate from landmark detection and may fail independently.
**How to avoid:** Always check if `result.facial_transformation_matrixes` has an entry for the face index. Fall back to None pose (assume frontal) with a warning per CONTEXT.md decision.
**Warning signs:** IndexError when accessing `result.facial_transformation_matrixes[i]`.

### Pitfall 6: Gimbal Lock at Extreme Pitch
**What goes wrong:** SciPy warns about gimbal lock when pitch approaches +/-90 degrees. Yaw and roll become ambiguous.
**Why it happens:** Fundamental limitation of Euler angles when the middle rotation reaches +/-90 degrees.
**How to avoid:** At +/-90 pitch, the face is looking straight up/down -- far beyond the +/-30 degree rejection threshold. The warning can be safely ignored since those faces are rejected anyway.
**Warning signs:** SciPy RuntimeWarning about gimbal lock.

## Code Examples

### Enabling Transformation Matrix in MediaPipe Helper

```python
# Source: Verified from mediapipe_helper.py and MediaPipe source code
# In utils/mediapipe_helper.py - modify get_landmarker():

def get_landmarker(min_detection_confidence=0.5, min_presence_confidence=0.5,
                   output_facial_transformation_matrixes=False):
    global _landmarker, _landmarker_params

    params = (min_detection_confidence, min_presence_confidence,
              output_facial_transformation_matrixes)

    if _landmarker is not None and _landmarker_params == params:
        return _landmarker

    # ... (model download logic unchanged) ...

    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=10,
        min_face_detection_confidence=min_detection_confidence,
        min_face_presence_confidence=min_presence_confidence,
        output_facial_transformation_matrixes=output_facial_transformation_matrixes,
    )
    _landmarker = vision.FaceLandmarker.create_from_options(options)
    _landmarker_params = params
    return _landmarker
```

### Extracting Matrix in landmarks.py

```python
# Source: Verified from landmarks.py and MediaPipe FaceLandmarkerResult source
def extract_landmarks(result, img_width, img_height):
    if not result.face_landmarks:
        return []

    faces = []
    for i, face_lms in enumerate(result.face_landmarks):
        landmarks_px = np.array(
            [[lm.x * img_width, lm.y * img_height] for lm in face_lms]
        )
        landmarks_3d = np.array(
            [[lm.x, lm.y, lm.z] for lm in face_lms]
        )

        # Extract transformation matrix if available
        pose_matrix = None
        if (hasattr(result, 'facial_transformation_matrixes') and
                result.facial_transformation_matrixes and
                i < len(result.facial_transformation_matrixes)):
            pose_matrix = result.facial_transformation_matrixes[i]

        faces.append({
            "landmarks": landmarks_px,
            "landmarks_3d": landmarks_3d,
            "pose": pose_matrix,  # np.ndarray (4,4) or None
        })
    return faces
```

### Head Dimensions from 3D Landmarks

```python
# Head bounding box from 3D landmarks for downstream model file
def compute_head_dimensions(landmarks_3d: np.ndarray, ipd: float) -> dict:
    """Compute head dimensions normalized by IPD.

    Args:
        landmarks_3d: (478, 3) landmarks (ideally frontalized)
        ipd: inter-pupil distance for normalization

    Returns:
        Dict with 'width', 'height', 'depth' in IPD-normalized units.
    """
    if ipd < 1e-8:
        ipd = 1.0
    mins = landmarks_3d.min(axis=0)
    maxs = landmarks_3d.max(axis=0)
    extents = maxs - mins
    return {
        'width': float(extents[0] / ipd),
        'height': float(extents[1] / ipd),
        'depth': float(extents[2] / ipd),
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| cv2.solvePnP for head pose | MediaPipe transformation matrix | MediaPipe Tasks API (2023) | No OpenCV needed; matrix provided directly |
| Manual Euler extraction | SciPy Rotation class | SciPy 1.4+ (2019) | Handles all edge cases automatically |
| 2D Procrustes for pose removal | 3D de-rotation via inverse transform | This phase | True frontalization instead of 2D approximation |

**Deprecated/outdated:**
- `mediapipe.solutions.face_mesh`: Legacy API. Current project uses `mediapipe.tasks.python.vision.FaceLandmarker` (correct).

## Open Questions

1. **Euler angle convention validation**
   - What we know: SciPy 'XYZ' intrinsic is the standard mapping to pitch/yaw/roll in camera-centric coordinates
   - What's unclear: MediaPipe's exact coordinate frame orientation (is +Y up or down in their metric space?)
   - Recommendation: Create a synthetic test -- build a known rotation matrix for 30-degree yaw, verify `as_euler('XYZ')` returns [0, 30, 0]. If signs are inverted, negate the relevant axis. Empirical validation with real images is essential.

2. **Frontalization centroid choice**
   - What we know: De-rotation should be around some center point
   - What's unclear: Whether to use landmark centroid, nose tip, or eye midpoint as rotation center
   - Recommendation: Use landmark centroid (mean of all 478 points). This preserves relative positions best. The eye midpoint is used for IPD normalization separately.

3. **Accuracy target validation**
   - What we know: Target is ~2-3% IPD mean landmark error for frontalization
   - What's unclear: How to create ground truth for validation without real paired frontal/rotated images
   - Recommendation: Synthetic rotation tests. Take frontal landmarks, apply known rotation, frontalize, measure error. Real-world accuracy will be dominated by MediaPipe detection noise.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | None (uses default discovery in `tests/`) |
| Quick run command | `conda run -n comfyui python -m pytest tests/ -x -v` |
| Full suite command | `conda run -n comfyui python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POSE-01 | Extract pitch/yaw/roll from 4x4 matrix | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_extract_pose_identity -x` | No - Wave 0 |
| POSE-01 | Correct angles for known rotations (30-deg yaw, etc.) | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_extract_pose_known_rotation -x` | No - Wave 0 |
| POSE-01 | Handle matrix with uniform scale | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_extract_pose_with_scale -x` | No - Wave 0 |
| POSE-02 | Frontalize identity (already frontal) returns same landmarks | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_frontalize_identity -x` | No - Wave 0 |
| POSE-02 | Frontalize rotated landmarks matches frontal within tolerance | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_frontalize_accuracy -x` | No - Wave 0 |
| POSE-02 | Frontalize with missing matrix falls back gracefully | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_frontalize_no_matrix -x` | No - Wave 0 |
| POSE-03 | IPD-normalized landmarks have IPD=1.0 | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_normalize_ipd -x` | No - Wave 0 |
| POSE-03 | Two different-sized faces produce comparable normalized landmarks | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_normalize_cross_face -x` | No - Wave 0 |
| POSE-03 | Near-zero IPD handled gracefully | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_normalize_zero_ipd -x` | No - Wave 0 |
| ALL | v1.0 regression: all 123 tests pass unchanged | regression | `conda run -n comfyui python -m pytest tests/ -v` | Yes (123 existing) |

### Sampling Rate
- **Per task commit:** `conda run -n comfyui python -m pytest tests/test_pose_utils.py -x -v`
- **Per wave merge:** `conda run -n comfyui python -m pytest tests/ -v`
- **Phase gate:** Full suite green (123 existing + new tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_pose_utils.py` -- covers POSE-01, POSE-02, POSE-03
- [ ] Test fixtures for known rotation matrices (identity, 30-deg yaw, 45-deg yaw, 30-deg pitch)
- [ ] Test fixtures for synthetic 3D landmarks (frontal face with known geometry)

## Sources

### Primary (HIGH confidence)
- MediaPipe face_landmarker.py source code (lines 2917-2925) - verified matrix format is `List[np.ndarray]`, 4x4, row-major
- MediaPipe FaceLandmarkerOptions source - verified `output_facial_transformation_matrixes` parameter (default False)
- SciPy Rotation docs (scipy.spatial.transform.Rotation) - verified from_matrix(), as_euler(), inv(), apply() APIs
- MediaPipe face_geometry.proto - verified matrix contains scale+rotation+translation, bottom row [0,0,0,1]
- Local environment verification: MediaPipe 0.10.18, SciPy 1.12.0, 123 existing tests

### Secondary (MEDIUM confidence)
- [MediaPipe Python guide](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python) - general usage
- [MediaPipe 3D Face Transform blog](https://developers.googleblog.com/en/mediapipe-3d-face-transform/) - right-handed metric 3D space, centimeter units
- [GitHub Issue #1642](https://github.com/google/mediapipe/issues/1642) - column-major storage in proto (but Python API normalizes to row-major)
- [SciPy Rotation reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.html) - Euler convention details

### Tertiary (LOW confidence)
- Euler angle convention mapping (XYZ -> pitch/yaw/roll) needs empirical validation with real images

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - both libraries already installed and verified, no new dependencies
- Architecture: HIGH - clear integration points, minimal changes to v1.0, well-understood math
- Pitfalls: HIGH - verified from source code (cache invalidation, scale in matrix, coordinate systems)
- Euler convention: MEDIUM - standard mapping but needs empirical validation per Open Question 1

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable domain, no fast-moving dependencies)
