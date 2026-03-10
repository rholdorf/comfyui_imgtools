---
phase: 03-face-shape-morphing
plan: 02
subsystem: morph
tags: [tps, face-morphing, comfyui-node, scikit-image, graceful-degradation]

# Dependency graph
requires:
  - phase: 03-face-shape-morphing
    plan: 01
    provides: morph_utils (compute_morph_warp, generate_feathered_mask, normalize_landmarks, MORPH_CONTROL_INDICES)
  - phase: 02-core-node-implementation
    provides: FaceCropAlign node, alignment utilities, face mask generation
provides:
  - FaceShapeMorph ComfyUI node for face shape warping
  - Registered as "ImgTools Face Shape Morph" in NODE_CLASS_MAPPINGS
  - ALIGN_DATA passthrough for Phase 4 compositing
affects: [phase-4-compositing, face swap pipeline]

# Tech tracking
tech-stack:
  added: [skimage.transform.warp]
  patterns: [graceful degradation with try/except passthrough, morphed-position mask generation]

key-files:
  created: [face_morph.py, tests/test_face_morph.py]
  modified: [__init__.py]

key-decisions:
  - "Generate feathered mask from morphed landmark positions (not source) per Research pitfall 6"
  - "Eye-corner coherence test uses normalized space to account for IED normalization scaling"

patterns-established:
  - "Graceful degradation: wrap morph logic in try/except, return source image + ones mask on any failure"
  - "Mask from morphed positions: update only MORPH_CONTROL_INDICES in full 478-point array for mask generation"

requirements-completed: [MORPH-01, MORPH-02, MORPH-04, MORPH-05]

# Metrics
duration: 4min
completed: 2026-03-10
---

# Phase 3 Plan 2: FaceShapeMorph Node Summary

**FaceShapeMorph ComfyUI node wiring TPS warp pipeline with strength control, feathered mask from morphed positions, and graceful degradation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T19:18:24Z
- **Completed:** 2026-03-10T19:22:52Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Built FaceShapeMorph node that morphs source face shape toward target using TPS warping with configurable strength
- Full graceful degradation: empty landmarks, zero IED, TPS failure, or any exception returns source unchanged
- Feathered warp mask generated from morphed (not source) landmark positions for correct compositing alignment
- ALIGN_DATA passthrough for Phase 4 reverse compositing
- Node registered in __init__.py behind _face_nodes_available gate
- 21 node-specific tests, 87 total tests passing with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: FaceShapeMorph node implementation with TDD**
   - `8425f91` (test: add failing tests for FaceShapeMorph node)
   - `0488c90` (feat: implement FaceShapeMorph node with TPS face warping)
2. **Task 2: Register FaceShapeMorph and run full test suite**
   - `163f100` (feat: register FaceShapeMorph in NODE_CLASS_MAPPINGS)

_TDD tasks have RED (test) and GREEN (feat) commits_

## Files Created/Modified
- `face_morph.py` - FaceShapeMorph class with morph() method and _passthrough() helper
- `tests/test_face_morph.py` - 21 tests across 7 test classes (conventions, outputs, strength, passthrough, degradation, mask, coherence)
- `__init__.py` - Import and registration of FaceShapeMorph behind _face_nodes_available gate

## Decisions Made
- Generate feathered mask from morphed landmark positions (not source): ensures mask aligns with warped face contour, per Research pitfall 6 about mask/warp misalignment
- Eye-corner coherence test uses normalized (IED-independent) space: the IED normalization intentionally removes size differences between faces, so coherence must be tested in normalized coordinates

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixture eye landmarks had zero intra-eye distance**
- **Found during:** Task 1 (TDD RED/GREEN cycle)
- **Issue:** Setting all eye indices to the same (x,y) made eye-corner distances 0, causing coherence test to fail trivially
- **Fix:** Changed fixture to place eye landmarks in small ellipses (parametric by eye_size) so corner indices have distinct positions
- **Files modified:** tests/test_face_morph.py
- **Verification:** TestFeatureCoherence passes with meaningful distance comparisons
- **Committed in:** 0488c90 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test fixture)
**Impact on plan:** Essential test correctness fix. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 3 complete: all morph utilities and FaceShapeMorph node delivered
- FaceShapeMorph outputs (morphed_face IMAGE, warp_mask MASK, align_data ALIGN_DATA) ready for Phase 4 compositing
- ALIGN_DATA passthrough ensures reverse transform data is preserved

---
## Self-Check: PASSED

All 3 created/modified files verified on disk. All 3 task commits verified in git log.

---
*Phase: 03-face-shape-morphing*
*Completed: 2026-03-10*
