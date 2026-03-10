---
phase: 01-environment-and-detection
plan: 01
subsystem: detection
tags: [mediapipe, face-landmarks, pytest, utilities]

# Dependency graph
requires: []
provides:
  - "utils/mediapipe_helper.py with get_landmarker() and comfyui_to_mediapipe()"
  - "utils/landmarks.py with extract_landmarks() and draw_landmarks_on_image()"
  - "requirements.txt with mediapipe>=0.10.14"
  - "Test scaffold with conftest.py fixtures and pytest config"
affects: [01-02, 02-crop-logic, 03-morph-pipeline]

# Tech tracking
tech-stack:
  added: [mediapipe, pytest]
  patterns: [lazy-model-loading, torch-to-mediapipe-conversion, tdd]

key-files:
  created:
    - requirements.txt
    - utils/__init__.py
    - utils/mediapipe_helper.py
    - utils/landmarks.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_mediapipe_helper.py
    - pyproject.toml
  modified: []

key-decisions:
  - "Added pyproject.toml with pythonpath config for pytest module resolution"
  - "Landmarker caching includes parameter comparison for confidence thresholds"

patterns-established:
  - "Lazy model loading: global cached instance with auto-download from CDN"
  - "Tensor conversion: ComfyUI [B,H,W,C] float32 -> numpy uint8 -> mp.Image"
  - "Test fixtures in conftest.py: sample tensors, mp.Images, mock landmark data"

requirements-completed: [PLAT-01, PLAT-02]

# Metrics
duration: 2min
completed: 2026-03-10
---

# Phase 01 Plan 01: Utils Foundation Summary

**MediaPipe helper with lazy model loading/caching, landmark extraction and drawing utilities, pytest scaffold with 5 passing tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-10T15:46:43Z
- **Completed:** 2026-03-10T15:48:25Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Created utils package with MediaPipe Face Landmarker lazy loading and auto-download
- Implemented landmark extraction (pixel coords) and debug drawing utilities
- Established test infrastructure with pytest config, fixtures, and 5 passing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Create utils package with MediaPipe helper and landmark utilities** - `d2f0d44` (feat)
2. **Task 2: Create test scaffold and helper tests** - `dde0507` (test)

## Files Created/Modified
- `requirements.txt` - Declares mediapipe>=0.10.14 dependency
- `utils/__init__.py` - Package init
- `utils/mediapipe_helper.py` - Model download, lazy loading, tensor conversion
- `utils/landmarks.py` - Landmark extraction and drawing utilities
- `tests/__init__.py` - Test package init
- `tests/conftest.py` - Shared fixtures (tensors, mp.Image, mock landmarks)
- `tests/test_mediapipe_helper.py` - 5 tests for helper module
- `pyproject.toml` - pytest config with pythonpath and slow marker

## Decisions Made
- Added pyproject.toml with `pythonpath = ["."]` for pytest to resolve utils module imports
- Landmarker caching compares stored confidence parameters; recreates instance if they differ

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added pyproject.toml for pytest module resolution**
- **Found during:** Task 2 (test scaffold creation)
- **Issue:** pytest could not import `utils.mediapipe_helper` -- module not found because tests/ runs in a different import context
- **Fix:** Created pyproject.toml with `[tool.pytest.ini_options]` setting `pythonpath = ["."]` and `testpaths = ["tests"]`
- **Files modified:** pyproject.toml
- **Verification:** All 5 tests pass with `conda run -n ComfyUI pytest tests/ -x -q`
- **Committed in:** dde0507 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for test execution. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Utils package ready for plan 01-02 to implement FaceDetect node
- Test scaffold in place for adding node-level tests
- MediaPipe model will auto-download on first use

---
*Phase: 01-environment-and-detection*
*Completed: 2026-03-10*
