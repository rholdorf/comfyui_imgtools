# Feature Landscape: v1.1 Versatile Model

**Domain:** Multi-image canonical face model building, 3D landmark normalization, pose-aware morph application
**Researched:** 2026-03-11
**Builds on:** v1.0 (FaceDetect, FaceCropAlign, FaceShapeMorph, FaceComposite -- all shipped)

## Table Stakes

Features that make v1.1 actually useful. Without these, multi-image model building is incomplete.

| Feature | Why Expected | Complexity | Dependencies on v1.0 |
|---------|--------------|------------|----------------------|
| FaceModelBuilder node (multi-image input) | Core value of v1.1 -- build a canonical face from N target images instead of one. Without this, user is limited to single-image-to-image morph. | High | Reuses FaceDetect internally for landmark extraction |
| 3D pose extraction from MediaPipe matrix | Required to normalize away head pose before averaging. Enable `output_facial_transformation_matrixes=True` to get 4x4 matrix per face. | Low | One-line config change to `get_landmarker()` |
| Pose-normalized (frontalized) landmarks | Each image's landmarks must be de-rotated to canonical frontal view before averaging. Uses inverse of MediaPipe's 4x4 matrix via scipy Rotation. | Med | New `pose_utils.py`; uses scipy.spatial.transform.Rotation (already installed) |
| IPD-based scale normalization | Faces at different distances/resolutions must be size-normalized. Inter-pupil distance (IPD) is the standard reference. | Low | `normalize_landmarks()` in `morph_utils.py` already does this for 2D. Extend to 3D. |
| Weighted averaging of normalized landmarks | Average the frontalized, IPD-normalized landmarks across N images. Weight by cos(yaw)*cos(pitch)*confidence for quality. | Med | Straightforward numpy weighted mean |
| Persistent model file format (.npz) | Save canonical model to disk so it can be reloaded without reprocessing. Users build once, morph many. ~6KB per model. | Low | `numpy.savez_compressed` / `numpy.load` with `allow_pickle=False` |
| Pose-aware diff application | When applying model shape to source, delta must respect source's current pose. Cannot blindly apply frontal diff to 3/4 view. | High | Modifies `compute_morph_warp()` in `morph_utils.py` |
| Head size estimation from model | Canonical model carries average head dimensions (IPD-relative) so FaceComposite can scale correctly. | Low | Model stores average; passed via align_data |
| Directory/batch image input | User provides folder path or image batch. Node iterates, detects, builds model. | Med | Uses pathlib.Path.glob() for directory listing |

## Differentiators

Features beyond basic functionality that add real quality.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Automatic pose-based rejection | Reject images where face yaw > threshold (e.g., 45-60 deg). Extreme poses have unreliable landmarks. | Low | Threshold on Euler yaw from 4x4 matrix decomposition |
| Per-image confidence weighting | Weight near-frontal images higher when averaging. Formula: `cos(yaw) * cos(pitch) * detection_confidence`. | Low | Simple formula, big quality gain over unweighted mean |
| Model preview/visualization | Output landmark plot showing canonical shape. Verify model quality before applying. | Low | Reuse existing `draw_landmarks_on_image` on blank canvas |
| Pose quality report | Output metadata: which images used/rejected, per-image yaw/pitch/roll, confidence. | Low | Structured dict output for debugging |
| FaceModelMorph as separate node | Dedicated node for model-based morphing (cleaner UX than overloading FaceShapeMorph). | Med | Alternative to modifying FaceShapeMorph; see Architecture discussion |

## Anti-Features

Features to explicitly NOT build in v1.1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full 3D face reconstruction | Overkill. Need 3D only for pose removal, not rendering. | Use MediaPipe's 4x4 matrix for pose; pure linear algebra, no 3D renderer. |
| OpenCV dependency for solvePnP | Project constraint: no OpenCV. Unnecessary because MediaPipe provides the matrix. | Enable `output_facial_transformation_matrixes=True` -- done. |
| Neural network pose estimator (6DRepNet, WHENet) | Extra model, GPU overhead, complexity. | MediaPipe's matrix gives pitch/yaw/roll with no extra model. |
| Face identity clustering | Multi-person directory is a face recognition problem (InsightFace territory). | Require single-person input or user-specified face index. Document limitation. |
| Blendshape/expression normalization | Full solution needs blendshape decomposition -- different problem domain. | Document: recommend neutral-expression photos. Outlier rejection handles extreme cases. |
| Incremental model building | Adding images to existing model without reprocessing is nice but adds complexity. | Ship rebuild-from-scratch first. Store per-image data in npz for future incremental support. |
| Region-selective morphing | Not critical for v1.1; multi-image model is the priority. | Keep as v1.2 candidate. |

## Feature Dependencies

```
Existing v1.0 Pipeline (unchanged):
  FaceDetect -> FaceCropAlign -> FaceShapeMorph -> FaceComposite

New v1.1 Model Building Pipeline:

  [Directory of images]
         |
         v
  FaceModelBuilder
    - For each image:
      1. FaceDetect (reuse existing node logic)
      2. Get facial_transformation_matrix (enable flag in MediaPipe options)
      3. Extract pose (pitch/yaw/roll from 4x4 matrix via scipy.Rotation)
      4. Reject if extreme pose or low confidence
      5. De-rotate landmarks to frontal (inverse rotation via scipy.Rotation.inv())
      6. IPD-normalize (scale so IED = 1.0)
    - Weighted average all normalized landmarks
    - Store: canonical_landmarks, avg_head_dimensions, metadata
         |
         v
  FACE_MODEL output (+ save to .facemodel.npz)

New v1.1 Morph Pipeline:

  FaceDetect (source image, with transformation matrix)
         |
         v
  FaceCropAlign (source image)
         |
         v
  FaceModelMorph  <---- FACE_MODEL input
    - Estimate source pose from its transformation_matrix
    - Normalize source landmarks to canonical space
    - Compute shape delta: canonical_model - source_normalized
    - Scale delta back to source pixel space (multiply by source IPD)
    - Apply via TPS (reuse existing warp infrastructure)
         |
         v
  FaceComposite (unchanged from v1.0)
```

Key dependency chain for implementation:
```
Enable transformation matrix in MediaPipe (foundation)
  -> pose_utils.py: extract Euler angles, de-rotate landmarks
    -> model_io.py: NPZ save/load
      -> FaceModelBuilder node (uses pose_utils + model_io)
    -> Pose-aware diff in morph_utils.py (uses pose_utils)
      -> FaceModelMorph node (uses diff application)
```

## MVP Recommendation for v1.1

Prioritize (minimum viable multi-image model):

1. **Enable transformation matrix output** -- One-line change to `get_landmarker()`. Foundation for everything.

2. **Pose utilities (pose_utils.py)** -- Extract Euler angles from 4x4 matrix via scipy.Rotation. De-rotate landmarks to frontal via inverse. Core math module.

3. **Model I/O (model_io.py)** -- Save/load canonical model as .npz. Straightforward but must be defined early so model format is stable.

4. **FaceModelBuilder node** -- Process directory, detect, normalize, average, save. Main new user-facing node.

5. **FaceModelMorph node** -- Accept FACE_MODEL, compute pose-aware delta, apply via TPS. Main integration with existing pipeline.

6. **Head size in model** -- Store average head dimensions. Pass through to FaceComposite.

Defer to v1.1.1 or v1.2:
- **Incremental model building**: Rebuild-from-scratch first.
- **Model preview/visualization**: Nice to have but not blocking.
- **Per-image confidence weighting**: Start with cos(yaw)*cos(pitch) weighting. Statistical weighting later.

## Complexity Assessment

| Feature | Estimated Effort | Risk Level | Notes |
|---------|-----------------|------------|-------|
| Enable transformation matrix output | Tiny (config change) | Low | One boolean in `get_landmarker()` |
| Pose decomposition (4x4 matrix -> Euler) | Small (utility function) | Low | scipy.Rotation handles this cleanly |
| Landmark de-rotation to frontal | Small (matrix multiply) | Low | `pts_3d @ R_inv.T` -- verified working |
| Model I/O (npz save/load) | Small | Low | Verified round-trip at ~6KB |
| FaceModelBuilder node | Medium (orchestration) | Medium | Mostly wiring existing pieces together |
| Pose-aware diff application | High (core algorithm) | High | Hardest part -- delta must respect source pose |
| FaceModelMorph node | Medium (new node) | Low | Thin wrapper once diff application works |

## Sources

- MediaPipe `output_facial_transformation_matrixes`: verified via `help(vision.FaceLandmarkerOptions)` on mediapipe 0.10.18 (HIGH confidence)
- MediaPipe `facial_transformation_matrixes: List[numpy.ndarray]`: verified via `inspect.getmembers()` (HIGH confidence)
- scipy.spatial.transform.Rotation: verified round-trip Euler decomposition with scipy 1.12.0 (HIGH confidence)
- numpy.savez_compressed: verified round-trip at 6KB with numpy 1.26.4 (HIGH confidence)
- [MediaPipe 3D Face Transform](https://developers.googleblog.com/mediapipe-3d-face-transform/) -- Procrustes analysis for pose matrix
- [SciPy Rotation docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.html)
