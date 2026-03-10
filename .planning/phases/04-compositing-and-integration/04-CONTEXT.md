# Phase 4: Compositing and Integration - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Build FaceComposite node that places the morphed face back into the original image, reversing the crop/align transform with feathered alpha blending. Validate the full 3-node pipeline (FaceCropAlign -> FaceShapeMorph -> FaceComposite) end-to-end. Poisson seamless blending is v2 (COMP-05).

</domain>

<decisions>
## Implementation Decisions

### Mask blending strategy
- Use warp_mask from FaceShapeMorph as-is — no additional feathering in the composite node
- Alpha blend per-pixel: `result = original * (1 - mask) + morphed * mask`
- No external mask input — warp_mask is the only blending mask
- scikit-image only, no OpenCV (Poisson clone deferred to COMP-05 in v2)

### Node inputs & outputs
- 4 inputs: `original_image` (IMAGE), `morphed_face` (IMAGE), `warp_mask` (MASK), `align_data` (ALIGN_DATA)
- 2 outputs: `composited_image` (IMAGE), `face_region_mask` (MASK)
- No blend opacity/strength parameter — morph intensity is controlled upstream in FaceShapeMorph
- Single image only (batch=1) — multi-face handled by running multiple pipelines with different face_index

### Reverse transform handling
- Expand the composite region slightly beyond crop_box to prevent rotation artifacts at edges
- Reconstruct inverse transform from align_data's transform_matrix — no upstream changes needed
- On invalid/corrupted align_data (singular matrix, missing keys): return original image unmodified + empty mask — no error, workflow continues

### Claude's Discretion
- Whether to blend in crop space or original image space (mask timing)
- Inverse transform reconstruction approach
- Exact crop region expansion amount for rotation safety
- Pixel diff tolerance metric for round-trip tests

</decisions>

<specifics>
## Specific Ideas

- Full pipeline wiring: FaceCropAlign(source) + FaceCropAlign(target) -> FaceShapeMorph -> FaceComposite(original_image=source)
- Graceful degradation matches all prior nodes — return valid outputs, never crash workflow
- Feathered mask from morph node should naturally hide edge artifacts from reverse transform

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `utils/alignment.py`: `AffineTransform`, `build_alignment_transform()`, `apply_alignment()` with `transform.inverse` — directly reusable for reverse warp
- `utils/face_mask.py`: `generate_face_mask()` with FACE_OVAL_INDICES — can generate face region mask in original space
- `face_crop.py`: align_data dict contains `transform_matrix` (3x3 ndarray), `crop_box` (x1,y1,x2,y2), `original_size` (w,h), `rotation_angle`, `rotation_center`

### Established Patterns
- scikit-image `warp()` with `inverse_map` for affine transforms (used in alignment.py:111)
- Nodes in separate files: face_detection.py, face_crop.py, face_morph.py -> face_composite.py
- Utils in utils/ subfolder for shared math/helpers
- ComfyUI conventions: INPUT_TYPES classmethod, RETURN_TYPES tuple, IMAGE tensors [batch, H, W, C]
- Graceful degradation: _passthrough pattern returns valid outputs on error (face_morph.py:129)

### Integration Points
- FaceShapeMorph outputs (morphed_face, warp_mask, align_data) connect directly to FaceComposite inputs
- __init__.py registration with NODE_CLASS_MAPPINGS / NODE_DISPLAY_NAME_MAPPINGS
- Gated behind _face_nodes_available check (same as FaceDetect, FaceCropAlign, FaceShapeMorph)

</code_context>

<testing>
## E2E Validation Strategy

### Round-trip test (primary)
- Full pipeline with morph strength=0: output should be near-identical to original image
- Synthetic images with mocked landmarks (consistent with Phase 1-3 test patterns)
- Pixel diff tolerance at Claude's discretion (accounting for bilinear interpolation in rotation/reverse)

### Additional scenarios
- **Strength=1.0**: full morph pipeline must not crash, output valid image with correct dimensions
- **Rotated face (~15 deg)**: rotation + reverse rotation produces correct placement
- **Graceful degradation**: invalid landmarks -> returns original image without error
- **Dimension consistency**: output image has exactly the same dimensions as input original_image

### Test approach
- Unit tests with mocked landmarks only (no MediaPipe dependency in tests)
- Deterministic, fast, CI-friendly

</testing>

<deferred>
## Deferred Ideas

- Poisson seamless blending option (cv2.seamlessClone) — COMP-05 in v2
- Blend opacity slider on composite node — could be useful but redundant with morph strength
- External mask input (user-painted or from another node) — future enhancement
- Integration test with real MediaPipe detection — potential future @pytest.mark.slow test

</deferred>

---

*Phase: 04-compositing-and-integration*
*Context gathered: 2026-03-10*
