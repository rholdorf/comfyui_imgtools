---
phase: 01-environment-and-detection
plan: 02
subsystem: detection
tags: [mediapipe, face-landmarks, comfyui-node, tdd]

# Dependency graph
requires:
  - "01-01: utils/mediapipe_helper.py and utils/landmarks.py"
provides:
  - "face_detection.py with FaceDetect ComfyUI node class"
  - "FaceDetect registered as 'ImgTools Face Detect' in NODE_CLASS_MAPPINGS"
  - "FACE_LANDMARKS custom type output (list of dicts with 478-point landmarks)"
affects: [02-crop-logic, 03-morph-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns: [comfyui-node-pattern, conditional-import-registration, tdd]

key-files:
  created:
    - face_detection.py
    - tests/test_face_detection.py
  modified:
    - __init__.py

key-decisions:
  - "Used try/except conditional import for graceful degradation when mediapipe missing"

patterns-established:
  - "ComfyUI node pattern: INPUT_TYPES classmethod, RETURN_TYPES/NAMES tuples, FUNCTION string"
  - "Conditional registration: try/except import with _available flag, add to mappings if available"
  - "FACE_LANDMARKS type: list of dicts with 'landmarks' (478,2) and 'landmarks_3d' (478,3) numpy arrays"

requirements-completed: [DET-01, PLAT-03]

# Metrics
duration: 2min
completed: 2026-03-10
---

# Phase 01 Plan 02: FaceDetect Node Summary

**FaceDetect ComfyUI node detecting 478 face landmarks via MediaPipe with preview image output and graceful degradation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-10T15:50:45Z
- **Completed:** 2026-03-10T15:52:43Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented FaceDetect node with TDD (6 tests RED then GREEN)
- Node detects 478 landmarks per face, returns structured FACE_LANDMARKS data
- Preview image output draws green dots at landmark positions
- Graceful degradation: prints warning if mediapipe not installed, does not crash

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement FaceDetect node (TDD)** - `52cbbf6` (feat)
2. **Task 2: Register FaceDetect in __init__.py** - `748443a` (feat)

## Files Created/Modified
- `face_detection.py` - FaceDetect ComfyUI node class with detect_faces method
- `tests/test_face_detection.py` - 6 tests: conventions, landmark detection, no-face handling, preview output
- `__init__.py` - Conditional import and registration of FaceDetect

## Decisions Made
- Used try/except conditional import for graceful degradation when mediapipe is missing, printing a warning with install instructions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 1 complete: all detection infrastructure in place
- FaceDetect node outputs FACE_LANDMARKS type for downstream crop/align phase
- 11 total tests passing across both plans (5 helper + 6 node)

---
*Phase: 01-environment-and-detection*
*Completed: 2026-03-10*
