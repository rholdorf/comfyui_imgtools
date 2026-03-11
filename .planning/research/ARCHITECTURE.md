# Architecture Patterns

**Domain:** v1.1 Versatile Model -- multi-image face model building with 3D normalization
**Researched:** 2026-03-11

## Existing Architecture (v1.0, unchanged)

Four-node stateless pipeline, all under `imgtools/face`:

```
[FaceDetect] --> FACE_LANDMARKS (list of dicts with "landmarks" (478,2) + "landmarks_3d" (478,3))
     |
     v
[FaceCropAlign] --> IMAGE, ALIGN_DATA, MASK, FACE_LANDMARKS (crop-space)
     |
     v
[FaceShapeMorph] --> IMAGE (warped), MASK, ALIGN_DATA (with head_scale)
     |
     v
[FaceComposite] --> IMAGE (composited), MASK
```

**Key existing data structures:**
- `FACE_LANDMARKS`: `list[dict]` with `"landmarks"` (478,2 px) and `"landmarks_3d"` (478,3 normalized)
- `ALIGN_DATA`: dict with `rotation_angle`, `rotation_center`, `crop_box`, `original_size`, `transform_matrix`, optionally `head_scale`
- `MORPH_CONTROL_INDICES`: 42 points (36 face oval + 6 eyebrow endpoints)

**Key existing utilities:**
- `morph_utils.py`: `procrustes_align()`, `_symmetrize_delta()`, `normalize_landmarks()`, `compute_morph_warp()`, `generate_feathered_mask()`
- `alignment.py`: `compute_eye_centers()`, `build_alignment_transform()`, `apply_alignment()`
- `landmarks.py`: `extract_landmarks()` -- already returns both 2D and 3D
- `mediapipe_helper.py`: landmarker caching with config-aware singleton

## v1.1 Changes: What's New, What's Modified, What's Unchanged

### New Files

#### 1. `utils/pose_utils.py` -- Head Pose from MediaPipe Matrix

Extracts pose from MediaPipe's 4x4 transformation matrix and de-rotates landmarks to frontal.

**Key functions:**

```python
from scipy.spatial.transform import Rotation

def extract_pose(transform_matrix_4x4: np.ndarray) -> dict:
    """Extract pitch, yaw, roll from MediaPipe's 4x4 transformation matrix.

    The matrix maps canonical face -> detected face pose. We extract
    the rotation component and decompose to Euler angles.

    Args:
        transform_matrix_4x4: (4, 4) numpy array from
            result.facial_transformation_matrixes[i]

    Returns:
        dict with "pitch", "yaw", "roll" (degrees),
        "rotation" (scipy.Rotation), "rotation_matrix" (3x3 ndarray).
    """
    rot = Rotation.from_matrix(transform_matrix_4x4[:3, :3])
    pitch, yaw, roll = rot.as_euler('xyz', degrees=True)
    return {
        "pitch": pitch, "yaw": yaw, "roll": roll,
        "rotation": rot,
        "rotation_matrix": transform_matrix_4x4[:3, :3],
    }


def frontalize_landmarks(landmarks_3d: np.ndarray, pose: dict) -> np.ndarray:
    """Remove pose rotation from 3D landmarks, returning frontal-view coords.

    Applies inverse rotation to bring landmarks to canonical frontal orientation.

    Args:
        landmarks_3d: (478, 3) normalized coordinates from MediaPipe.
        pose: dict from extract_pose().

    Returns:
        (478, 3) frontalized landmarks (de-rotated, still centered).
    """
    inv_matrix = pose["rotation"].inv().as_matrix()
    centered = landmarks_3d - landmarks_3d.mean(axis=0)
    return centered @ inv_matrix.T
```

**Why this approach:** MediaPipe's 4x4 matrix IS the pose. No need to estimate it from landmarks (which v1.0's ARCHITECTURE.md proposed). The matrix comes free from enabling one boolean. scipy.Rotation handles decomposition and inverse cleanly.

#### 2. `utils/model_io.py` -- Model Persistence

Handles NPZ save/load for face models.

```python
def save_face_model(model: dict, path: str) -> None:
    """Save face model to .npz file.

    Model dict must contain:
        canonical_landmarks: (478, 2) float32 -- frontalized, IPD-normalized
        head_dimensions: (3,) float32 -- width/height/depth ratios
        metadata: dict with version, n_images, ied_mean, etc.
    """
    meta_bytes = np.frombuffer(
        json.dumps(model["metadata"]).encode(), dtype=np.uint8
    )
    np.savez_compressed(path,
        canonical_landmarks=model["canonical_landmarks"].astype(np.float32),
        head_dimensions=model["head_dimensions"].astype(np.float32),
        metadata=meta_bytes,
    )


def load_face_model(path: str) -> dict:
    """Load face model from .npz file. Safe (no pickle)."""
    data = np.load(path, allow_pickle=False)
    return {
        "canonical_landmarks": data["canonical_landmarks"],
        "head_dimensions": data["head_dimensions"],
        "metadata": json.loads(bytes(data["metadata"])),
    }
```

#### 3. `face_model_builder.py` -- FaceModelBuilder Node

New ComfyUI node that processes images into a face model.

```python
class FaceModelBuilder:
    RETURN_TYPES = ("FACE_MODEL", "INT", "STRING")
    RETURN_NAMES = ("face_model", "images_used", "report")
    FUNCTION = "build_model"
    CATEGORY = "imgtools/face"
```

### Modified Files

#### 4. `utils/mediapipe_helper.py` -- Enable Transformation Matrix

Small change: pass `output_facial_transformation_matrixes=True` when creating landmarker for model building. The existing `get_landmarker()` gets a new parameter.

```python
def get_landmarker(min_detection_confidence=0.5, min_presence_confidence=0.5,
                   output_transformation_matrix=False):
    # ... existing logic ...
    options = vision.FaceLandmarkerOptions(
        # ... existing options ...
        output_facial_transformation_matrixes=output_transformation_matrix,
    )
```

#### 5. `utils/landmarks.py` -- Include Transformation Matrix

When present, include the matrix in the face dict:

```python
def extract_landmarks(result, img_width, img_height):
    faces = []
    for i, face_lms in enumerate(result.face_landmarks):
        face_data = {
            "landmarks": landmarks_px,
            "landmarks_3d": landmarks_3d,
        }
        if result.facial_transformation_matrixes:
            face_data["transformation_matrix"] = result.facial_transformation_matrixes[i]
        faces.append(face_data)
    return faces
```

#### 6. `utils/morph_utils.py` -- New Model-Based Morph Function

Add `compute_model_morph_warp()` alongside existing `compute_morph_warp()`:

```python
def compute_model_morph_warp(source_lms, source_lms_3d, source_transform_matrix,
                              face_model, strength, img_shape):
    """Compute TPS warp using canonical face model instead of single target.

    1. Extract source pose from transformation matrix
    2. Frontalize + IPD-normalize source landmarks
    3. Compute shape delta in canonical space: model - source
    4. Scale delta back to source pixel space (* source_ipd)
    5. Symmetrize delta (reuse existing)
    6. Apply strength, build TPS with boundary anchors (reuse existing)

    Returns:
        Same as compute_morph_warp: (tps, morphed_ctrl_px, head_scale)
    """
```

#### 7. `face_morph.py` -- OR new `face_model_morph.py`

**Architecture decision: separate node vs overloaded node.**

Recommendation: **Separate FaceModelMorph node** because:
- Cleaner UX (no confusing optional inputs)
- Different required inputs (FACE_MODEL vs target_image + target_landmarks)
- Easier to test independently
- v1.0 FaceShapeMorph remains untouched (zero regression risk)

```python
class FaceModelMorph:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_image": ("IMAGE",),
                "source_landmarks": ("FACE_LANDMARKS",),
                "source_align_data": ("ALIGN_DATA",),
                "face_model": ("FACE_MODEL",),
                "strength": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "ALIGN_DATA")
    RETURN_NAMES = ("morphed_face", "warp_mask", "align_data")
    FUNCTION = "morph"
    CATEGORY = "imgtools/face"
```

### Component Boundaries (v1.1 Complete)

| Component | Responsibility | Status | Communicates With |
|-----------|---------------|--------|-------------------|
| `FaceDetect` | Detect 478 landmarks (2D + 3D) + optional 4x4 matrix | **Minor mod** (pass-through flag) | FaceCropAlign, FaceModelBuilder |
| `FaceCropAlign` | Crop, align, transform landmarks to crop space | **Unchanged** | FaceShapeMorph, FaceModelMorph |
| `FaceModelBuilder` | Build canonical model from images | **NEW** | FaceModelMorph (via FACE_MODEL) |
| `FaceShapeMorph` | TPS warp from single target | **Unchanged** | FaceComposite |
| `FaceModelMorph` | TPS warp from canonical model | **NEW** | FaceComposite |
| `FaceComposite` | Paste morphed face back with blending | **Unchanged** | -- |
| `utils/pose_utils.py` | Pose extraction, landmark frontalization | **NEW** | model building, model morph |
| `utils/model_io.py` | NPZ save/load for face models | **NEW** | FaceModelBuilder |
| `utils/morph_utils.py` | TPS computation + new model-based variant | **Modified** (additive) | FaceModelMorph |
| `utils/mediapipe_helper.py` | Landmarker creation/caching | **Modified** (new param) | FaceDetect, FaceModelBuilder |
| `utils/landmarks.py` | Landmark extraction from MediaPipe result | **Modified** (include matrix) | All detection consumers |
| `utils/alignment.py` | Affine transforms, eye centers | **Unchanged** | -- |

### Data Flow: v1.1 Model-Based Workflow

```
Target Image Directory
         |
         v
  [FaceModelBuilder] -----> FACE_MODEL (canonical landmarks + head dims)
                                |
                                |  (saved as .facemodel.npz, ~6KB)
                                |
Source Image --> [FaceDetect] --> FACE_LANDMARKS (2D + 3D + optional 4x4)
                    |
                    v
             [FaceCropAlign] --> cropped IMAGE, ALIGN_DATA, crop FACE_LANDMARKS
                    |
                    v
             [FaceModelMorph] <--- FACE_MODEL
                    |
                    | internally:
                    | 1. extract_pose(source transformation_matrix)
                    | 2. frontalize_landmarks(source_3d, pose)
                    | 3. normalize by IPD
                    | 4. delta = model_canonical - source_canonical
                    | 5. scale delta to source pixel space
                    | 6. TPS warp (reuse existing infrastructure)
                    |
                    v
             [FaceComposite] --> Final composited IMAGE
```

### Data Flow: v1.0 Single-Target Workflow (PRESERVED, UNCHANGED)

```
Source --> [FaceDetect] --> [FaceCropAlign] --> [FaceShapeMorph] --> [FaceComposite]
Target --> [FaceDetect] --> [FaceCropAlign] ------^
```

## Patterns to Follow

### Pattern 1: Separate Node per Workflow Mode
**What:** FaceModelMorph is a separate node from FaceShapeMorph.
**When:** v1.1 model-based morphing.
**Why:** Zero regression risk to v1.0. Cleaner INPUT_TYPES (no confusing optional inputs). Each node has single responsibility.

### Pattern 2: Canonical Space as Intermediary
**What:** All shape comparisons happen in normalized, pose-free, scale-free coordinate space.
**When:** Model building (averaging) and model application (diff computation).
**Why:** Makes landmarks from different images comparable regardless of pose, image size, face distance.

```
Raw 3D landmarks (MediaPipe normalized)
    --> extract pose from 4x4 matrix (scipy.Rotation)
    --> de-rotate to frontal (inverse rotation)
    --> project to 2D (drop z)
    --> normalize by IPD, center on eyes
    = Canonical space (comparable across images)
```

### Pattern 3: Delta in Canonical, Apply in Pixel Space
**What:** Compute shape difference in canonical space, then scale the delta vector back to source pixel space for TPS application.
**When:** Model-based morph in FaceModelMorph.
**Why:** Canonical space is where shapes are comparable; pixel space is where TPS operates.

```python
# In canonical space (IPD = 1.0, frontal, centered):
delta_canonical = model_canonical[CTRL_IDX] - source_canonical[CTRL_IDX]

# Scale to source pixel space:
delta_px = delta_canonical * source_ipd  # restore source scale

# Apply at source control points:
morphed_pts = source_ctrl_px + strength * delta_px
```

### Pattern 4: Incremental Averaging for Memory Efficiency
**What:** Process images one at a time with running weighted sum, not load-all-then-average.
**When:** FaceModelBuilder processing a directory.
**Why:** Memory efficient; works with large directories; can report progress per image.

### Pattern 5: Reuse Existing Infrastructure
**What:** FaceModelBuilder reuses `get_landmarker()`, `extract_landmarks()`, `compute_eye_centers()`.
**When:** Building the model -- detection is identical to FaceDetect.
**Why:** No code duplication; consistent behavior; tested code.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Using OpenCV for Pose Estimation
**What:** Adding `cv2.solvePnP()` for head pose.
**Why bad:** Introduces OpenCV dependency (project constraint); solvePnP requires camera intrinsics.
**Instead:** MediaPipe already provides the 4x4 matrix. Just enable the boolean flag.

### Anti-Pattern 2: Estimating Pose from 3D Landmarks via SVD
**What:** Custom SVD-based Procrustes between MediaPipe 3D landmarks and a reference canonical model.
**Why bad:** Reinvents what MediaPipe already computes internally. More code, more bugs, worse accuracy.
**Instead:** Use `result.facial_transformation_matrixes[i]` directly. Zero estimation code needed.
**Note:** The v1.0 ARCHITECTURE.md proposed this approach before we discovered MediaPipe provides the matrix. This research supersedes that recommendation.

### Anti-Pattern 3: Full 3D Face Reconstruction
**What:** Building a complete 3D mesh, projecting to novel views.
**Why bad:** Overkill for shape proportion matching; massive complexity; out of scope.
**Instead:** Use 3D landmarks only for pose estimation; work in 2D for shape morphing.

### Anti-Pattern 4: Overloading FaceShapeMorph with Optional FACE_MODEL
**What:** Adding `face_model` as optional input to existing FaceShapeMorph.
**Why bad:** Confusing UX (when do I use which input?); risk of regressions; harder to test.
**Instead:** Separate FaceModelMorph node. Clean inputs, clean responsibility.

### Anti-Pattern 5: JSON for Model Storage
**What:** Using JSON with nested lists for landmark arrays.
**Why bad:** Loses dtype precision, 10x larger than npz, slower to parse.
**Instead:** numpy .npz with `allow_pickle=False`. Compact (6KB), safe, preserves float32 precision.
**Note:** The v1.0 ARCHITECTURE.md proposed JSON. This research supersedes that -- npz is strictly better for numeric arrays.

## Suggested Build Order

Dependencies: pose_utils -> model_io -> FaceModelBuilder -> morph_utils changes -> FaceModelMorph.

### Phase 1: 3D Pose Foundation
**Build:** `utils/pose_utils.py` + mediapipe_helper.py change + landmarks.py change
**Deliverables:**
- `extract_pose()` using scipy.Rotation on MediaPipe's 4x4 matrix
- `frontalize_landmarks()` for pose removal
- Enable transformation matrix in `get_landmarker()`
- Include matrix in `extract_landmarks()` result
- Unit tests with synthetic 4x4 matrices

### Phase 2: Model Building
**Build:** `utils/model_io.py` + `face_model_builder.py`
**Deliverables:**
- NPZ save/load with version metadata
- FaceModelBuilder node with directory input, pose rejection, weighted averaging
- FACE_MODEL custom type registered in `__init__.py`
- Tests: model round-trip, averaging convergence

### Phase 3: Model-Based Morph
**Build:** `morph_utils.py` additions + `face_model_morph.py`
**Deliverables:**
- `compute_model_morph_warp()` in morph_utils
- FaceModelMorph node with FACE_MODEL input
- Same output interface as FaceShapeMorph (IMAGE, MASK, ALIGN_DATA)
- Tests: model morph produces valid warp, comparison with v1.0 single-target

### Phase 4: Integration & Polish
**Deliverables:**
- Full pipeline test: directory -> model -> morph -> composite
- Edge cases: empty dir, single image, all rejected, missing faces
- Performance validation
- Registration in `__init__.py`

## Sources

- MediaPipe `facial_transformation_matrixes`: verified via introspection on mediapipe 0.10.18 (HIGH)
- scipy.spatial.transform.Rotation: verified round-trip with scipy 1.12.0 (HIGH)
- numpy npz round-trip: verified at ~6KB with numpy 1.26.4 (HIGH)
- [MediaPipe 3D Face Transform](https://developers.googleblog.com/mediapipe-3d-face-transform/)
- [SciPy Rotation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.html)
