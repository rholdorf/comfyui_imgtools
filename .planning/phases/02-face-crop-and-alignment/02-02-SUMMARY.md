---
phase: 02-face-crop-and-alignment
plan: 02
subsystem: face-crop
tags: [comfyui-node, face-crop, face-alignment, affine-transform, face-mask, torch-tensor]

requires:
  - phase: 02-face-crop-and-alignment
    provides: "Alignment math utilities (5 functions) and face mask generation from Plan 01"
  - phase: 01-project-setup
    provides: "FaceDetect node with FACE_LANDMARKS output, conditional import pattern"
provides:
  - "FaceCropAlign ComfyUI node: IMAGE + FACE_LANDMARKS -> (IMAGE, ALIGN_DATA, MASK)"
  - "ALIGN_DATA dict with rotation_angle, rotation_center, crop_box, original_size, transform_matrix"
  - "Face index selection with graceful clamping"
affects: [03-crop-logic, 04-testing-polish]

tech-stack:
  added: []
  patterns: [TDD red-green for ComfyUI nodes, package-qualified test imports]

key-files:
  created: [face_crop.py, tests/test_face_crop.py]
  modified: [__init__.py]

key-decisions:
  - "Used package-qualified imports (comfyui_imgtools.face_crop) in tests to match face_detection test pattern"
  - "Gated FaceCropAlign behind same _face_nodes_available check as FaceDetect since both require mediapipe ecosystem"

patterns-established:
  - "ComfyUI node TDD: test conventions first, then output types, then behavior"
  - "ALIGN_DATA as plain dict (not custom type) for easy serialization in Phase 4 reversal"

requirements-completed: [DET-02, DET-03, DET-04, DET-05]

duration: 3min
completed: 2026-03-10
---

# Phase 02 Plan 02: FaceCropAlign Node Summary

**FaceCropAlign ComfyUI node wiring alignment utilities and mask generation into a face crop pipeline with configurable padding, alignment toggle, and face index selection**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-10T17:11:09Z
- **Completed:** 2026-03-10T17:14:12Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- FaceCropAlign node accepting IMAGE + FACE_LANDMARKS, outputting cropped face IMAGE, ALIGN_DATA dict, and face MASK
- 10 unit tests covering conventions, output types, face index selection/clamping, and alignment toggle behavior
- Node registered in ComfyUI NODE_CLASS_MAPPINGS with conditional import gating
- All 33 tests pass (10 new + 23 existing from Phase 1 and Plan 01)

## Task Commits

Each task was committed atomically:

1. **Task 1: FaceCropAlign node with TDD** - `d3a3836` (test: RED), `ca9932b` (feat: GREEN)
2. **Task 2: Register FaceCropAlign in __init__.py** - `17de881` (feat)

_TDD Task 1 has two commits (test then implementation)_

## Files Created/Modified
- `face_crop.py` - FaceCropAlign node with crop_and_align method, imports from utils/alignment and utils/face_mask
- `tests/test_face_crop.py` - 10 tests: conventions, output types, ALIGN_DATA fields, face index selection, clamping, align toggle
- `__init__.py` - Added FaceCropAlign import and registration alongside FaceDetect

## Decisions Made
- Used package-qualified imports (`from comfyui_imgtools.face_crop import FaceCropAlign`) in tests to match existing face_detection test pattern, since pythonpath="." in pyproject.toml requires package context for relative imports
- Gated FaceCropAlign behind same `_face_nodes_available` try/except block as FaceDetect, keeping both face nodes under single mediapipe availability check

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed test import path to use package-qualified name**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Tests used `from face_crop import FaceCropAlign` but relative imports in face_crop.py require package context
- **Fix:** Changed to `from comfyui_imgtools.face_crop import FaceCropAlign` matching existing test pattern
- **Files modified:** tests/test_face_crop.py
- **Verification:** All 10 tests pass
- **Committed in:** ca9932b

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Import path correction necessary for tests to find module. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FaceCropAlign node fully operational with all Phase 2 utilities wired in
- ALIGN_DATA dict provides all fields needed for Phase 4 composite reversal
- 33 total tests pass (Phase 1 + Phase 2 complete)
- Ready for Phase 3 (crop logic / morph) which consumes FaceCropAlign outputs

## Self-Check: PASSED

All 3 created/modified files verified on disk. All 3 task commits verified in git log.

---
*Phase: 02-face-crop-and-alignment*
*Completed: 2026-03-10*
