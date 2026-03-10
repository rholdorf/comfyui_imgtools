# Roadmap: ComfyUI Face Shape Matcher

## Overview

This roadmap delivers a three-node face morphing pipeline (FaceCropAlign, FaceShapeMorph, FaceComposite) for ComfyUI that pre-processes face geometry before face swapping. The work progresses from environment validation and face detection, through cropping/alignment, TPS-based shape morphing, and finally compositing with feathered blending. Each phase delivers a verifiable node that builds on the previous, culminating in an end-to-end workflow that integrates with ReActor.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Environment and Detection** - Verify Python/MediaPipe compatibility, implement face landmark detection core
- [ ] **Phase 2: Face Crop and Alignment** - Build FaceCropAlign node with rotation handling, padding, and multi-face selection
- [ ] **Phase 3: Face Shape Morphing** - Build FaceShapeMorph node with TPS warping and strength control
- [ ] **Phase 4: Compositing and Integration** - Build FaceComposite node with feathered blending and end-to-end pipeline validation

## Phase Details

### Phase 1: Environment and Detection
**Goal**: Face landmarks can be reliably detected from images on macOS Apple Silicon
**Depends on**: Nothing (first phase)
**Requirements**: DET-01, PLAT-01, PLAT-02, PLAT-03
**Success Criteria** (what must be TRUE):
  1. MediaPipe Face Landmarker runs successfully in the ComfyUI Python environment on macOS Apple Silicon
  2. Node detects 478 face landmarks from a test image and returns landmark coordinate data
  3. Node follows ComfyUI conventions (INPUT_TYPES, RETURN_TYPES, IMAGE tensor format)
  4. Only MediaPipe and scikit-image are added as new dependencies beyond existing ComfyUI deps
**Plans**: TBD

Plans:
- [ ] 01-01: TBD

### Phase 2: Face Crop and Alignment
**Goal**: Users can extract a cropped, upright-aligned face from any image with control over which face and padding
**Depends on**: Phase 1
**Requirements**: DET-02, DET-03, DET-04, DET-05
**Success Criteria** (what must be TRUE):
  1. Node crops face region from image with user-configurable padding margin
  2. Tilted or rotated faces are aligned to upright orientation based on eye positions
  3. User can select which face to process by index when multiple faces are present
  4. Node outputs cropped face image, alignment transform data, and face mask as separate outputs
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

### Phase 3: Face Shape Morphing
**Goal**: Users can morph a source face shape to match a target face's proportions with adjustable intensity
**Depends on**: Phase 2
**Requirements**: MORPH-01, MORPH-02, MORPH-03, MORPH-04, MORPH-05
**Success Criteria** (what must be TRUE):
  1. Node warps source face contour to match target face proportions using TPS with ~60 contour control points
  2. Strength slider (0.0-1.0) visibly controls morph intensity -- 0.0 produces no change, 1.0 produces full shape match
  3. Interior facial features (eyes, nose, mouth) remain undistorted after morphing
  4. Node outputs morphed face image and warp mask for downstream use
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

### Phase 4: Compositing and Integration
**Goal**: Users can run the full face shape matching pipeline end-to-end, producing a natural-looking composited result ready for face swap
**Depends on**: Phase 3
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04
**Success Criteria** (what must be TRUE):
  1. Node composites morphed face back into the original image at the correct position and orientation
  2. Feathered mask blending produces smooth face-to-background transitions with no visible seams
  3. Reverse alignment transform correctly restores original face orientation (no rotation artifacts)
  4. Full three-node pipeline (crop/align -> morph -> composite) produces a natural-looking result from source and target face images
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Environment and Detection | 0/? | Not started | - |
| 2. Face Crop and Alignment | 0/? | Not started | - |
| 3. Face Shape Morphing | 0/? | Not started | - |
| 4. Compositing and Integration | 0/? | Not started | - |
