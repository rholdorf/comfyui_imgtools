---
phase: 02-face-crop-and-alignment
plan: 01
subsystem: face-alignment
tags: [scikit-image, affine-transform, face-mask, mediapipe-landmarks, numpy]

requires:
  - phase: 01-project-setup
    provides: "MediaPipe landmark extraction (478, 2) arrays, pytest infrastructure"
provides:
  - "Eye center computation from landmark indices"
  - "Alignment angle calculation from eye positions"
  - "Affine transform building and application via skimage"
  - "Padded crop box computation with image clamping"
  - "Face oval mask generation from landmark polygon"
affects: [02-02-PLAN, 03-crop-logic, 04-testing-polish]

tech-stack:
  added: [skimage.transform.AffineTransform, skimage.transform.warp, skimage.draw.polygon2mask]
  patterns: [TDD red-green for utility modules, deterministic fixture landmarks]

key-files:
  created: [utils/alignment.py, utils/face_mask.py, tests/test_alignment.py, tests/test_face_mask.py]
  modified: [tests/conftest.py]

key-decisions:
  - "Used abs(dx) in arctan2 angle calculation to handle MediaPipe left/right eye convention (subject's right eye is left in image coords)"
  - "Inlined FACE_OVAL_INDICES in conftest fixtures to avoid cross-module import dependency during TDD"

patterns-established:
  - "Deterministic landmark fixtures: _make_deterministic_landmarks() creates predictable (478,2) arrays with known eye/oval positions"
  - "Coordinate convention: landmarks are (x,y), polygon2mask expects (row,col)=(y,x), always swap explicitly"

requirements-completed: [DET-02, DET-03, DET-05]

duration: 4min
completed: 2026-03-10
---

# Phase 02 Plan 01: Alignment Math and Face Mask Summary

**Eye-based alignment utilities (5 functions) and face oval mask generation using skimage AffineTransform and polygon2mask**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T17:04:10Z
- **Completed:** 2026-03-10T17:08:40Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Alignment utility module with eye center computation, angle calculation, affine transform building/application, and padded crop box
- Face mask generation from 36 MediaPipe face oval landmark indices via polygon2mask
- 18 unit tests covering all functions with deterministic fixtures (horizontal, tilted, multi-face)

## Task Commits

Each task was committed atomically:

1. **Task 1: Alignment utilities with TDD** - `257be91` (test: RED), `3dcd477` (feat: GREEN)
2. **Task 2: Face mask generation with TDD** - `f19d4ba` (test: RED), `52613b0` (feat: GREEN)

_TDD tasks have two commits each (test then implementation)_

## Files Created/Modified
- `utils/alignment.py` - Eye centers, alignment angle, affine transform, padded crop box (5 exported functions)
- `utils/face_mask.py` - Face oval mask generation (1 function + FACE_OVAL_INDICES constant)
- `tests/test_alignment.py` - 12 unit tests for alignment math
- `tests/test_face_mask.py` - 6 unit tests for mask generation
- `tests/conftest.py` - Added deterministic landmark fixtures (horizontal, tilted, multi-face)

## Decisions Made
- Used `abs(dx)` in `compute_alignment_angle` to handle MediaPipe's left/right convention where subject's right eye has lower x in image coordinates, preventing pi-radian angle for upright faces
- Inlined FACE_OVAL_INDICES in conftest as `_FACE_OVAL_INDICES_FOR_FIXTURES` to avoid circular import during TDD when face_mask.py did not yet exist

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed alignment angle convention for MediaPipe eye ordering**
- **Found during:** Task 1 (alignment utilities)
- **Issue:** `compute_alignment_angle` returned pi radians for upright faces because MediaPipe's "right eye" (subject's right) has lower x than "left eye" in image coords, making dx negative
- **Fix:** Used `abs(dx)` in arctan2 so angle measures tilt deviation from horizontal regardless of eye ordering direction
- **Files modified:** utils/alignment.py
- **Verification:** test_zero_angle_no_rotation passes with ~0 angle
- **Committed in:** 3dcd477

**2. [Rule 3 - Blocking] Inlined face oval indices in conftest to unblock TDD**
- **Found during:** Task 1 (conftest fixture creation)
- **Issue:** `_make_deterministic_landmarks` imported `FACE_OVAL_INDICES` from `utils.face_mask` which did not exist yet
- **Fix:** Defined `_FACE_OVAL_INDICES_FOR_FIXTURES` directly in conftest.py
- **Files modified:** tests/conftest.py
- **Verification:** All fixtures work, tests collect and run
- **Committed in:** 3dcd477

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for correctness and TDD flow. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 alignment functions and mask generation ready for FaceCropAlign node (Plan 02)
- Deterministic fixtures available for Plan 02 node-level tests
- 23 total tests pass (18 new + 5 Phase 1)

## Self-Check: PASSED

All 5 created/modified files verified on disk. All 4 task commits verified in git log.

---
*Phase: 02-face-crop-and-alignment*
*Completed: 2026-03-10*
