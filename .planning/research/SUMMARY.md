# Project Research Summary

**Project:** comfyui_imgtools v1.1 — Versatile Model
**Domain:** Multi-image canonical face model building with 3D pose normalization
**Researched:** 2026-03-11
**Confidence:** HIGH

## Executive Summary

v1.1 extends the existing four-node face morphing pipeline (FaceDetect, FaceCropAlign, FaceShapeMorph, FaceComposite) with two new nodes: `FaceModelBuilder`, which processes a directory of images to build a persistent canonical face model, and `FaceModelMorph`, which applies that model to a source image using pose-aware shape diffing. The core technical challenge — head pose extraction and normalization — is solved without any new dependencies: MediaPipe 0.10.18 already provides a 4x4 transformation matrix per detected face, available by setting one boolean flag (`output_facial_transformation_matrixes=True`). SciPy's `Rotation` class (already installed as a transitive dependency) decomposes that matrix into pitch/yaw/roll and computes the inverse for landmark de-rotation. Model persistence uses NumPy's `.npz` format, producing ~6 KB files safely without pickle.

The recommended architecture is strictly additive: all new capabilities live in new modules (`pose_utils.py`, `model_io.py`, `face_model_builder.py`, `face_model_morph.py`) with only three minimal, backward-compatible changes to existing shared utilities (`mediapipe_helper.py`, `landmarks.py`, `morph_utils.py`). The v1.0 two-image pipeline is preserved unchanged and carries zero regression risk. The new model-based workflow uses a distinct coordinate-space pipeline — canonical (frontal, IPD-normalized) for averaging and delta computation, pixel-space for TPS warp application — which must not be conflated with the existing 2D Procrustes alignment. `FaceModelMorph` is a separate node from `FaceShapeMorph`, not an overloaded variant.

The primary implementation risk is the pose-aware diff application: the delta is computed in canonical space but must be de-normalized back to the source's pixel space by applying the source's IPD scale and pose rotation in the correct order. Expression contamination in multi-image averaging is the secondary risk, mitigated by using median over mean and weighting by `cos(yaw) * cos(pitch)`. Both risks have clear prevention strategies verified against the installed dependency stack.

## Key Findings

### Recommended Stack

No new dependencies are required. The entire v1.1 feature set is achievable with the stack already installed and verified in the `comfyui` conda environment. The key discovery is that MediaPipe 0.10.18 already provides head pose as a 4x4 matrix — eliminating the need for `cv2.solvePnP` or any custom SVD-based pose estimator that would have been the default approach.

**Core technologies:**
- **MediaPipe 0.10.18**: Face landmark detection + 4x4 transformation matrix — enable via `output_facial_transformation_matrixes=True` (verified API via introspection)
- **SciPy 1.12.0 `Rotation`**: Matrix-to-Euler decomposition and inverse rotation — already installed as scikit-image transitive dep; round-trip verified
- **NumPy 1.26.4**: 3D landmark math, IPD normalization, `.npz` model persistence — round-trip verified at ~6 KB with `allow_pickle=False`
- **scikit-image 0.24.0**: TPS warp infrastructure — unchanged from v1.0
- **PyTorch (ComfyUI)**: Tensor I/O bridge — unchanged from v1.0

### Expected Features

**Must have (table stakes):**
- `FaceModelBuilder` node: process image directory, detect landmarks, normalize to canonical space, average, save `.facemodel.npz`
- 3D pose extraction from MediaPipe's 4x4 matrix via SciPy Rotation
- Landmark frontalization (de-rotation to canonical pose-free space)
- IPD-based scale normalization for cross-image comparability
- Weighted landmark averaging (weight by `cos(yaw) * cos(pitch)`)
- Persistent model file format (`.facemodel.npz`, ~6 KB, with version/metadata)
- Automatic rejection of extreme-pose images (yaw threshold ~45-60 degrees)
- `FaceModelMorph` node: accepts `FACE_MODEL`, computes pose-aware delta, applies via TPS warp
- Head size estimation stored in model for correct FaceComposite scaling

**Should have (competitive differentiators):**
- Per-image quality report: images used/rejected, per-image yaw/pitch/roll, confidence scores
- Model preview output: landmark plot on blank canvas for model validation before use
- Pose-based strength attenuation: auto-reduce morph strength for source faces with high yaw

**Defer to v1.2+:**
- Incremental model building (add images without full reprocessing)
- Region-selective morphing
- Blendshape/expression normalization (requires blendshape decomposition — different problem domain)
- Multi-person directory support (requires face identity clustering — InsightFace territory)

### Architecture Approach

The architecture follows a strict additive pattern: new nodes and utility modules are added without modifying the v1.0 pipeline. `FaceModelMorph` is a separate node from `FaceShapeMorph` (not an overloaded variant) — enabling clean `INPUT_TYPES`, single responsibility, and zero regression risk. All shape comparisons happen in a canonical coordinate space (frontal, IPD-normalized) that is explicitly defined and used consistently across both model building and model application. The model file format is structured from day one with version metadata to prevent silent format incompatibilities.

**Major components:**
1. `utils/pose_utils.py` (NEW) — `extract_pose()` from 4x4 matrix, `frontalize_landmarks()` via inverse rotation
2. `utils/model_io.py` (NEW) — NPZ save/load with version metadata, `allow_pickle=False`
3. `face_model_builder.py` (NEW) — ComfyUI node: directory input, detect/normalize/average/save, `FACE_MODEL` output type
4. `face_model_morph.py` (NEW) — ComfyUI node: `FACE_MODEL` + `FACE_LANDMARKS` input, pose-aware delta, same output interface as `FaceShapeMorph`
5. `utils/morph_utils.py` (MODIFIED, additive) — add `compute_model_morph_warp()` alongside existing function; never remove or alter existing function
6. `utils/mediapipe_helper.py` (MODIFIED, additive) — new `output_transformation_matrix` param; update cache key to include it
7. `utils/landmarks.py` (MODIFIED, additive) — include `transformation_matrix` in face dict when present

### Critical Pitfalls

1. **Z-coordinate scale mismatch** — MediaPipe's Z is normalized by image width (weak perspective), not metric depth. Never feed raw Z into rotation estimation. Use the 4x4 transformation matrix directly — it already handles this internally. Validate frontalization against known-pose test images before building the averaging pipeline.

2. **Dual-Procrustes conflict** — The existing `compute_morph_warp()` runs 2D Procrustes alignment. The new model-based path must NOT use Procrustes — the canonical model is already pose-free. Solve by keeping `compute_morph_warp()` untouched and creating a separate `compute_model_morph_warp()` that uses the 3D pipeline. Never mix normalized and unnormalized landmarks in a single delta computation.

3. **OpenCV dependency violation** — `cv2.solvePnP` is the instinctive tool for head pose but violates the project's no-OpenCV constraint and is unnecessary here. MediaPipe's 4x4 matrix eliminates the need entirely.

4. **Expression contamination in averaging** — Naive `np.mean()` across images corrupts the canonical model with expression variation. Use median (robust to expression outliers) or weighted mean with `cos(yaw) * cos(pitch)`. Require minimum 5 images; warn if fewer provided.

5. **Denormalization order error in diff application** — The shape delta is in canonical space (IPD=1.0, frontal). De-normalization back to pixel space must apply: (a) scale by source IED, (b) rotate by source pose. Reversing the order or omitting either step produces scale- or pose-dependent morph artifacts. Test with synthetic known-pose data before integrating.

## Implications for Roadmap

Based on the dependency chain identified in research: `pose_utils` is the foundation for everything. The model file format must be defined early to avoid rework. The hardest piece — pose-aware diff application — should come last when all infrastructure is solid and testable.

### Phase 1: 3D Pose Foundation

**Rationale:** The transformation matrix output from MediaPipe, plus pose decomposition and frontalization utilities, are prerequisites for both FaceModelBuilder and FaceModelMorph. This is the narrowest change with the highest leverage — it enables everything else without adding user-facing nodes yet.
**Delivers:** `pose_utils.py` (`extract_pose`, `frontalize_landmarks`), updated `mediapipe_helper.py` (new param + cache key update) and `landmarks.py` (include matrix in face dict), unit tests with synthetic 4x4 matrices.
**Addresses:** Table-stakes: 3D pose extraction, landmark frontalization, 3D extension of IPD normalization.
**Avoids:** Pitfall 1 (Z-scale — use matrix, not raw Z), Pitfall 3 (OpenCV — not needed), Pitfall 9 (cache invalidation — include new param in key from day one).

### Phase 2: Model File Format

**Rationale:** The model file format must be stable before FaceModelBuilder writes to it and FaceModelMorph reads from it. Defining format early, with versioning, prevents silent incompatibilities when either side changes.
**Delivers:** `model_io.py` (`save_face_model`, `load_face_model`), `.facemodel.npz` format storing canonical_landmarks (478, 2), head_dimensions (3,), version metadata, per-landmark stddev, and control_indices (42); round-trip tests confirming dtype/shape preservation.
**Addresses:** Table-stakes: persistent model format, head size in model.
**Avoids:** Pitfall 5 (control point mismatch — model stores both 478-point and 42-point subsets), Pitfall 7 (no versioning — explicit version field and load-time validation from the start).

### Phase 3: FaceModelBuilder Node

**Rationale:** With pose utilities and model I/O in place, the builder node is primarily orchestration — detect, normalize, average, save. The algorithmic pieces exist; this phase wires them together into a user-facing ComfyUI node.
**Delivers:** `face_model_builder.py` with `FaceModelBuilder` node, `FACE_MODEL` custom type registered in `__init__.py`, streaming per-image processing (no batch-load), pose-based rejection, median/weighted averaging, quality report output (`images_used`, `report` string).
**Addresses:** All table-stakes model building features plus quality report differentiator.
**Avoids:** Pitfall 4 (expression contamination — use median over mean; weight by pose), Pitfall 10 (memory — stream one image at a time, accumulate only 478x2 float arrays).

### Phase 4: FaceModelMorph Node

**Rationale:** The highest-risk phase, placed last when all infrastructure is solid. `compute_model_morph_warp()` is the hardest function in v1.1: it must normalize source landmarks to canonical space, compute the shape delta, and de-normalize back to pixel space in the correct order.
**Delivers:** `compute_model_morph_warp()` in `morph_utils.py` (alongside, never replacing, existing function), `face_model_morph.py` with `FaceModelMorph` node (same IMAGE/MASK/ALIGN_DATA output interface as FaceShapeMorph), pose-based strength attenuation for high-yaw sources.
**Addresses:** Pose-aware diff application, FaceModelMorph node, head size from model passed to FaceComposite.
**Avoids:** Pitfall 2 (dual-Procrustes — new function never calls `procrustes_align`), Pitfall 6 (denormalization order — prototype and test with synthetic known-pose data before committing), Pitfall 8 (`_symmetrize_delta` NOT applied on model-based path — canonical model is already symmetric).

### Phase 5: Integration and Polish

**Rationale:** End-to-end pipeline validation, edge case hardening, and regression verification before release.
**Delivers:** Full pipeline integration test (directory -> model -> morph -> composite), regression tests confirming v1.0 pipeline output bit-identical before and after v1.1 changes, edge case handling (empty directory, all images rejected, single image, no face detected, malformed model file), model preview visualization.
**Addresses:** Model preview differentiator, v1.0 regression safety.
**Avoids:** Pitfall 11 (profile view failure — pose-based attenuation validated end-to-end), Pitfall 12 (regression from shared utility changes — full existing test suite green before Phase 1 starts and after each phase).

### Phase Ordering Rationale

- Phases 1 and 2 are pure infrastructure with no user-facing nodes; they establish the contracts (pose API, model file format) that all later phases depend on.
- Phase 3 can be built and tested independently of Phase 4 — the builder produces valid models even before the morph node exists.
- Phase 4 is deliberately last because it is the highest-risk and depends on all prior work being stable and tested.
- Phase 5 validates the whole before shipping; the regression baseline (existing 123 tests passing) must be confirmed green before Phase 1 even begins.

### Research Flags

Phases needing deeper research or experimentation during planning:
- **Phase 4 (FaceModelMorph):** The exact coordinate-frame math for `compute_model_morph_warp()` — specifically the denormalization order and whether foreshortening compensation is needed beyond simple IPD scaling — should be prototyped with synthetic data before the implementation plan is finalized. This was flagged HIGH risk in FEATURES.md.

Phases with well-established patterns (skip research-phase):
- **Phase 1:** MediaPipe API and SciPy Rotation verified against installed packages; implementation is fully specified.
- **Phase 2:** NumPy NPZ round-trip verified; format structure is clear from ARCHITECTURE.md signatures.
- **Phase 3:** Orchestration of verified components using established ComfyUI node pattern.
- **Phase 5:** Integration testing follows existing project test patterns (pytest, `conda run -n comfyui`).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All APIs verified against installed versions via introspection and round-trip tests; zero new deps |
| Features | HIGH | MVP scope is small and clear; differentiators are optional; anti-features explicitly documented |
| Architecture | HIGH | Component boundaries are explicit with concrete function signatures; additive-only approach minimizes risk |
| Pitfalls | HIGH | Critical pitfalls verified against existing codebase; key mathematical risks tested with synthetic data |

**Overall confidence:** HIGH

### Gaps to Address

- **Denormalization math validation:** The delta pipeline from canonical space back to pixel space (`scale by source IED`, then `rotate by source pose`) is described clearly but has not been validated against real multi-pose test images. This is the single highest implementation risk. A synthetic test (known canonical model, known source at 0/15/30/45-degree yaw, verify pixel-space morphed landmarks) should be the first deliverable of Phase 4.
- **`_symmetrize_delta` behavior on model path:** Research confirms it should be skipped on the model-based morph path (Pitfall 8), but behavior when the canonical model has real asymmetry (all real faces are slightly asymmetric) is not tested. Recommend exposing a `symmetrize` boolean on `FaceModelMorph` defaulting to `False`, with documentation.
- **Blendshape-based expression weighting:** The API exists (`output_face_blendshapes=True`) but the mapping from blendshape scores to a "neutrality" weight is unverified. Start with `cos(yaw) * cos(pitch)` weighting; add blendshape weighting as a v1.1.1 improvement after validating the simpler approach.
- **Z-coordinate depth accuracy at extreme poses:** MediaPipe's weak perspective Z is sufficient for near-frontal normalization but may produce errors at yaw > 30 degrees. Using the 4x4 matrix (which bypasses raw Z) avoids this for pose estimation, but the frontalized 3D coordinates still carry weak-perspective Z. Validate frontalization residuals with real test images at 15/30/45-degree yaw before relying on them in production averaging.

## Sources

### Primary (HIGH confidence)
- MediaPipe FaceLandmarkerOptions API — `output_facial_transformation_matrixes` parameter verified via `help(vision.FaceLandmarkerOptions)` on mediapipe 0.10.18
- MediaPipe FaceLandmarkerResult — `facial_transformation_matrixes: List[numpy.ndarray]` field verified via `inspect.getmembers()`
- SciPy Rotation (`from_matrix`, `as_euler`, `inv`) — round-trip verified with scipy 1.12.0
- NumPy npz round-trip — verified at ~6 KB with numpy 1.26.4, `allow_pickle=False`
- Existing codebase: `morph_utils.py`, `alignment.py`, `mediapipe_helper.py`, `face_morph.py`, `face_composite.py`

### Secondary (MEDIUM confidence)
- [MediaPipe 3D Face Transform blog](https://developers.googleblog.com/mediapipe-3d-face-transform/) — Procrustes analysis for pose matrix, Z coordinate semantics
- [MediaPipe Face Landmarker Python Guide](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python) — transformation matrix and blendshape options
- [SciPy Rotation docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.html)
- [MediaPipe Face Mesh wiki](https://github.com/google-ai-edge/mediapipe/wiki/MediaPipe-Face-Mesh) — Z coordinate normalization (weak perspective, scaled by image width)
- [MediaPipe Z coordinate normalization release notes v0.7.6](https://github.com/google/mediapipe/releases/tag/v0.7.6)
- [Procrustes analysis limitations for 2D vs 3D](https://arxiv.org/html/2409.16861v1) — alignment pitfalls

---
*Research completed: 2026-03-11*
*Ready for roadmap: yes*
