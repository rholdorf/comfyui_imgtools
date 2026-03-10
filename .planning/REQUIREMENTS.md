# Requirements: ComfyUI Face Shape Matcher

**Defined:** 2026-03-10
**Core Value:** Morph source face shape to match target face proportions so downstream face swap produces natural results

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Detection

- [x] **DET-01**: Node detects face landmarks using MediaPipe Face Landmarker (478 points)
- [x] **DET-02**: Node crops face region with configurable padding margin
- [x] **DET-03**: Node aligns tilted/rotated faces to upright orientation based on eye positions
- [x] **DET-04**: User can select which face to process by index when multiple faces detected
- [x] **DET-05**: Node outputs cropped face image, alignment transform data, and face mask

### Morphing

- [x] **MORPH-01**: Node warps source face shape to match target face proportions using TPS
- [x] **MORPH-02**: Strength parameter (0.0-1.0) controls morph intensity
- [x] **MORPH-03**: Node uses ~60 face contour landmarks (not all 478) for efficient warping
- [x] **MORPH-04**: Interior facial features (eyes, nose, mouth) are anchored to prevent distortion
- [x] **MORPH-05**: Node outputs morphed face image and warp mask

### Compositing

- [ ] **COMP-01**: Node composites morphed face back into original image
- [ ] **COMP-02**: Feathered mask blending for smooth face-to-background transition
- [ ] **COMP-03**: Reverse alignment transform to match original face orientation
- [ ] **COMP-04**: Node outputs full composited image and face region mask

### Platform

- [x] **PLAT-01**: All nodes run on macOS with Apple Silicon (no CUDA-only dependencies)
- [x] **PLAT-02**: Dependencies limited to MediaPipe + scikit-image (+ existing ComfyUI deps)
- [x] **PLAT-03**: Nodes follow ComfyUI conventions (INPUT_TYPES, RETURN_TYPES, IMAGE tensors)

## v2 Requirements

### Morphing Enhancements

- **MORPH-06**: Region-selective morphing weights (jaw, forehead, cheeks individually)
- **MORPH-07**: Landmark debug visualization overlay

### Compositing Enhancements

- **COMP-05**: Poisson seamless blending option (cv2.seamlessClone)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Face swap | Handled by ReActor and other existing swap nodes |
| Video/real-time processing | Massive complexity; process individual frames instead |
| 3D face reconstruction | Overkill for proportion matching; heavy deps |
| InsightFace as detector | Non-commercial license, CUDA-preferring |
| Color/lighting correction | Separate concern; let downstream nodes handle |
| Model training | MediaPipe pre-trained model is sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DET-01 | Phase 1 | Complete |
| DET-02 | Phase 2 | Complete |
| DET-03 | Phase 2 | Complete |
| DET-04 | Phase 2 | Complete |
| DET-05 | Phase 2 | Complete |
| MORPH-01 | Phase 3 | Complete |
| MORPH-02 | Phase 3 | Complete |
| MORPH-03 | Phase 3 | Complete |
| MORPH-04 | Phase 3 | Complete |
| MORPH-05 | Phase 3 | Complete |
| COMP-01 | Phase 4 | Pending |
| COMP-02 | Phase 4 | Pending |
| COMP-03 | Phase 4 | Pending |
| COMP-04 | Phase 4 | Pending |
| PLAT-01 | Phase 1 | Complete |
| PLAT-02 | Phase 1 | Complete |
| PLAT-03 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-03-10*
*Last updated: 2026-03-10 after roadmap creation*
