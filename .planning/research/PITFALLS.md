# Domain Pitfalls: v1.1 Versatile Model

**Domain:** Adding 3D landmark normalization, multi-image canonical model averaging, and pose-aware morph diff application to existing 2D face morphing pipeline
**Researched:** 2026-03-11
**Focus:** Integration pitfalls with existing v1.0 codebase

---

## Critical Pitfalls

Mistakes that cause rewrites or major regression in the existing pipeline.

### Pitfall 1: Z-Coordinate Scale Mismatch Breaks 3D Pose Estimation

**What goes wrong:** MediaPipe's `landmarks_3d` Z coordinate is normalized by image width (same scale as X), not by any physical depth measure. Treating Z as a true metric depth and feeding it into rotation estimation produces wildly wrong pitch/yaw angles, especially for faces at different distances from the camera.

**Why it happens:** The Z values from MediaPipe use a weak perspective projection model. Developers assume Z is metric depth and apply rigid body rotation math that expects consistent 3D geometry. In reality, Z magnitude changes with face size in frame.

**Consequences:** Pose normalization rotates landmarks to incorrect "frontal" positions. Canonical model averaging then mixes incorrectly-normalized landmarks, producing a distorted average face shape. The entire model is garbage, but subtly -- it looks plausible until you composite onto a real face and get asymmetric or misshapen results.

**Prevention:**
- Normalize Z by inter-pupillary distance (IPD) before any rotation estimation, so Z is relative to face scale, not image scale.
- Validate pose estimation against known-pose test images (frontal, 15-degree, 30-degree yaw) before building the canonical model pipeline.
- Use MediaPipe's built-in `facial_transformation_matrixes` (available by setting `output_facial_transformation_matrixes=True` in FaceLandmarkerOptions) instead of manually computing pose from 3D points. This gives a 4x4 matrix from canonical face to detected face, which is exactly the rotation you need to invert.

**Detection:** Compare normalized-then-projected landmarks against original 2D landmarks. Large residuals (>5% of IED) indicate bad pose estimation.

**Phase:** Must be addressed in the 3D normalization foundation phase (earliest work).

### Pitfall 2: Existing 2D Procrustes Conflicts with New 3D Normalization

**What goes wrong:** The current `compute_morph_warp()` pipeline does: select control points -> Procrustes align (2D rotation + scale) -> symmetrize delta -> TPS warp. Adding 3D normalization creates a double-alignment problem: landmarks get pose-corrected once by the new 3D pipeline, then Procrustes tries to remove pose again, potentially introducing errors or negating the 3D correction.

**Why it happens:** The existing Procrustes alignment in `morph_utils.py` was designed to handle the case where source and target faces have different 2D poses. If the new canonical model already provides pose-free landmarks, running Procrustes on top of that is redundant at best and harmful at worst (the 2D Procrustes might "correct" real shape differences that look like rotation residuals).

**Consequences:** Morphing produces wrong deltas. The target shape stored in the canonical model is already normalized, but the source face still needs alignment. If both paths use Procrustes, the delta extraction is inconsistent. If only one does, there is a coordinate frame mismatch.

**Prevention:**
- Design the new FaceModelBuilder node to output landmarks in a clearly-defined normalized coordinate space (IPD-normalized, frontal-projected).
- When applying the model diff to a new source image, the source landmarks must be normalized to the SAME coordinate space before computing the delta. Then the delta is de-normalized back to the source's original pose/scale for TPS application.
- Keep the existing `compute_morph_warp()` UNTOUCHED for the v1.0 two-image workflow. Create a separate `compute_model_morph_warp()` function for the model-based workflow that replaces Procrustes with the new 3D-aware normalization.
- Never mix normalized and unnormalized landmarks in the same delta computation.

**Detection:** Unit test: apply canonical model to a perfectly frontal face. The delta should match what you get from the old 2D pipeline with the same frontal target. If they diverge, the normalization pipelines disagree.

**Phase:** Core integration phase -- must be designed before implementing either the model builder or the diff applicator.

### Pitfall 3: solvePnP Requires OpenCV -- Violates scikit-image-Only Constraint

**What goes wrong:** Nearly every head pose estimation tutorial and library for MediaPipe uses `cv2.solvePnP()` to compute pitch/yaw/roll from 3D landmarks. Developers reach for OpenCV instinctively. Adding OpenCV as a dependency breaks the project's explicit "scikit-image only (no OpenCV)" constraint, bloats the install, and may cause conflicts on Apple Silicon.

**Why it happens:** solvePnP is the standard tool for this job. Pure-numpy alternatives are not widely documented.

**Consequences:** Dependency bloat, potential platform issues, violation of architectural constraint established in v1.0.

**Prevention:**
- **Use MediaPipe's `facial_transformation_matrixes`** -- this is the strongest option. MediaPipe already computes a 4x4 transformation matrix from canonical face to detected face. Enable it with `output_facial_transformation_matrixes=True`. Extract rotation from this matrix using numpy (it is a standard 4x4 affine decomposition). No OpenCV needed.
- If `facial_transformation_matrixes` proves insufficient, implement a minimal PnP solver in pure numpy using Direct Linear Transform (DLT) -- this is ~50 lines of linear algebra (SVD-based), not the iterative Levenberg-Marquardt that OpenCV uses, but sufficient for 478-point face mesh where you have massive overdetermination.
- Add a CI check / import guard that fails if OpenCV is imported anywhere in the codebase.

**Detection:** `grep -r "import cv2" .` in CI. Also check transitive dependencies.

**Phase:** Must be resolved in the 3D normalization phase, before any pose estimation code is written.

### Pitfall 4: Naive Mean of Multi-Image Landmarks Produces Distorted Canonical Model

**What goes wrong:** Averaging landmarks across N images without proper outlier rejection, expression filtering, or weighting produces a "blurry" canonical face that represents no real face shape. Expressions (mouth open, squinting, raised eyebrows) shift landmarks dramatically. Even one image with an extreme expression corrupts the average.

**Why it happens:** Developers assume "more images = better model" and compute `np.mean(all_normalized_landmarks, axis=0)`. They forget that face shape (what we care about) varies far less than facial expression (what we do not care about). The 42 morph control points include eyebrow endpoints, which shift significantly with expression.

**Consequences:** The canonical model's contour points are smoothed toward an average expression, not an average shape. Morphing a source face toward this model produces unnatural proportions, especially around the jaw and brow.

**Prevention:**
- Use median instead of mean for each landmark coordinate independently. Median is robust to expression outliers (a single open-mouth image shifts the chin landmark, but the median across 10 images ignores it).
- Weight images by a "neutrality" score: use MediaPipe's blendshape scores (available via `output_face_blendshapes=True`) to detect expression. Images with high expression coefficients get low weight. Neutral-expression images dominate the average.
- After computing the average, apply the existing `_symmetrize_delta()` logic to enforce bilateral symmetry on the canonical model itself (a canonical model should be symmetric).
- Require a minimum of 5 images for a model; warn the user if fewer are provided.
- Show per-landmark variance in a debug output so the user can identify problematic images.

**Detection:** Check per-landmark standard deviation after normalization. Landmarks with stddev > 0.05 * IED suggest expression contamination or failed normalization in some images.

**Phase:** FaceModelBuilder node implementation phase.

---

## Moderate Pitfalls

### Pitfall 5: Control Point Set Mismatch Between Canonical Model and TPS Warp

**What goes wrong:** The canonical model stores all 478 normalized landmarks (needed for full face characterization), but the TPS warp uses only the 42 `MORPH_CONTROL_INDICES`. If the model-to-source delta is computed on the full 478 points but only the 42-point subset is used for warping, the delta at those 42 points may not accurately represent the shape difference (because Procrustes/normalization on 478 points produces different alignment than on 42 points).

**Prevention:**
- Store all 478 landmarks in the canonical model, but compute the canonical-to-source delta using ONLY the 42 `MORPH_CONTROL_INDICES` after normalization. This keeps the delta in the same landmark space the TPS warp expects.
- Alternatively, store both the full 478 and the pre-selected 42-point subset in the model file. Use the 42-point subset for morph delta, and the full set for future features (e.g., expression transfer).
- Add an assertion that the control point indices used for delta computation match `MORPH_CONTROL_INDICES` exactly.

**Phase:** Model file format design phase.

### Pitfall 6: Pose-Aware Diff Application Reverses Normalization Wrong

**What goes wrong:** The canonical model stores frontal-normalized landmarks. To apply the morph diff to a source image, you must: (1) normalize source landmarks to frontal, (2) compute delta in normalized space, (3) de-normalize the delta back to source's original pose. Step 3 is where things break -- developers apply the inverse rotation correctly but forget that the delta magnitude must also be de-normalized by the source's head scale.

**Why it happens:** In normalized space, landmarks are IPD-scaled (IED=1.0). The delta is in this normalized space. When projecting back to pixel space, the delta must be multiplied by the source's actual IED. Missing this step produces morphs that are either too subtle (large face) or too aggressive (small face).

**Consequences:** Morph strength varies with face size in the image, which is exactly the problem the existing `head_scale` mechanism in v1.0 was designed to handle. But the new model-based path has a different scale normalization, so the existing `head_scale` logic may not apply correctly.

**Prevention:**
- Define the delta pipeline explicitly: `delta_normalized = canonical_model_pts - normalize(source_pts)`. Then `delta_pixel = denormalize(delta_normalized, source_ied, source_pose)`.
- The denormalization must apply: (a) scale by source IED, (b) rotate by source pose (inverse of the frontal rotation), (c) translate to source center.
- Test with synthetic data: create a known canonical model, apply it to a source at 0-degree and 30-degree yaw, verify the pixel-space morphed landmarks are geometrically consistent.

**Phase:** Diff application phase (the node that uses the model at morph time).

### Pitfall 7: Model File Format Lacks Versioning or Metadata

**What goes wrong:** The canonical model is saved as a numpy array or JSON blob without version info, point count, normalization parameters, or the landmark indices used. Future changes to the normalization pipeline or control point set make old model files silently incompatible.

**Prevention:**
- Use a structured format (JSON or numpy .npz) with explicit metadata:
  ```
  {
    "version": "1.0",
    "num_images": 10,
    "landmark_count": 478,
    "control_indices": [...42 indices...],
    "normalization": "ipd_frontal_v1",
    "canonical_landmarks_478": [...],
    "canonical_control_42": [...],
    "head_dimensions": {...},
    "per_landmark_stddev": [...],
    "created": "2026-03-11"
  }
  ```
- Validate version on load. Reject or convert old formats explicitly.
- Include `per_landmark_stddev` so the diff applicator can optionally weight the morph by landmark confidence.

**Phase:** Model file format design (early in FaceModelBuilder work).

### Pitfall 8: Existing `_symmetrize_delta()` Becomes Redundant or Conflicting

**What goes wrong:** The current pipeline uses `_symmetrize_delta()` to remove yaw-induced asymmetry from the 2D shape delta. If the new 3D normalization already removes pose (including yaw), then `_symmetrize_delta()` either does nothing (wasted computation) or actively harms the result by symmetrizing real asymmetric shape differences that the 3D normalization correctly preserved.

**Why it happens:** The symmetrization was a 2D heuristic to compensate for information that 2D Procrustes cannot capture (perspective foreshortening from yaw). With proper 3D normalization, this information is handled upstream.

**Prevention:**
- In the model-based morph path, do NOT apply `_symmetrize_delta()`. The canonical model is already symmetric (or should be, per Pitfall 4).
- Keep `_symmetrize_delta()` in the existing v1.0 two-image path unchanged.
- Document clearly which code path uses which symmetry handling.

**Phase:** Integration/refactoring phase when creating the model-based morph function.

---

## Minor Pitfalls

### Pitfall 9: FaceLandmarker Cache Invalidation When Adding New Options

**What goes wrong:** The current `get_landmarker()` caches on `(min_detection_confidence, min_presence_confidence)`. Adding `output_facial_transformation_matrixes=True` and `output_face_blendshapes=True` for the model builder creates a different landmarker configuration. If the model builder runs first, the cached landmarker has these options. If the morph pipeline runs next, it reuses a landmarker with extra options enabled (minor perf waste) or, worse, the cache key does not include the new params and the wrong landmarker is returned.

**Prevention:**
- Include ALL configurable options in the `_landmarker_params` cache key tuple.
- Or create a separate landmarker factory for the model builder (preferred, since it processes batches of images and may want different settings).

**Phase:** When modifying `mediapipe_helper.py` to support transformation matrix output.

### Pitfall 10: Large Image Batches in Model Builder Exhaust Memory

**What goes wrong:** The FaceModelBuilder processes a directory of images. Loading all images simultaneously, or storing all 478x3 landmark arrays for hundreds of images, can exhaust memory -- especially on Apple Silicon machines with unified memory.

**Prevention:**
- Process images one at a time in a streaming fashion. Accumulate only the normalized landmark arrays (478x2 or 478x3 floats = ~4KB per image), not the images themselves.
- Set a sensible upper limit (e.g., 100 images) with a warning.
- Use incremental statistics (running mean/median) if the image count is very large.

**Phase:** FaceModelBuilder node implementation.

### Pitfall 11: Frontal Projection Loses Real Depth Information Needed for Profile Views

**What goes wrong:** Projecting 3D landmarks to frontal for canonicalization discards depth-dependent shape info (e.g., nose protrusion, brow ridge depth). When the canonical model is applied to a profile-view source, the morph tries to impose a frontal shape on a face seen from the side, which makes no geometric sense.

**Prevention:**
- The morph diff should only affect the face oval contour and eyebrow positions (the existing 42 control points), NOT depth-sensitive features like nose bridge.
- For extreme poses (yaw > 45 degrees), skip morphing or reduce strength automatically. Use the pose angle from `facial_transformation_matrixes` to detect this.
- Document the supported pose range (recommend < 30 degrees yaw for good results).

**Phase:** Diff application phase, with pose-based strength attenuation.

### Pitfall 12: Existing Test Suite Does Not Cover Model-Based Path

**What goes wrong:** The 123 existing tests validate the v1.0 two-image pipeline. New model-based code might pass its own tests but break the existing pipeline through shared utility changes. Especially risky: changes to `morph_utils.py`, `alignment.py`, or `mediapipe_helper.py`.

**Prevention:**
- Run the full existing test suite after every change to shared utilities.
- Add integration tests that verify the v1.0 pipeline produces identical output before and after v1.1 changes (regression test with known input/output pairs).
- Keep new model-based functions in separate modules where possible to minimize touching shared code.

**Phase:** Throughout all phases -- establish regression test baseline before starting v1.1 work.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| 3D normalization foundation | Z-coordinate scale mismatch (P1), OpenCV dependency (P3) | Use MediaPipe's transformation matrices, validate Z normalization with test images |
| FaceModelBuilder node | Expression contamination in averaging (P4), control point mismatch (P5), no versioning (P7) | Median + blendshape weighting, store both 478 and 42 point sets, structured file format |
| Model diff application | Dual-Procrustes conflict (P2), denormalization errors (P6), symmetrize redundancy (P8) | Separate morph function for model path, explicit normalize/denormalize pipeline, skip symmetrize |
| Integration / testing | Cache invalidation (P9), regression in v1.0 path (P12) | Include all options in cache key, regression test baseline |
| Edge cases | Profile view failure (P11), memory on large batches (P10) | Pose-based strength attenuation, streaming processing |

---

## Sources

- [MediaPipe Face Landmarker Python Guide](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python) -- transformation matrix and blendshape options (HIGH confidence)
- [MediaPipe Z coordinate normalization release notes](https://github.com/google/mediapipe/releases/tag/v0.7.6) -- Z uses weak perspective projection, scaled by image width (HIGH confidence)
- [MediaPipe Face Mesh wiki](https://github.com/google-ai-edge/mediapipe/wiki/MediaPipe-Face-Mesh) -- 3D coordinate meaning (HIGH confidence)
- [scikit-image TPS documentation](https://scikit-image.org/docs/stable/auto_examples/transform/plot_tps_deformation.html) -- TPS numerical considerations (MEDIUM confidence)
- [Procrustes analysis limitations for 2D vs 3D](https://arxiv.org/html/2409.16861v1) -- alignment pitfalls (MEDIUM confidence)
- Existing codebase analysis: `morph_utils.py`, `alignment.py`, `mediapipe_helper.py`, `face_morph.py`, `face_composite.py` (HIGH confidence)
