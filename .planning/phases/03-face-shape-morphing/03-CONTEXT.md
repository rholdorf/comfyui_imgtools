# Phase 3: Face Shape Morphing - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Build FaceShapeMorph node that warps a source face's shape to match a target face's proportions using TPS warping, with adjustable strength. Takes cropped/aligned faces from FaceCropAlign. Compositing the morphed face back into the original image is Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Node wiring / inputs
- Both source and target go through FaceCropAlign first — morph node takes two cropped face IMAGEs + two FACE_LANDMARKS + source ALIGN_DATA
- FaceCropAlign needs a new output: single-face landmarks transformed to crop space (so morph node doesn't need face_index selection)
- ALIGN_DATA passes through the morph node as an output for Phase 4 compositing
- Only parameter beyond the inputs: strength FLOAT slider — no extra toggles or region controls for v1

### Morph scope
- Full proportional match — contour AND internal feature positions (eyes, nose, mouth) move to match target
- Features shift position/spacing to match target proportions, but each feature's internal shape stays coherent (no stretching an eye into an oval)
- Strength slider controls how far all points move: 0.0 = source, 0.5 = halfway, 1.0 = full target proportions
- Claude's discretion on which ~60 control points to select for the TPS warp — balance between face oval, eyebrows, eye corners, nose outline, mouth outline

### Strength behavior
- Linear interpolation: `morphed_pt = source_pt + strength * (target_pt - source_pt)`
- Strength capped at 0.0–1.0, no overshoot
- Warp mask output is soft/feathered (Gaussian-blurred edges, ~5-10% of face size), not binary — saves Phase 4 from re-feathering

### Edge case handling
- Normalize both landmark sets by inter-eye distance before computing warp — transfers proportions, not absolute size
- On invalid/missing landmarks or TPS failure: return source face unmodified + full-face mask + align_data passthrough — no error, no workflow interruption
- Warp applies to entire crop image (including background) — warp_mask tells Phase 4 what to composite
- Add corner/edge anchor points (4 corners + ~4-8 edge midpoints) to prevent TPS from distorting crop borders

### Claude's Discretion
- Debug/visualization output (warp grid overlay or similar)
- Exact control point subset selection (~60 from 478 landmarks)
- Whether to resize output canvas or keep source crop dimensions
- TPS implementation approach (scipy RBF, custom, etc.)

</decisions>

<specifics>
## Specific Ideas

- FaceCropAlign must be updated to output crop-space landmarks as a new FACE_LANDMARKS output — this is a prerequisite for the morph node
- Full pipeline wiring: FaceCropAlign(source) + FaceCropAlign(target) → FaceShapeMorph → FaceComposite
- Graceful degradation matches FaceDetect's pattern (return empty/passthrough, never crash workflow)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `utils/face_mask.py`: FACE_OVAL_INDICES (36 contour points) + `generate_face_mask()` — basis for control point selection and warp mask generation
- `utils/alignment.py`: `compute_eye_centers()` — needed for inter-eye distance normalization
- `utils/landmarks.py`: `extract_landmarks()` returns per-face dicts with `landmarks` (478x2 px) — morph node consumes this format
- `face_crop.py`: FaceCropAlign node — needs new landmark output, already computes crop-space landmarks internally (line 75-76)

### Established Patterns
- scikit-image only (no OpenCV) — TPS implementation must follow this constraint
- Nodes in separate files (face_detection.py, face_crop.py → face_morph.py)
- Utils in utils/ subfolder for shared math/helpers
- ComfyUI conventions: INPUT_TYPES classmethod, RETURN_TYPES tuple, IMAGE tensors [batch, H, W, C]
- Graceful degradation: return valid outputs on error, don't crash ComfyUI

### Integration Points
- FaceCropAlign outputs feed directly into FaceShapeMorph inputs
- ALIGN_DATA passes through for Phase 4 FaceComposite
- New FACE_LANDMARKS output from FaceCropAlign connects to morph node's landmark inputs
- __init__.py registration with NODE_CLASS_MAPPINGS / NODE_DISPLAY_NAME_MAPPINGS

</code_context>

<deferred>
## Deferred Ideas

- Region-selective morphing weights (jaw, forehead, cheeks individually) — MORPH-06 in v2
- Landmark debug visualization overlay — MORPH-07 in v2
- Overshoot/exaggeration (strength > 1.0) — potential v2 feature

</deferred>

---

*Phase: 03-face-shape-morphing*
*Context gathered: 2026-03-10*
