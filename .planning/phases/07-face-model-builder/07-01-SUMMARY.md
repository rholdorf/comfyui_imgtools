---
phase: 07-face-model-builder
plan: 01
subsystem: face-model
tags: [mediapipe, numpy, face-model, weighted-average, pose-filtering, npz]

requires:
  - phase: 05-pose-estimation
    provides: "pose_utils.py with frontalize, normalize, head_dimensions"
  - phase: 06-model-persistence
    provides: "model_io.py with save/load NPZ persistence"
provides:
  - "model_io v2 schema with (478,3) 3D stddev"
  - "model_builder.py pipeline: scan_images, process_image, compute_weighted_average, build_face_model"
affects: [07-02-face-model-builder-node]

tech-stack:
  added: []
  patterns: ["mock extract_landmarks for unit testing pipeline functions", "cos(yaw)*cos(pitch) weighting for pose-aware averaging"]

key-files:
  created: [utils/model_builder.py, tests/test_face_model_builder.py]
  modified: [utils/model_io.py, tests/test_model_io.py]

key-decisions:
  - "Mock extract_landmarks at module level for process_image tests (avoids needing real MediaPipe model)"
  - "MODEL_VERSION bumped to 2 for breaking schema change (478,2 -> 478,3 stddev)"

patterns-established:
  - "Pipeline pattern: separate pure functions from ComfyUI node for testability"
  - "Weighted averaging with cos-based pose weighting for multi-image landmark fusion"

requirements-completed: [MODL-01, MODL-02]

duration: 5min
completed: 2026-03-11
---

# Phase 7 Plan 01: Model Builder Pipeline Summary

**model_io v2 schema with 3D stddev and core builder pipeline (scan, detect, filter, average) for multi-image face model construction**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-11T23:27:41Z
- **Completed:** 2026-03-11T23:32:34Z
- **Tasks:** 2 (TDD: 4 commits)
- **Files modified:** 4

## Accomplishments
- Updated model_io schema to v2 with (478,3) 3D stddev support
- Created model_builder.py with full pipeline: directory scanning, per-image face detection/filtering, weighted 3D landmark averaging, and end-to-end model building
- Extreme poses (|yaw|>45, |pitch|>30) rejected; accepted faces weighted by cos(yaw)*cos(pitch)
- Missing transformation matrix gracefully falls back to weight=1.0 without frontalization
- 172 tests pass (26 new: 10 model_io + 16 model_builder)

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Update model_io schema to v2** - RED: `bedbd18` (test), GREEN: `6ae916c` (feat)
2. **Task 2: Create model_builder.py pipeline** - RED: `0f44d6b` (test), GREEN: `9f3ea56` (feat)

## Files Created/Modified
- `utils/model_io.py` - MODEL_VERSION=2, landmark_stddev (478,3)
- `utils/model_builder.py` - Core pipeline: scan_images, process_image, compute_weighted_average, build_face_model
- `tests/test_model_io.py` - Updated for v2 schema, added v1 rejection + wrong stddev shape tests
- `tests/test_face_model_builder.py` - 16 tests covering scan, process, average, build

## Decisions Made
- Bumped MODEL_VERSION to "2" since (478,2)->(478,3) stddev is a breaking schema change
- Mocked `extract_landmarks` at module level in process_image tests to avoid needing real MediaPipe model, while still testing the full pose filtering and normalization logic
- Used `__array__` protocol on mock PIL images to satisfy `np.array()` conversion

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mock strategy for process_image tests**
- **Found during:** Task 2 (model_builder tests)
- **Issue:** Original mock approach (mock landmarker returning fake FaceLandmarkerResult) didn't pass correct pose angles through extract_landmarks because extract_pose_angles recomputed from identity matrix
- **Fix:** Mocked extract_landmarks at module level instead, passing synthetic face dicts with desired pose values directly
- **Files modified:** tests/test_face_model_builder.py
- **Verification:** All 16 tests pass with correct weight assertions
- **Committed in:** 9f3ea56 (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test mock strategy changed for correctness. No scope creep.

## Issues Encountered
None beyond the mock strategy adjustment documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- model_builder.py pipeline ready for Plan 02 (FaceModelBuilder ComfyUI node)
- Plan 02 will add: node class, quality report formatting, landmark preview rendering, __init__.py registration

---
*Phase: 07-face-model-builder*
*Completed: 2026-03-11*
