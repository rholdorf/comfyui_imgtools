---
phase: 04-compositing-and-integration
plan: 02
subsystem: face-pipeline
tags: [comfyui-node, registration, pipeline-integration, e2e-validation]

requires:
  - phase: 04-compositing-and-integration
    plan: 01
    provides: FaceComposite node implementation
provides:
  - Full 4-node face pipeline registered and validated in ComfyUI
affects: []

tech-stack:
  added: []
  patterns: [direct-paste-compositing, feathered-rect-mask]

key-files:
  created: []
  modified: [face_composite.py, tests/test_face_composite.py]

key-decisions:
  - "FaceComposite simplified to direct paste (no reverse warp, no resize) — morphed_face is used exactly as-is"
  - "Only crop_box and original_size required from align_data (transform_matrix no longer needed)"
  - "8px feathered rectangular mask for edge blending"

patterns-established:
  - "Simple paste composite: place morphed face at crop_box origin with feathered blend"

requirements-completed: [COMP-01, COMP-04]

duration: manual
completed: 2026-03-11
---

# Phase 4 Plan 2: Registration & Pipeline Validation Summary

**FaceComposite registered in ComfyUI, full pipeline validated by user**

## Accomplishments
- FaceComposite already registered in __init__.py (done during 04-01)
- Node registered as 'ImgTools Face Composite' under imgtools/face category
- Gated behind _face_nodes_available check (same as other face nodes)
- Full pipeline tested by user: FaceDetect → FaceCropAlign → FaceShapeMorph → FaceComposite
- FaceComposite simplified during debugging: removed reverse warp and resize, now does direct paste with feathered blending
- User confirmed pipeline produces correct results
- All 123 tests pass

## Deviations from Plan
- FaceComposite was significantly simplified vs original plan:
  - Removed reverse affine warp (skimage.warp)
  - Removed head_scale resize logic
  - Now pastes morphed_face as-is at crop_box position
  - Only requires crop_box + original_size from align_data

## Files Modified
- `face_composite.py` - Simplified to direct paste (no warp, no resize)
- `tests/test_face_composite.py` - Removed rotated round-trip test, simplified passthrough tests

---
*Phase: 04-compositing-and-integration*
*Completed: 2026-03-11*
