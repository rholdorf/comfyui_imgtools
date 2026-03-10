# Architecture Patterns

**Domain:** Face shape morphing nodes for ComfyUI
**Researched:** 2026-03-10

## Recommended Architecture

Three-node pipeline following ComfyUI conventions. Each node is stateless, receives inputs via `INPUT_TYPES`, returns outputs via `RETURN_TYPES`.

### Component Boundaries

| Component | Responsibility | Inputs | Outputs |
|-----------|---------------|--------|---------|
| FaceCropAlign | Detect face landmarks, rotate to upright, crop face region | IMAGE, face_index (INT), margin (FLOAT) | IMAGE (cropped), MASK, LANDMARKS (custom), TRANSFORM (custom) |
| FaceShapeMorph | Warp source face to match target face proportions via TPS | IMAGE (source crop), LANDMARKS (source), LANDMARKS (target), strength (FLOAT) | IMAGE (warped), MASK |
| FaceComposite | Paste warped face back into original image with blending | IMAGE (original), IMAGE (warped face), MASK, TRANSFORM | IMAGE (composited), MASK |

### Data Flow

```
Source Image --+---> [FaceCropAlign] ---> source_crop, source_landmarks, source_transform
               |
               |     Target Image ---> [FaceCropAlign] ---> target_crop, target_landmarks
               |
               |     source_crop + source_landmarks + target_landmarks
               |          |
               |          v
               |     [FaceShapeMorph] ---> warped_face, warp_mask
               |
               +---> [FaceComposite] <--- warped_face + source_transform + warp_mask
                          |
                          v
                    Final composited image + mask
```

### Custom Types

ComfyUI supports custom types as Python objects passed between nodes:

**LANDMARKS** -- Numpy array of shape (478, 2) containing face landmark pixel coordinates (denormalized from MediaPipe's normalized [0,1] format). Passed between FaceCropAlign and FaceShapeMorph.

**TRANSFORM** -- Dataclass containing: alignment affine matrix (2x3 numpy array), crop bounding box (x, y, w, h), original image dimensions (H, W), and rotation angle. Enables FaceComposite to reverse the crop and rotation.

## Patterns to Follow

### Pattern 1: Tensor Conversion Bridge
**What:** Convert between ComfyUI torch tensors and numpy arrays at node boundaries.
**When:** Every node entry and exit point.

```python
def process(self, image):
    # ComfyUI IMAGE: torch tensor [batch, H, W, C], float32, range [0, 1]
    img_np = image[0].cpu().numpy()  # (H, W, C), float32, [0, 1]

    # For MediaPipe: uint8 RGB
    img_uint8 = (img_np * 255).astype(np.uint8)

    # ... process ...

    # Back to ComfyUI tensor
    result = torch.from_numpy(result_np).unsqueeze(0)  # [1, H, W, C]
    return (result,)
```

### Pattern 2: Lazy Model Loading
**What:** Load MediaPipe model once, reuse across invocations.
**When:** FaceCropAlign node.

```python
_landmarker = None

def get_landmarker():
    global _landmarker
    if _landmarker is None:
        model_path = os.path.join(os.path.dirname(__file__), "models", "face_landmarker.task")
        options = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=10,
        )
        _landmarker = vision.FaceLandmarker.create_from_options(options)
    return _landmarker
```

### Pattern 3: Alignment via Eye-Line Rotation
**What:** Compute rotation angle from eye landmarks, apply affine transform.
**When:** FaceCropAlign, before cropping.

```python
def compute_alignment(landmarks, img_shape):
    # MediaPipe indices 468/473 = iris centers
    left_eye = landmarks[468]
    right_eye = landmarks[473]
    angle = np.degrees(np.arctan2(right_eye[1] - left_eye[1],
                                   right_eye[0] - left_eye[0]))
    center = ((left_eye[0] + right_eye[0]) / 2,
              (left_eye[1] + right_eye[1]) / 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return M, angle
```

### Pattern 4: Landmark Subset for TPS Control Points
**What:** Use ~60 contour + anchor landmarks, not all 478.
**When:** FaceShapeMorph.
**Why:** TPS solving is O(n^3). 478 points is slow; contour points are what define face shape.

```python
# Face oval contour indices from MediaPipe face mesh
FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
             397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
             172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]

# Feature anchors (eyes, nose, mouth) -- pinned to prevent distortion
ANCHORS = [33, 133, 362, 263, 1, 61, 291, 199]
```

### Pattern 5: Strength as Landmark Interpolation
**What:** Blend between source and target positions.

```python
morphed_points = source + strength * (target - source)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: All 478 Landmarks as TPS Points
**Why bad:** O(n^3) solve; ~1-2s per image. Interior landmarks (iris detail, nostril) don't affect face shape.
**Instead:** ~60 contour + anchor points.

### Anti-Pattern 2: Monolithic All-In-One Node
**Why bad:** Can't inspect intermediates; can't debug; can't compose with other nodes.
**Instead:** Three separate nodes with clean interfaces.

### Anti-Pattern 3: Storing State Between Invocations
**Why bad:** ComfyUI nodes are stateless by design. State causes bugs with re-execution.
**Instead:** Cache only the model, not results.

### Anti-Pattern 4: Warping the Entire Image
**Why bad:** Slow; TPS control points are only on face; distortion outside face region.
**Instead:** Crop face first, warp only the crop, composite back.

### Anti-Pattern 5: Legacy MediaPipe Face Mesh API
**Why bad:** `mediapipe.solutions.face_mesh` is deprecated; 468 landmarks vs 478 in new API.
**Instead:** `mediapipe.tasks.python.vision.FaceLandmarker`.

## Scalability Considerations

| Concern | Single image | Batch (10) | Batch (100+) |
|---------|-------------|-----------|-------------|
| MediaPipe inference | ~30ms | ~300ms | Cache target detection; only detect once |
| TPS solve (~60 pts) | ~5ms | ~50ms | Negligible |
| TPS warp (512x512) | ~20ms | ~200ms | Main bottleneck; reduce crop resolution if needed |
| Composite + blend | ~5ms | ~50ms | Negligible |
| Memory | ~50MB | ~100MB | Watch torch tensor accumulation |

## Sources

- [MediaPipe Face Landmarker Python](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python) -- task API
- [scikit-image TPS warp](https://scikit-image.org/docs/stable/auto_examples/transform/plot_tps_deformation.html)
- [MediaPipe face mesh landmark indices](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png)
