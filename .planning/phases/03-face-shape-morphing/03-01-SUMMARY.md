---
phase: 03-face-shape-morphing
plan: 01
subsystem: morph
tags: [tps, landmarks, scikit-image, face-morphing, normalization]

# Dependency graph
requires:
  - phase: 02-core-node-implementation
    provides: FaceCropAlign node, alignment utilities, face mask generation
provides:
  - FaceCropAlign FACE_LANDMARKS 4th output for crop-space landmarks
  - MORPH_CONTROL_INDICES (67 curated landmark indices)
  - normalize_landmarks for inter-eye distance normalization
  - compute_morph_warp for TPS warp pipeline with strength control
  - generate_feathered_mask for soft-edged compositing masks
  - _get_boundary_anchors for TPS edge pinning
affects: [03-02-PLAN, face_morph node, phase 4 compositing]

# Tech tracking
tech-stack:
  added: [skimage.transform.ThinPlateSplineTransform, skimage.filters.gaussian]
  patterns: [inter-eye-distance normalization, boundary anchor deduplication, TPS estimate(dst, src) convention]

key-files:
  created: [utils/morph_utils.py, tests/test_morph_utils.py]
  modified: [face_crop.py, tests/test_face_crop.py]

key-decisions:
  - "Added near-duplicate point deduplication before TPS estimation to prevent numerical instability"
  - "Used 12 boundary anchors (4 corners + 4 midpoints + 4 quarter points) for robust edge pinning"

patterns-established:
  - "TPS argument order: estimate(dst, src) for warp inverse mapping"
  - "Normalize landmarks by IED before computing morph displacement"
  - "Deduplicate near-coincident control points before TPS fitting"

requirements-completed: [MORPH-03]

# Metrics
duration: 6min
completed: 2026-03-10
---

# Phase 3 Plan 1: Crop Landmarks and Morph Utils Summary

**FaceCropAlign outputs crop-space FACE_LANDMARKS; morph_utils provides 67-point TPS warp pipeline with IED normalization and feathered mask generation**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-10T19:08:52Z
- **Completed:** 2026-03-10T19:15:16Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- FaceCropAlign now returns 4 outputs including crop-space landmarks in FACE_LANDMARKS format
- Built complete morph utility module with 67 curated control point indices spanning face oval, eyes, eyebrows, nose, and lips
- Implemented TPS warp pipeline with inter-eye distance normalization, strength interpolation, and boundary anchors
- Implemented feathered mask generation using Gaussian blur on face oval mask
- Full TDD coverage: 37 tests for plan scope, 66 total tests passing with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: FaceCropAlign crop-space landmarks + morph_utils foundation**
   - `5f8451d` (test: add failing tests for crop landmarks and morph utils)
   - `85aa870` (feat: add crop-space landmarks output and morph utils foundation)
2. **Task 2: TPS warp pipeline and feathered mask**
   - `404a283` (test: add failing tests for TPS warp and feathered mask)
   - `56ea9ac` (feat: implement TPS warp pipeline and feathered mask generation)

_TDD tasks have RED (test) and GREEN (feat) commits_

## Files Created/Modified
- `utils/morph_utils.py` - Control point indices, normalization, boundary anchors, TPS warp, feathered mask
- `face_crop.py` - Updated RETURN_TYPES/RETURN_NAMES to 4-tuple, added crop_landmarks_out packaging
- `tests/test_morph_utils.py` - 22 tests covering all morph utility functions
- `tests/test_face_crop.py` - Updated existing tests for 4-tuple return, added 5 TestCropLandmarks tests

## Decisions Made
- Added near-duplicate point deduplication in compute_morph_warp: TPS numerical instability occurs when control points (e.g., eye corner indices overlapping with eye cluster averages) are nearly coincident. O(n^2) dedup with 1e-3 tolerance prevents this.
- Used 12 boundary anchors (4 corners + 4 edge midpoints + 4 quarter points) matching the RESEARCH.md recommendation for robust TPS edge pinning.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Near-duplicate TPS control points causing numerical instability**
- **Found during:** Task 2 (TPS warp implementation)
- **Issue:** When eye landmark indices (33, 133, 362, 263) overlap positionally with eye cluster averages in test fixtures, TPS estimate produces wildly incorrect mappings
- **Fix:** Added deduplication loop that removes points within 1e-3 distance of an earlier point before TPS estimation
- **Files modified:** utils/morph_utils.py
- **Verification:** Identity warp test now passes with atol=1.0
- **Committed in:** 56ea9ac (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential correctness fix for TPS stability. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All morph utility primitives ready for FaceShapeMorph node (Plan 03-02)
- FaceCropAlign provides crop-space landmarks needed by morph node
- compute_morph_warp and generate_feathered_mask are the core building blocks for the node's morph() method

---
## Self-Check: PASSED

All 4 created/modified files verified on disk. All 4 task commits verified in git log.

---
*Phase: 03-face-shape-morphing*
*Completed: 2026-03-10*
