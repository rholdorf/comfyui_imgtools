---
phase: 08-facemodelmorph-node
plan: 01
subsystem: face-morphing
tags: [tps-warp, pose-attenuation, procrustes, mediapipe, comfyui-node]

requires:
  - phase: 05-pose-extraction
    provides: frontalize_landmarks, normalize_landmarks_3d, compute_head_dimensions
  - phase: 07-facemodelbuilder-node
    provides: FACE_MODEL dict with canonical_landmarks and head_dimensions

provides:
  - FaceModelMorph ComfyUI node with pose-aware delta computation and TPS warp
  - _symmetrize_model function for bilateral model symmetrization (MRPH-03)
  - Cosine pose attenuation (POSE-04)
  - Drop-in replacement for FaceShapeMorph output contract (IMAGE, MASK, ALIGN_DATA)

affects: [09-integration, compositing-workflow]

tech-stack:
  added: []
  patterns:
    - "Pose-aware delta: frontalize -> normalize -> delta -> scale by IED -> symmetrize"
    - "Procrustes fallback when pose=None"
    - "Cosine attenuation: effective_strength = strength * cos(yaw) * cos(pitch)"

key-files:
  created:
    - face_model_morph.py
    - tests/test_face_model_morph.py
  modified:
    - __init__.py

key-decisions:
  - "Model symmetrization operates on full 478-landmark array using mirror pair IDs as direct indices"
  - "Delta computed in IPD-normalized space, scaled back to pixels by source IED"
  - "Head scale uses model width / source width ratio interpolated by effective_strength"

patterns-established:
  - "Dual-path delta: pose-aware (frontalize+normalize) vs Procrustes fallback"
  - "Model symmetrization separate from delta symmetrization (two concerns)"

requirements-completed: [MRPH-01, MRPH-03, POSE-04]

duration: 3min
completed: 2026-03-12
---

# Phase 8 Plan 01: FaceModelMorph Node Summary

**Pose-aware face model morphing node with TPS warp, cosine attenuation, Procrustes fallback, and model symmetrization toggle**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-12T01:09:59Z
- **Completed:** 2026-03-12T01:13:30Z
- **Tasks:** 3 (TDD: RED, GREEN, REFACTOR)
- **Files modified:** 3

## Accomplishments
- FaceModelMorph node with pose-aware delta computation producing visible TPS warp
- Procrustes fallback path for faces without pose data (pose=None)
- Cosine attenuation reduces morph at high yaw/pitch (POSE-04)
- Model symmetrization toggle for bilateral symmetry enforcement (MRPH-03)
- 28 tests covering all behaviors, conventions, edge cases
- Node registered in NODE_CLASS_MAPPINGS, full suite 212 tests green

## Task Commits

Each task was committed atomically:

1. **RED: Failing tests** - `2716c34` (test)
2. **GREEN: FaceModelMorph implementation** - `0c87663` (feat)
3. **REFACTOR: Node registration** - `1fd0892` (refactor)

## Files Created/Modified
- `face_model_morph.py` - FaceModelMorph node with pose-aware and fallback delta paths, TPS warp, model symmetrization
- `tests/test_face_model_morph.py` - 28 tests: conventions, delta computation, attenuation, symmetrization, graceful degradation
- `__init__.py` - Register FaceModelMorph in NODE_CLASS_MAPPINGS

## Decisions Made
- Model symmetrization operates on full (478, 2) array using `_MORPH_MIRROR_PAIRS` landmark IDs as direct array indices (not positional indices into control subset)
- Delta computed in IPD-normalized space then scaled to pixels by source IED (origin-independent displacement)
- Head scale from model vs source width ratio, interpolated by effective_strength; defaults to 1.0 for synthetic/degenerate 3D landmarks
- Did NOT call `compute_morph_warp` -- wrote custom TPS assembly (delta pipeline is fundamentally different)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- FaceModelMorph node complete and registered, outputs (IMAGE, MASK, ALIGN_DATA) compatible with FaceComposite
- MRPH-02 (head_scale passthrough) implemented via align_data["head_scale"]
- Ready for integration testing and remaining Phase 8 plans

---
*Phase: 08-facemodelmorph-node*
*Completed: 2026-03-12*
