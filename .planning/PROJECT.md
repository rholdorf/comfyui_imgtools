# ComfyUI Face Shape Matcher

## What This Is

A set of ComfyUI custom nodes that pre-process face geometry before face swapping. The nodes deform/morph a source face to match the shape and proportions of a target face, solving the common problem where face swap tools (like ReActor) replace features but preserve the original face shape — leading to uncanny results when face shapes differ significantly. Built as an extension to the existing comfyui_imgtools project.

## Core Value

Morph the source face shape to match the target face proportions so that downstream face swap produces natural-looking results regardless of face shape differences.

## Requirements

### Validated

- ✓ ImageDimensionFitter node — existing
- ✓ ImagePaddingCalculator node — existing
- ✓ PathSplitter node — existing

### Active

- [ ] Face crop & align node — detect face landmarks with MediaPipe, crop face region, align to upright orientation
- [ ] Face shape morph node — warp cropped/aligned source face to match target face proportions (jaw/chin, width/height ratio, forehead, full head silhouette)
- [ ] Face composite node — paste morphed face back into original image with feathered mask blending
- [ ] Strength parameter (0-1 slider) — control how much morphing is applied, from no change to full match
- [ ] Face index selection — let user pick which face to process by index when multiple faces detected
- [ ] Output full image + cropped face + mask from each node for inspection and downstream use
- [ ] Mac / Apple Silicon / MLX compatibility — all processing must work on macOS without CUDA
- [ ] Handle tilted/rotated faces — align before morphing, de-align after compositing

### Out of Scope

- Face swap itself — handled by ReActor or other existing swap nodes
- Real-time video processing — batch image processing only
- Training or fine-tuning models — use pre-trained MediaPipe face mesh
- GPU-only operations — must work on CPU/MPS (Apple Silicon)

## Context

- This extends the existing comfyui_imgtools custom node package
- Existing nodes follow ComfyUI convention: stateless, INPUT_TYPES/RETURN_TYPES, IMAGE tensors [batch, h, w, c]
- Target workflow: source image → face shape match nodes → ReActor face swap → output
- Similar nodes exist (FaceShaper series) but don't work on Mac
- MediaPipe chosen for face detection: 468 landmarks, runs well on Mac, no GPU required
- Deformation approach: best technique for quality (thin-plate spline, mesh warp, or hybrid — to be determined during research)
- Split node design chosen over all-in-one for flexibility and intermediate inspection

## Constraints

- **Platform**: Must run on macOS with Apple Silicon (MPS backend) — no CUDA-only dependencies
- **Ecosystem**: Must follow existing ComfyUI node conventions and tensor format [batch, h, w, channels]
- **Dependencies**: MediaPipe for face landmarks; avoid heavy dependencies that don't support Mac
- **Integration**: Nodes must be composable with existing ComfyUI workflow nodes (ReActor, etc.)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MediaPipe for face detection | 468 landmarks, Mac-compatible, no GPU needed | — Pending |
| Split nodes (crop/morph/composite) | Flexibility, intermediate inspection, composability | — Pending |
| Feathered mask blending | Smooth transition, simpler than Poisson, good enough quality | — Pending |
| Face index selection | Match ReActor's UX, handle multi-face images | — Pending |
| Strength 0-1 slider | User control over morphing intensity | — Pending |

---
*Last updated: 2026-03-10 after initialization*
