# ComfyUI Face Shape Matcher

## What This Is

A set of ComfyUI custom nodes that pre-process face geometry before face swapping. Four nodes (FaceDetect, FaceCropAlign, FaceShapeMorph, FaceComposite) detect landmarks, crop and align faces, morph source face shape to match target proportions via TPS warping, and composite the result back with feathered blending. Designed to work upstream of ReActor or other face swap nodes.

## Core Value

Morph the source face shape to match the target face proportions so that downstream face swap produces natural-looking results regardless of face shape differences.

## Requirements

### Validated

- ✓ ImageDimensionFitter node — existing
- ✓ ImagePaddingCalculator node — existing
- ✓ PathSplitter node — existing
- ✓ Face landmark detection (478 points, MediaPipe) — v1.0
- ✓ Face crop with configurable padding — v1.0
- ✓ Face alignment (rotation correction via eye positions) — v1.0
- ✓ Multi-face selection by index — v1.0
- ✓ TPS-based face shape morphing (~42 contour points) — v1.0
- ✓ Strength slider (0.0-1.0) for morph intensity — v1.0
- ✓ Interior feature anchoring (eyes, nose, mouth undistorted) — v1.0
- ✓ Face composite with feathered blending — v1.0
- ✓ Full pipeline end-to-end validated — v1.0
- ✓ macOS Apple Silicon compatibility — v1.0
- ✓ Dependencies: MediaPipe + scikit-image only — v1.0

### Active

(None — v1.0 complete)

### Out of Scope

- Face swap itself — handled by ReActor or other existing swap nodes
- Real-time video processing — batch image processing only
- Training or fine-tuning models — use pre-trained MediaPipe face mesh
- GPU-only operations — must work on CPU/MPS (Apple Silicon)
- 3D face reconstruction — overkill for proportion matching
- Color/lighting correction — separate concern for downstream nodes

## Context

Shipped v1.0 with 3,148 LOC Python across 21 files.
Tech stack: MediaPipe (face landmarks), scikit-image (TPS warp, affine transforms), PyTorch (tensor I/O).
4 face nodes under `imgtools/face` category in ComfyUI.
123 tests passing.

## Constraints

- **Platform**: Must run on macOS with Apple Silicon (MPS backend) — no CUDA-only dependencies
- **Ecosystem**: Must follow existing ComfyUI node conventions and tensor format [batch, h, w, channels]
- **Dependencies**: MediaPipe for face landmarks; avoid heavy dependencies that don't support Mac
- **Integration**: Nodes must be composable with existing ComfyUI workflow nodes (ReActor, etc.)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MediaPipe for face detection | 478 landmarks, Mac-compatible, no GPU needed | ✓ Good — works reliably |
| Split nodes (crop/morph/composite) | Flexibility, intermediate inspection, composability | ✓ Good — enables debugging |
| Feathered rect mask blending | Smooth transition, simpler than Poisson, good enough quality | ✓ Good — natural results |
| Face index selection | Match ReActor's UX, handle multi-face images | ✓ Good |
| Strength 0-1 slider | User control over morphing intensity | ✓ Good |
| TPS with ~42 contour points | Face oval + eyebrow endpoints only, no interior features | ✓ Good — shape without distortion |
| Procrustes alignment (scale-normalizing) | Pose-invariant shape delta, separate head_scale | ✓ Good |
| Direct paste composite (no reverse warp) | Morphed face is already correct, just paste at crop_box | ✓ Good — simplest approach |
| scikit-image only (no OpenCV) | Lighter dependency, Mac-friendly | ✓ Good |

---
*Last updated: 2026-03-11 after v1.0 milestone*
