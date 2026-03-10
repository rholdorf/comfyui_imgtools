# Requirements: ComfyUI Face Shape Matcher

**Defined:** 2026-03-10
**Core Value:** Morph source face shape to match target face proportions so downstream face swap produces natural results

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Detection

- [ ] **DET-01**: Node detects face landmarks using MediaPipe Face Landmarker (478 points)
- [ ] **DET-02**: Node crops face region with configurable padding margin
- [ ] **DET-03**: Node aligns tilted/rotated faces to upright orientation based on eye positions
- [ ] **DET-04**: User can select which face to process by index when multiple faces detected
- [ ] **DET-05**: Node outputs cropped face image, alignment transform data, and face mask

### Morphing

- [ ] **MORPH-01**: Node warps source face shape to match target face proportions using TPS
- [ ] **MORPH-02**: Strength parameter (0.0-1.0) controls morph intensity
- [ ] **MORPH-03**: Node uses ~60 face contour landmarks (not all 478) for efficient warping
- [ ] **MORPH-04**: Interior facial features (eyes, nose, mouth) are anchored to prevent distortion
- [ ] **MORPH-05**: Node outputs morphed face image and warp mask

### Compositing

- [ ] **COMP-01**: Node composites morphed face back into original image
- [ ] **COMP-02**: Feathered mask blending for smooth face-to-background transition
- [ ] **COMP-03**: Reverse alignment transform to match original face orientation
- [ ] **COMP-04**: Node outputs full composited image and face region mask

### Platform

- [ ] **PLAT-01**: All nodes run on macOS with Apple Silicon (no CUDA-only dependencies)
- [ ] **PLAT-02**: Dependencies limited to MediaPipe + scikit-image (+ existing ComfyUI deps)
- [ ] **PLAT-03**: Nodes follow ComfyUI conventions (INPUT_TYPES, RETURN_TYPES, IMAGE tensors)

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
| DET-01 | — | Pending |
| DET-02 | — | Pending |
| DET-03 | — | Pending |
| DET-04 | — | Pending |
| DET-05 | — | Pending |
| MORPH-01 | — | Pending |
| MORPH-02 | — | Pending |
| MORPH-03 | — | Pending |
| MORPH-04 | — | Pending |
| MORPH-05 | — | Pending |
| COMP-01 | — | Pending |
| COMP-02 | — | Pending |
| COMP-03 | — | Pending |
| COMP-04 | — | Pending |
| PLAT-01 | — | Pending |
| PLAT-02 | — | Pending |
| PLAT-03 | — | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 0
- Unmapped: 17

---
*Requirements defined: 2026-03-10*
*Last updated: 2026-03-10 after initial definition*
