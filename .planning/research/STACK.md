# Technology Stack

**Project:** comfyui_imgtools - Face Shape Morphing Milestone
**Researched:** 2026-03-10

## Recommended Stack

### Face Detection & Landmarks
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| mediapipe | 0.10.32 | 478-point face landmark detection | Only viable option: 478 3D landmarks, runs on CPU, native macOS ARM64 wheels, no CUDA dependency. The new Face Landmarker task API (not legacy Face Mesh) provides blendshapes and transformation matrices as bonuses. | HIGH |

### Image Warping / Morphing
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| scikit-image | 0.26.0 | Thin Plate Spline warping | `ThinPlateSplineTransform.from_estimate()` -- clean API, smooth non-linear deformation, built on scipy/numpy (already ComfyUI deps). TPS produces smoother results than piecewise affine for face morphing. Preferred over OpenCV's TPS because skimage's API is cleaner and doesn't require opencv-contrib. | HIGH |
| scipy | (ComfyUI dep) | Spatial transforms, interpolation | Already a ComfyUI dependency. Used internally by scikit-image TPS and useful for Delaunay triangulation fallback. | HIGH |

### Image Processing & Compositing
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| opencv-python | (ComfyUI dep) | Image manipulation, color space conversion, Gaussian blur for feathered masks | Standard image processing. Use `opencv-python` (not `opencv-contrib-python`) -- TPS comes from scikit-image instead, keeping deps lighter. | HIGH |
| numpy | >=1.25.0 | Tensor/array operations | Already a ComfyUI dependency. All image data flows through numpy arrays. | HIGH |
| Pillow | (ComfyUI dep) | Image I/O fallback | Already a ComfyUI dependency. Not primary -- most work stays in numpy/torch tensors. | HIGH |

### ML Runtime
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| torch | (ComfyUI dep) | Tensor format compatibility, MPS backend | ComfyUI IMAGE tensors are `[batch, H, W, C]` torch tensors. Convert to numpy for processing, back to torch for output. Already installed. | HIGH |

## Critical: Python Version Constraint

**The system Python is 3.14.3 but MediaPipe only supports Python 3.9-3.12.**

ComfyUI itself recommends Python 3.13 (3.14 is experimental). This project MUST run inside a Python 3.12 or 3.13 virtual environment. If ComfyUI is already running on 3.14, MediaPipe will not install.

**Resolution options (in order of preference):**
1. ComfyUI likely runs in a venv with Python 3.12/3.13 -- verify before development
2. If ComfyUI uses 3.14, create a dedicated 3.12 venv for ComfyUI
3. Check for community-built MediaPipe 3.13/3.14 wheels (unofficial, on HuggingFace)

This is the single biggest integration risk for this milestone.

## New Dependencies (to add)

Only two new packages beyond what ComfyUI already provides:

```bash
pip install mediapipe>=0.10.20
pip install scikit-image>=0.25.0
```

Everything else (torch, numpy, scipy, Pillow, opencv) is already in ComfyUI's dependency tree.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Face landmarks | MediaPipe | Insightface | Non-commercial license restriction; heavier dependency (onnxruntime); Mac support is worse |
| Face landmarks | MediaPipe | dlib | Only 68 landmarks (vs 478); complex C++ build on Mac; much less facial detail for shape matching |
| Face landmarks | MediaPipe | face-alignment (BlazeFace) | Fewer landmarks; less maintained; MediaPipe is the upstream source anyway |
| TPS warping | scikit-image | opencv-contrib-python | Requires separate `opencv-contrib-python` install (conflicts with `opencv-python`); OpenCV's TPS API is clunky (DMatch objects, reshape gymnastics); scikit-image's API is cleaner |
| TPS warping | scikit-image | Custom numpy TPS | Reinventing the wheel; scikit-image's implementation is tested and optimized |
| Warping method | TPS | Piecewise affine (Delaunay triangulation) | More artifacts at triangle boundaries; TPS produces smoother, more natural deformations for face shape changes; PAW is faster but quality matters more here |
| Compositing | Feathered mask + alpha blend | cv2.seamlessClone (Poisson) | Poisson blending can cause color shifts and ghosting artifacts; feathered Gaussian mask is simpler, more predictable, and gives users more control via the strength parameter |

## MediaPipe API: Use Face Landmarker (NOT Legacy Face Mesh)

The legacy `mediapipe.solutions.face_mesh` API still works but is deprecated. Use the new task-based API:

```python
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Requires downloading face_landmarker.task model file
options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path="face_landmarker.task"),
    running_mode=vision.RunningMode.IMAGE,
    num_faces=5,  # support multi-face
)

with vision.FaceLandmarker.create_from_options(options) as landmarker:
    result = landmarker.detect(mp_image)
    # result.face_landmarks -> list of 478 NormalizedLandmark per face
```

The `.task` model file (~4MB) needs to be bundled or auto-downloaded. It provides 478 landmarks (10 more than legacy's 468), plus optional blendshapes and transformation matrices.

## scikit-image TPS API (0.26.0)

```python
from skimage.transform import ThinPlateSplineTransform, warp

# src_points, dst_points: (N, 2) arrays of landmark coordinates
tps = ThinPlateSplineTransform.from_estimate(dst_points, src_points)
warped = warp(image, tps, output_shape=image.shape[:2])
```

Note: `from_estimate` is the new API in 0.26.0. The old `estimate()` method is deprecated.

## Existing Landscape: ComfyUI_FaceShaper

The closest existing project is [ComfyUI_FaceShaper](https://github.com/fssorc/ComfyUI_FaceShaper). Key differences from our approach:

- Uses Insightface (non-commercial license) OR MediaPipe OR face-alignment
- Requires LivePortrait model files (landmark.onnx, landmark_model.pth)
- Uses "liquefying and stretching" rather than TPS warping
- No explicit macOS/Apple Silicon support
- More complex dependency tree

Our approach is simpler: MediaPipe only, TPS warping via scikit-image, minimal deps, Mac-first.

## Sources

- [MediaPipe PyPI](https://pypi.org/project/mediapipe/) - version 0.10.32, Python 3.9-3.12, macOS ARM64
- [MediaPipe Face Landmarker Python Guide](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python) - new task API
- [scikit-image 0.26.0 TPS docs](https://scikit-image.org/docs/stable/auto_examples/transform/plot_tps_deformation.html)
- [scikit-image 0.26.0 release notes](https://scikit-image.org/docs/stable/release_notes/release_0.26.html) - `from_estimate` API
- [opencv-contrib-python PyPI](https://pypi.org/project/opencv-contrib-python/) - version 4.13.0.92
- [ComfyUI_FaceShaper](https://github.com/fssorc/ComfyUI_FaceShaper) - existing solution comparison
- [ComfyUI system requirements](https://docs.comfy.org/installation/system_requirements) - Python 3.13 recommended
- [OpenCV seamless cloning docs](https://docs.opencv.org/4.x/df/da0/group__photo__clone.html)
