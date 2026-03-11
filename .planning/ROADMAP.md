# Roadmap: ComfyUI Face Shape Matcher

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-11)
- 🚧 **v1.1 Versatile Model** — Phases 5-9 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-11</summary>

- [x] Phase 1: Environment and Detection (2/2 plans) — completed 2026-03-10
- [x] Phase 2: Face Crop and Alignment (2/2 plans) — completed 2026-03-10
- [x] Phase 3: Face Shape Morphing (2/2 plans) — completed 2026-03-10
- [x] Phase 4: Compositing and Integration (2/2 plans) — completed 2026-03-11

</details>

### 🚧 v1.1 Versatile Model

**Milestone Goal:** Enable face shape morphing across diverse image compositions by building a canonical face model from multiple target images with 3D pose normalization.

- [x] **Phase 5: 3D Pose Foundation** - Extract head pose from MediaPipe matrix, frontalize and IPD-normalize landmarks (completed 2026-03-11)
- [ ] **Phase 6: Model Persistence** - Define and implement versioned .facemodel.npz file format with round-trip I/O
- [ ] **Phase 7: FaceModelBuilder Node** - User-facing node that processes a directory of images into an averaged canonical face model
- [ ] **Phase 8: FaceModelMorph Node** - User-facing node that applies a face model to source images via pose-aware delta and TPS warp
- [ ] **Phase 9: Integration and Polish** - Edge case hardening, end-to-end pipeline validation, model preview visualization

## Phase Details

### Phase 5: 3D Pose Foundation
**Goal**: Landmarks from any head pose can be normalized to a canonical frontal, scale-invariant representation
**Depends on**: Phase 4 (v1.0 complete)
**Requirements**: POSE-01, POSE-02, POSE-03
**Success Criteria** (what must be TRUE):
  1. Given a MediaPipe face detection result with transformation matrix, system extracts pitch/yaw/roll angles in degrees
  2. Given 3D landmarks from a rotated face, system produces frontalized landmarks that match the same face detected at frontal pose (within tolerance)
  3. Given landmarks from two faces of different sizes, IPD-normalized landmarks have inter-pupil distance of 1.0 and are directly comparable
  4. Existing v1.0 pipeline remains fully functional (123 tests pass unchanged)
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md — TDD: pose_utils.py with pose extraction, frontalization, and IPD normalization
- [ ] 05-02-PLAN.md — Integration: wire pose data into MediaPipe helper and face dict

### Phase 6: Model Persistence
**Goal**: Face models can be saved to disk and loaded back with full fidelity, enabling persistent reuse across sessions
**Depends on**: Phase 5
**Requirements**: MODL-03
**Success Criteria** (what must be TRUE):
  1. A .facemodel.npz file (~6 KB) stores canonical landmarks (478x2), head dimensions, control point indices, per-landmark stddev, and version metadata
  2. A model saved and loaded back produces identical data (dtype, shape, values) confirmed by round-trip test
  3. Loading a file with missing fields or wrong version raises a clear error message (not a silent failure or cryptic crash)
**Plans**: TBD

Plans:
- [ ] 06-01: TBD

### Phase 7: FaceModelBuilder Node
**Goal**: User can build a canonical face model from a directory of target images, with quality feedback on which images contributed
**Depends on**: Phase 5, Phase 6
**Requirements**: MODL-01, MODL-02, MODL-04, MODL-05
**Success Criteria** (what must be TRUE):
  1. User provides a directory path in ComfyUI, and FaceModelBuilder outputs a FACE_MODEL representing the averaged face shape
  2. Images with extreme head poses (yaw > threshold) are automatically rejected and remaining images are weighted by cos(yaw)*cos(pitch)
  3. Node outputs a quality report string listing each image with used/rejected status, yaw/pitch/roll values, and confidence
  4. Node outputs a landmark preview image showing the canonical model landmarks plotted on a canvas for visual validation
  5. Model file is saved to disk as .facemodel.npz and can be reloaded in future sessions
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

### Phase 8: FaceModelMorph Node
**Goal**: User can apply a canonical face model to any source image, producing a morphed result with pose-aware shape matching
**Depends on**: Phase 7
**Requirements**: MRPH-01, MRPH-02, MRPH-03, POSE-04
**Success Criteria** (what must be TRUE):
  1. User connects a FACE_MODEL and source image to FaceModelMorph, and gets a morphed image where the source face shape matches the model's proportions
  2. Morph strength is automatically attenuated for source faces with high yaw angle, preventing artifacts on near-profile views
  3. Head dimensions from the model are passed through to FaceComposite for correct scaling during compositing
  4. User can toggle a symmetrize option (default off) to force the canonical model to bilateral symmetry before applying
  5. Output interface (IMAGE, MASK, ALIGN_DATA) matches FaceShapeMorph, making FaceModelMorph a drop-in replacement in existing workflows
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

### Phase 9: Integration and Polish
**Goal**: The full model-based pipeline handles real-world edge cases gracefully and is validated end-to-end
**Depends on**: Phase 8
**Requirements**: INTG-01, INTG-02
**Success Criteria** (what must be TRUE):
  1. FaceModelBuilder handles empty directory, all-images-rejected, single-image, and no-face-detected cases with clear user-facing error messages (not crashes)
  2. FaceModelMorph handles malformed or incompatible model files with clear error messages
  3. Full pipeline (directory -> FaceModelBuilder -> FaceModelMorph -> FaceComposite) produces correct output end-to-end
  4. All v1.0 tests (123) continue to pass, confirming zero regression from v1.1 changes
**Plans**: TBD

Plans:
- [ ] 09-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 5 -> 6 -> 7 -> 8 -> 9

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Environment and Detection | v1.0 | 2/2 | Complete | 2026-03-10 |
| 2. Face Crop and Alignment | v1.0 | 2/2 | Complete | 2026-03-10 |
| 3. Face Shape Morphing | v1.0 | 2/2 | Complete | 2026-03-10 |
| 4. Compositing and Integration | v1.0 | 2/2 | Complete | 2026-03-11 |
| 5. 3D Pose Foundation | 2/2 | Complete   | 2026-03-11 | - |
| 6. Model Persistence | v1.1 | 0/? | Not started | - |
| 7. FaceModelBuilder Node | v1.1 | 0/? | Not started | - |
| 8. FaceModelMorph Node | v1.1 | 0/? | Not started | - |
| 9. Integration and Polish | v1.1 | 0/? | Not started | - |
