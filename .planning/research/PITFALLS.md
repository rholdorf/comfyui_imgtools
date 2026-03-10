# Domain Pitfalls

**Domain:** Face shape morphing nodes for ComfyUI on macOS/Apple Silicon
**Researched:** 2026-03-10

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Python Version Incompatibility with MediaPipe
**What goes wrong:** MediaPipe only supports Python 3.9-3.12. The system Python is 3.14. If ComfyUI runs on 3.13 or 3.14, mediapipe will not install from PyPI.
**Why it happens:** MediaPipe's C++ extensions require per-version compiled wheels. Google hasn't released wheels for 3.13+.
**Consequences:** Complete blocker -- no face detection means no product.
**Prevention:** Verify ComfyUI's actual Python version before any development. If 3.13+, either find community-built wheels (HuggingFace has some) or ensure ComfyUI uses a 3.12 venv.
**Detection:** `pip install mediapipe` fails with "no matching distribution found."

### Pitfall 2: TPS Warp with Too Many Control Points
**What goes wrong:** Using all 478 MediaPipe landmarks as TPS control points makes the solve O(n^3), taking 1-2 seconds per image. For batch processing, this becomes unusable.
**Why it happens:** Intuition says "more points = better quality." In reality, interior facial landmarks (iris detail, individual nostril points) don't contribute to face shape -- only the contour matters.
**Consequences:** 10-100x slower than necessary. Users abandon the tool.
**Prevention:** Use ~60 control points: face oval contour (~36 points) + key feature anchors (~8 points) + a few forehead/chin points. Pin interior features (eyes, nose, mouth centers) as fixed anchors to prevent distortion.
**Detection:** Profiling shows >500ms in TPS solve step.

### Pitfall 3: Feature Distortion During Shape Warping
**What goes wrong:** TPS warping the face contour also distorts eyes, nose, and mouth -- making the face look alien even though the shape matches.
**Why it happens:** TPS is a global smooth interpolation. Moving jawline points pulls nearby features.
**Consequences:** Morphed faces look uncanny; defeats the purpose.
**Prevention:** Pin eye corners, nose tip, and mouth corners as anchored control points (same source and target position). This constrains the warp to affect only the shape, not the features. Use regularization parameter on TPS if available.
**Detection:** Eyes/nose/mouth shift position or stretch after warping.

### Pitfall 4: Landmark Coordinate Space Mismatch
**What goes wrong:** MediaPipe returns normalized coordinates [0, 1]. scikit-image TPS expects pixel coordinates. Mixing these produces invisible, wrong, or catastrophic warps.
**Why it happens:** Two different libraries with different conventions. Easy to forget the conversion.
**Consequences:** Warp is applied to wrong positions; face is destroyed or unchanged.
**Prevention:** Denormalize immediately after detection: `pixel_x = landmark.x * image_width`. Establish a single canonical coordinate space (pixel coords) and convert once at the boundary.
**Detection:** Warped face is distorted beyond recognition or appears unchanged.

### Pitfall 5: Compositing Seam Artifacts
**What goes wrong:** The boundary where warped face meets original image shows a visible seam -- hard edge, color mismatch, or ghosting.
**Why it happens:** Direct pixel replacement without blending; mask edge is too sharp; color/brightness difference between warped region and background.
**Consequences:** Result is obviously fake and unusable.
**Prevention:** Gaussian-blur the mask edge (feathering radius ~10-20 pixels). Expand the face crop region with padding so the blending zone is on background, not face features. Alpha-blend using the soft mask: `output = warped * mask + original * (1 - mask)`.
**Detection:** Visible hard edge around face in output.

## Moderate Pitfalls

### Pitfall 1: Rotation Artifacts from Face Alignment
**What goes wrong:** Rotating the image to align the face creates black triangular regions at corners. These get included in the crop and bleed into the morph.
**Prevention:** Use `cv2.warpAffine` with `borderMode=cv2.BORDER_REPLICATE` or crop inside the valid region. Ensure crop bounding box stays within the rotated image bounds.

### Pitfall 2: Face Detection Failure on Extreme Angles
**What goes wrong:** MediaPipe fails to detect faces at extreme profile angles (>60 degrees) or heavy occlusion. Node returns no landmarks.
**Prevention:** Return the original image unchanged when no face is detected (fail gracefully). Log a warning. Don't error out.

### Pitfall 3: Source/Target Landmark Count Mismatch
**What goes wrong:** Source image has landmarks from a detected face; target image has different resolution or detected face at different scale. Direct landmark position comparison is meaningless without normalization.
**Prevention:** Always work with normalized coordinates when comparing source and target, then denormalize to each image's pixel space for actual warping. The morph should match proportional relationships, not absolute positions.

### Pitfall 4: opencv-python vs opencv-contrib-python Conflict
**What goes wrong:** If you install `opencv-contrib-python` alongside ComfyUI's `opencv-python`, pip will either refuse or create a broken state (both provide the `cv2` namespace).
**Prevention:** Don't use opencv-contrib. Use scikit-image for TPS instead. If you need OpenCV's TPS for any reason, install `opencv-contrib-python-headless` which can coexist.

### Pitfall 5: Model File Distribution
**What goes wrong:** MediaPipe's Face Landmarker requires a `face_landmarker.task` file (~4MB). If not bundled, users get a runtime error on first use.
**Prevention:** Auto-download the model file on first use (like many ComfyUI nodes do). Cache in `models/` subdirectory. Provide clear error message if download fails.

## Minor Pitfalls

### Pitfall 1: Batch Dimension Handling
**What goes wrong:** Forgetting that ComfyUI IMAGE tensors are [batch, H, W, C]. Processing only index 0 and returning [1, H, W, C] drops remaining batch items.
**Prevention:** Loop over batch dimension explicitly. For V1, document that only batch[0] is processed.

### Pitfall 2: Float32 vs Uint8 Image Format
**What goes wrong:** ComfyUI uses float32 [0, 1]; OpenCV functions often expect uint8 [0, 255]; MediaPipe expects uint8 RGB. Silent type mismatches produce dark or saturated images.
**Prevention:** Explicit conversion at boundaries. Use helper functions: `to_uint8()`, `to_float32()`, `to_comfy_tensor()`.

### Pitfall 3: BGR vs RGB Color Space
**What goes wrong:** OpenCV uses BGR by default. MediaPipe and ComfyUI use RGB. Swapping red and blue channels makes skin look blue.
**Prevention:** Never assume color order. Convert explicitly: `cv2.cvtColor(img, cv2.COLOR_BGR2RGB)` when reading from OpenCV, but ComfyUI tensors are already RGB -- don't double-convert.

### Pitfall 4: Memory Leak from MediaPipe Context Manager
**What goes wrong:** MediaPipe's FaceLandmarker should be used as a context manager (`with ... as landmarker`). If not closed, it leaks memory across invocations.
**Prevention:** Use module-level singleton with lazy initialization (Pattern 2 from ARCHITECTURE.md). Alternatively, use `with` statement per invocation if caching proves problematic.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Setup / deps | Python 3.14 vs MediaPipe 3.12 | Verify ComfyUI's Python version FIRST |
| Face detection | Model file not found | Auto-download face_landmarker.task |
| Crop & align | Rotation black corners | BORDER_REPLICATE, crop inside valid region |
| TPS warping | Feature distortion | Pin eye/nose/mouth as fixed anchors |
| TPS warping | Too many control points | Use ~60 contour points, not 478 |
| Compositing | Seam artifacts | Gaussian-blur mask, expand crop padding |
| Integration | opencv package conflicts | Use scikit-image TPS, not opencv-contrib |

## Sources

- [MediaPipe PyPI](https://pypi.org/project/mediapipe/) -- Python version support (3.9-3.12)
- [MediaPipe Python 3.13 issue](https://github.com/google-ai-edge/mediapipe/issues/6159) -- no 3.13 support
- [TPS Warping tutorial](https://khanhha.github.io/posts/Thin-Plate-Splines-Warping/) -- control point selection
- [OpenCV TPS issues](https://github.com/opencv/opencv/issues/7084) -- known bugs in OpenCV TPS
- [LearnOpenCV face morph](https://learnopencv.com/face-morph-using-opencv-cpp-python/) -- compositing best practices
- [OpenCV seamlessClone](https://docs.opencv.org/4.x/df/da0/group__photo__clone.html) -- Poisson blending alternative
