# Technology Stack

**Project:** comfyui_imgtools v1.1 — Versatile Model
**Researched:** 2026-03-11

## Key Finding: No New Dependencies Required

The v1.1 features (3D landmark normalization, multi-image averaging, persistent model format, pose-aware diff application) can be built entirely with the existing dependency stack. Zero new packages to install, test, or maintain.

## Existing Stack (Already Installed, Verified)

### Core (unchanged from v1.0)

| Technology | Version | Purpose | v1.1 Role |
|------------|---------|---------|-----------|
| MediaPipe | 0.10.18 | Face landmark detection | **NEW:** `facial_transformation_matrixes` for 3D pose |
| scikit-image | 0.24.0 | TPS warp, affine transforms | Unchanged -- warp application |
| NumPy | 1.26.4 | Array math | **NEW:** `.npz` for model file format, 3D landmark math |
| SciPy | 1.12.0 | (transitive via scikit-image) | **NEW:** `Rotation` class for Euler angle extraction |
| PyTorch | (ComfyUI) | Tensor I/O | Unchanged -- ComfyUI format bridge |

### Capabilities Mapped to Existing Deps

| Capability Needed | Solution | Why No New Dep |
|---|---|---|
| Head pose (pitch/yaw/roll) | MediaPipe `output_facial_transformation_matrixes=True` returns 4x4 matrix per face | Already in MediaPipe 0.10.18, just a boolean flag |
| Rotation math (matrix to Euler, inverse) | `scipy.spatial.transform.Rotation` | Already installed as scikit-image transitive dep |
| 3D landmark rotation to frontal | NumPy matrix multiplication (`pts @ R_inv.T`) | Core numpy |
| IPD-based scaling | `np.linalg.norm` | Already used in v1.0 `normalize_landmarks()` |
| Model file persistence | `numpy.savez_compressed` / `numpy.load` | Built into NumPy |
| Multi-image averaging | `numpy.mean(axis=0)` over stacked arrays | Built into NumPy |
| Directory traversal for image loading | `pathlib.Path.glob()` | Python stdlib |

## Critical Implementation Details

### 1. MediaPipe Facial Transformation Matrix (HIGH confidence)

**What it is:** A 4x4 rigid transform from canonical face space to detected face pose. Already available in the installed MediaPipe, disabled by default.

**Verified API (mediapipe 0.10.18):**

```python
# FaceLandmarkerOptions -- flip one boolean:
output_facial_transformation_matrixes: bool = False  # change to True

# FaceLandmarkerResult -- already typed:
facial_transformation_matrixes: List[numpy.ndarray]  # 4x4 float matrices per face
```

**Integration point:** Modify `utils/mediapipe_helper.py:get_landmarker()` to accept and pass through `output_facial_transformation_matrixes=True`. Modify `utils/landmarks.py:extract_landmarks()` to include the matrix in the face dict when present.

**Verification method:** Confirmed via `inspect.getmembers(vision.FaceLandmarkerResult)` and `help(vision.FaceLandmarkerOptions)` on the installed package. The field exists, is typed as `List[numpy.ndarray]`, and the option flag is available.

### 2. SciPy Rotation for Pose Decomposition (HIGH confidence)

**What it is:** Extract pitch/yaw/roll from MediaPipe's 4x4 matrix, compute inverse rotation for frontal normalization.

```python
from scipy.spatial.transform import Rotation

# Extract Euler angles from MediaPipe's 4x4 matrix
rot = Rotation.from_matrix(transform_4x4[:3, :3])
pitch, yaw, roll = rot.as_euler('xyz', degrees=True)

# Compute inverse for frontal normalization
inv_rot = rot.inv().as_matrix()
frontal_pts = landmarks_3d @ inv_rot.T
```

**Integration point:** New `utils/pose_utils.py` module with functions for pose extraction and landmark de-rotation.

**Verification method:** Tested with scipy 1.12.0 -- `Rotation.from_matrix()`, `.as_euler()`, `.inv()` all work correctly. Round-trip verified: construct rotation from known Euler angles, decompose back, get same angles.

### 3. NumPy NPZ for Model Persistence (HIGH confidence)

**What it is:** Compressed numpy archive format. Zero dependencies, safe loading, perfect for numeric array storage.

**Measured performance:** 478x3 float32 landmarks + head dimensions + JSON metadata = **~6 KB compressed**.

```python
# Save model
np.savez_compressed(path,
    canonical_landmarks=canonical_3d,     # (478, 3) float32
    head_dimensions=head_dims,            # (3,) float32
    metadata=np.frombuffer(json.dumps({
        'version': '1.0',
        'n_images': count,
        'ied_mean': mean_ied,
    }).encode(), dtype=np.uint8)
)

# Load model (safe -- no pickle)
data = np.load(path, allow_pickle=False)
canonical = data['canonical_landmarks']
meta = json.loads(bytes(data['metadata']))
```

**Why NPZ over alternatives:**

| Format | Verdict | Reason |
|--------|---------|--------|
| NPZ | **Use this** | Zero deps, safe, preserves dtype/shape, ~6KB |
| JSON | No | Loses array dtype, 10x larger for numeric data |
| msgpack | No | Requires new dep (msgpack-numpy), no benefit for ~6KB |
| pickle | No | Arbitrary code execution risk with `allow_pickle=True` |
| HDF5 | No | Requires h5py, overkill for single face model |

**Integration point:** New `utils/model_io.py` with `save_face_model()` / `load_face_model()`.

**Verification method:** Full round-trip tested with numpy 1.26.4 -- save, load, verify shapes, dtype, and metadata integrity.

### 4. 3D Normalization Pipeline (using above tools)

The full normalization flow uses only the three tools above:

```
Image -> MediaPipe detect (with transform matrix)
      -> Extract 3D landmarks (478, 3) from result
      -> Extract rotation from 4x4 matrix via scipy.Rotation
      -> De-rotate landmarks to frontal: pts_3d @ R_inv.T
      -> Scale by IPD: (pts - center) / ied  (numpy)
      -> Now in canonical pose-free, scale-free space
```

For multi-image averaging:
```
For each image:
    -> Normalize to frontal + IPD-scaled
    -> Stack into (N_images, 478, 3) array
np.mean(axis=0) -> canonical model (478, 3)
```

## What NOT to Add

| Library | Why Considered | Why Rejected |
|---------|---------------|-------------|
| OpenCV (cv2) | solvePnP for pose estimation | MediaPipe already provides transformation matrix; project explicitly avoids OpenCV |
| msgpack / msgpack-numpy | Model file serialization | NPZ is simpler, zero deps, sufficient for ~6KB models |
| h5py | Model file persistence | Overkill; NPZ handles this with zero new deps |
| open3d | 3D point cloud operations | Heavy dep, only need basic matrix math that numpy handles |
| trimesh | 3D mesh manipulation | Not doing mesh operations, just landmark arrays |
| dlib | Alternative face detection | MediaPipe already integrated, switching would break v1.0 |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Pose estimation | MediaPipe transform matrix | cv2.solvePnP | Would add OpenCV dep; MediaPipe provides the 4x4 matrix for free |
| Rotation math | scipy.spatial.transform.Rotation | Manual Rodrigues in numpy | scipy already installed, Rotation API is cleaner and handles edge cases (gimbal lock warning) |
| Model format | numpy .npz | JSON with base64 arrays | NPZ is native, smaller, preserves dtype |
| Model format | numpy .npz | pickle | Security risk; npz with allow_pickle=False is safe |
| Frontal normalization | De-rotate 3D landmarks via inverse matrix | solvePnP + manual projection | MediaPipe gives the matrix directly; no need to solve it ourselves |

## Installation

```bash
# No new installation needed. Verify existing deps:
conda run -n comfyui python -c "
import mediapipe; print(f'mediapipe: {mediapipe.__version__}')  # 0.10.18
import scipy; print(f'scipy: {scipy.__version__}')              # 1.12.0
import numpy; print(f'numpy: {numpy.__version__}')              # 1.26.4
import skimage; print(f'skimage: {skimage.__version__}')        # 0.24.0
from scipy.spatial.transform import Rotation; print('Rotation: OK')
"
```

## File Extension Convention

Face model files use `.facemodel.npz` extension to distinguish from other numpy archives. This is purely a naming convention, not a new format.

## Sources

- MediaPipe FaceLandmarkerOptions API: verified via `help(vision.FaceLandmarkerOptions)` on installed mediapipe 0.10.18 -- `output_facial_transformation_matrixes` parameter confirmed
- MediaPipe FaceLandmarkerResult: verified via `inspect.getmembers()` -- `facial_transformation_matrixes: List[numpy.ndarray]` field confirmed
- [MediaPipe 3D Face Transform](https://developers.googleblog.com/mediapipe-3d-face-transform/) -- describes the face geometry module that produces the transformation matrix
- [SciPy Rotation class docs (v1.17)](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.html) -- `from_matrix()`, `as_euler()`, `inv()`
- [MediaPipe Face Mesh wiki](https://github.com/google-ai-edge/mediapipe/wiki/MediaPipe-Face-Mesh) -- z coordinate semantics (relative depth, scaled as x)
- NumPy npz format: round-trip verified with numpy 1.26.4 on installed environment
- SciPy Rotation: round-trip verified with scipy 1.12.0 -- construct from Euler, decompose, get matching angles
