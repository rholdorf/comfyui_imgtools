# Requirements: ComfyUI Face Shape Matcher

**Defined:** 2026-03-11
**Core Value:** Morph source face shape to match target face proportions so downstream face swap produces natural results

## v1.1 Requirements

Requirements for v1.1 Versatile Model milestone. Each maps to roadmap phases.

### 3D Pose Normalization

- [ ] **POSE-01**: System can extract pitch/yaw/roll from MediaPipe's 4x4 transformation matrix
- [ ] **POSE-02**: System can frontalize 3D landmarks by de-rotating to canonical frontal pose
- [ ] **POSE-03**: System can normalize landmarks by inter-pupil distance for cross-image comparability
- [ ] **POSE-04**: FaceModelMorph auto-attenuates morph strength for source faces with high yaw

### Model Building

- [ ] **MODL-01**: User can build a canonical face model from a directory of target images via FaceModelBuilder node
- [ ] **MODL-02**: FaceModelBuilder auto-rejects extreme-pose images and weights averaging by cos(yaw)*cos(pitch)
- [ ] **MODL-03**: FaceModelBuilder saves model as versioned .facemodel.npz (~6KB) with canonical landmarks and head dimensions
- [ ] **MODL-04**: FaceModelBuilder outputs per-image quality report (used/rejected, yaw/pitch/roll, confidence)
- [ ] **MODL-05**: FaceModelBuilder outputs a landmark preview visualization for model validation

### Model Morphing

- [ ] **MRPH-01**: User can apply a face model to a source image via FaceModelMorph node using pose-aware delta and TPS warp
- [ ] **MRPH-02**: FaceModelMorph passes head dimensions from model to FaceComposite for correct scaling
- [ ] **MRPH-03**: FaceModelMorph exposes a symmetrize toggle (default off) for the canonical model

### Integration

- [ ] **INTG-01**: FaceModelBuilder handles edge cases: empty directory, all images rejected, single image, no face detected
- [ ] **INTG-02**: FaceModelMorph handles edge case: malformed or incompatible model file

## v1.2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Model Enhancement

- **MENH-01**: User can incrementally add images to an existing model without full reprocessing
- **MENH-02**: System normalizes expression variation via blendshape decomposition before averaging

### Morphing Enhancement

- **MREH-01**: User can apply region-selective morphing weights (jaw, forehead, cheeks independently)
- **MREH-02**: System supports multi-person directories via face identity clustering

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full 3D face reconstruction | Overkill — 2D projection of frontalized landmarks sufficient for shape matching |
| OpenCV dependency | Constraint — MediaPipe 4x4 matrix + SciPy Rotation replaces solvePnP |
| v1.0 regression testing (standalone) | User deferred — existing 123 tests cover v1.0; edge cases prioritized instead |
| Real-time video processing | v1.0 constraint — batch image processing only |
| GPU-only operations | v1.0 constraint — must work on CPU/MPS |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| POSE-01 | — | Pending |
| POSE-02 | — | Pending |
| POSE-03 | — | Pending |
| POSE-04 | — | Pending |
| MODL-01 | — | Pending |
| MODL-02 | — | Pending |
| MODL-03 | — | Pending |
| MODL-04 | — | Pending |
| MODL-05 | — | Pending |
| MRPH-01 | — | Pending |
| MRPH-02 | — | Pending |
| MRPH-03 | — | Pending |
| INTG-01 | — | Pending |
| INTG-02 | — | Pending |

**Coverage:**
- v1.1 requirements: 14 total
- Mapped to phases: 0
- Unmapped: 14 ⚠️

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-11 after initial definition*
