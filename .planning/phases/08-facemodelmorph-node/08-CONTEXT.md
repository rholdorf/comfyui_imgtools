# Phase 8: FaceModelMorph Node - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

User-facing ComfyUI node that applies a canonical face model (FACE_MODEL) to any source image, producing a morphed result where the source face shape matches the model's proportions. Uses pose-aware delta computation and TPS warp. Output interface (IMAGE, MASK, ALIGN_DATA) matches FaceShapeMorph for drop-in replacement in existing workflows.

</domain>

<decisions>
## Implementation Decisions

### Pose Attenuation Curve
- Cosine fade: effective_strength = user_strength * cos(yaw) * cos(pitch)
- Same formula as model building weights (Phase 5/7 consistency)
- No floor — let cosine go to near-zero naturally; morphing near-profile faces is meaningless
- Graceful fallback: if source face has no pose data (pose=None), apply full strength with no attenuation
- Attenuation applied silently — no extra output, keep (IMAGE, MASK, ALIGN_DATA) signature

### Node Input Design
- Required inputs: source_image (IMAGE), face_model (FACE_MODEL), source_landmarks (FACE_LANDMARKS), source_align_data (ALIGN_DATA), strength (FLOAT)
- Optional input: symmetrize (BOOLEAN, default False)
- Require external landmarks from FaceDetect — same pattern as FaceShapeMorph, no internal detection
- No target_image input — FACE_MODEL replaces the target entirely
- FACE_MODEL input only — no file path alternative; separate LoadFaceModel node can be added later
- Strength slider: 0.0-1.0, default 0.5, step 0.05 — identical to FaceShapeMorph

### Denormalization Strategy
- Normalize source to model space (not denormalize model to pixel space)
- Pipeline: frontalize source 3D landmarks → normalize by IPD → compute delta in normalized space → scale delta back to pixels by source IED → apply to original pixel landmarks
- Fallback (no pose data): use Procrustes alignment between model 2D and source 2D pixel coords
- Always apply _symmetrize_delta() on the pixel-space delta (separate from MRPH-03 symmetrize toggle)
- MRPH-03 symmetrize toggle forces model to bilateral symmetry BEFORE delta computation; _symmetrize_delta cleans residual asymmetry AFTER

### Strength & Attenuation Interaction
- Multiply: effective = user_strength * cos(yaw) * cos(pitch)
- Head scale computed from model head_dimensions vs source head dimensions (both in IPD-normalized units)
- head_scale passed through align_data["head_scale"] for FaceComposite

### Claude's Discretion
- Internal function decomposition (single module vs separate morph util functions)
- Exact eye center computation method for source IED measurement
- How to handle edge cases within the warp (degenerate landmarks, near-zero IED)
- Whether to reuse compute_morph_warp or write a new model-specific warp function
- TPS boundary anchor placement (reuse existing _get_boundary_anchors)

</decisions>

<specifics>
## Specific Ideas

- Cosine attenuation curve is explicitly chosen for consistency with model building weights (Phase 5/7)
- "Drop-in replacement" is a hard requirement: same RETURN_TYPES, same strength defaults
- Two separate symmetrization concerns: (1) MRPH-03 toggle symmetrizes the MODEL, (2) _symmetrize_delta always symmetrizes the DELTA
- Frontalize-then-normalize path reuses existing pose_utils functions (frontalize_landmarks, normalize_landmarks_3d)
- Denormalization is "scale delta by IED" — not full inverse transform

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `utils/pose_utils.py`: `frontalize_landmarks()`, `normalize_landmarks_3d()`, `compute_head_dimensions()` — core of the denormalization pipeline
- `utils/morph_utils.py`: `MORPH_CONTROL_INDICES`, `_symmetrize_delta()`, `_get_boundary_anchors()`, `generate_feathered_mask()` — TPS warp infrastructure
- `utils/morph_utils.py`: `procrustes_align()` — fallback path when no pose data available
- `utils/morph_utils.py`: `normalize_landmarks()` — 2D IED normalization for fallback path
- `utils/model_io.py`: `load_face_model()` — reads FACE_MODEL from disk (for future LoadFaceModel node)
- `face_morph.py`: `FaceShapeMorph` — reference implementation for node structure, passthrough, and warp application

### Established Patterns
- Face data as dict: `{"landmarks": (478,2), "landmarks_3d": (478,3), "pose": {...}}` — source_landmarks follows this
- Passthrough on error: return source image + full mask + unmodified align_data
- head_scale in align_data: `out_align_data["head_scale"] = float(head_scale)` — FaceComposite reads this
- TPS inverse mapping: `tps.estimate(dst, src)` then `warp(img, inverse_map=tps)`
- Node registration: try/except in `__init__.py`, CATEGORY = "imgtools/face"

### Integration Points
- New `face_model_morph.py` at package root (same level as face_morph.py)
- Register as "FaceModelMorph" / "ImgTools Face Model Morph" in `__init__.py`
- Consumes FACE_MODEL type from FaceModelBuilder (Phase 7)
- Feeds into FaceComposite via (IMAGE, MASK, ALIGN_DATA) — same as FaceShapeMorph

</code_context>

<deferred>
## Deferred Ideas

- LoadFaceModel node (load .facemodel.npz from disk path) — could be Phase 9 or future
- Effective strength output for debugging — could add as optional output later if needed

</deferred>

---

*Phase: 08-facemodelmorph-node*
*Context gathered: 2026-03-11*
