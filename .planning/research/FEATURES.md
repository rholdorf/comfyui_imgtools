# Feature Landscape

**Domain:** Face shape morphing / pre-processing for face swap workflows in ComfyUI
**Researched:** 2026-03-10

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Face landmark detection | Foundation of everything -- can't morph without landmarks | Med | MediaPipe Face Landmarker, 478 points, CPU-native |
| Face crop & alignment | Morphing on aligned faces produces far better results; tilted faces break warping | Med | Rotate to upright based on eye positions, crop bounding box with margin |
| Face shape warping | Core value proposition -- deform source face to match target proportions | High | TPS warp using landmark subsets (jawline, forehead, cheeks) |
| Face compositing back | Morphed face must go back into the original image seamlessly | Med | Inverse rotation, feathered mask blending at edges |
| Strength slider (0-1) | Users need control over morph intensity; full match can look unnatural | Low | Linear interpolation between source and target landmark positions |
| Multi-face support | Images often have multiple faces; user needs to pick which one | Low | Face index parameter (integer), MediaPipe returns multiple faces |
| Mask output | Users need masks for downstream compositing or manual touchup | Low | Output soft mask of face region alongside processed image |
| Mac / Apple Silicon compatibility | Project constraint; FaceShaper doesn't reliably work on Mac | Med | All deps must have macOS ARM64 wheels; no CUDA-only operations |

## Differentiators

Features that set this apart from ComfyUI_FaceShaper and similar.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Split node architecture | Inspect intermediates, swap individual steps, compose with other nodes. FaceShaper V1 was monolithic. | Low (design choice) | Three nodes: FaceCropAlign, FaceShapeMorph, FaceComposite |
| Mac-first / Apple Silicon native | FaceShaper has no explicit Mac support; this project targets Mac first | Low | MediaPipe + scikit-image both have ARM64 wheels |
| No non-commercial deps | FaceShaper's Insightface has license restrictions | Low | MediaPipe only (Apache 2.0) |
| Landmark debug visualization | Visual overlay of detected landmarks + warp vectors for debugging | Low | Optional output showing landmarks on face |
| Region-selective morphing | Morph only jaw, forehead, or face width -- not all-or-nothing | Med | Region weights: jaw (0-1), forehead (0-1), cheeks (0-1) |
| Full image + cropped face dual output | Output both composited result AND isolated face from each node | Low | Enables inspection and downstream flexibility |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Face swap | ReActor and others handle this; duplicating adds massive scope | Output morphed faces that feed into existing swap nodes |
| Video/real-time processing | Temporal consistency, optical flow -- massive complexity | Process individual frames; users use ComfyUI video nodes |
| Model training/fine-tuning | Unnecessary; MediaPipe pre-trained model is sufficient | Use pre-trained face_landmarker.task as-is |
| 3D face reconstruction | Overkill for proportion matching; heavy deps, GPU needs | 2D landmark-based TPS warping is sufficient |
| InsightFace as detector | Non-commercial license, CUDA-preferring, heavy dependency | MediaPipe as sole detector |
| Color/lighting correction | Separate concern from geometry; post-swap problem | Let downstream nodes handle color |
| Animated morph sequences | Different product entirely (morph video generation) | Single-shot warp: source geometry to target geometry |

## Feature Dependencies

```
Face Landmark Detection (MediaPipe)
  |
  v
Face Crop & Align -----> outputs: cropped face, alignment transform, mask
  |
  v
Face Shape Morph ------> outputs: warped face, warp field
  |                      (requires source AND target landmarks)
  v
Face Composite --------> outputs: full image with warped face composited back
                         (requires original image, alignment transform, mask)
```

Critical path: Detection -> Crop/Align -> Morph -> Composite. Must ship together.

Independent additions: Landmark visualization, region-selective weights, Poisson blending toggle.

## MVP Recommendation

Prioritize (ship together as minimum viable pipeline):
1. **Face Crop & Align node** -- detect landmarks, rotate to upright, crop with padding
2. **Face Shape Morph node** -- TPS warp between landmark sets with strength slider
3. **Face Composite node** -- paste back with feathered mask, output full image + mask
4. **Face index selection** -- integer input on crop node (trivial)

Defer:
- **Region-selective morphing**: Ship full-face morph first; add per-region weights later
- **Landmark visualization**: Debugging aid; add when tuning morph quality
- **Poisson blending**: Feathered mask is simpler and predictable for V1

## Sources

- [ComfyUI_FaceShaper](https://github.com/fssorc/ComfyUI_FaceShaper) -- competitor analysis
- [MediaPipe Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) -- 478 landmarks
- [LearnOpenCV Face Morph](https://learnopencv.com/face-morph-using-opencv-cpp-python/) -- standard pipeline reference
- [OpenCV seamlessClone](https://docs.opencv.org/4.x/df/da0/group__photo__clone.html) -- Poisson blending reference
