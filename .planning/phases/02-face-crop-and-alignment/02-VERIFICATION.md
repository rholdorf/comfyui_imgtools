---
phase: 02-face-crop-and-alignment
verified: 2026-03-10T17:30:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 02: Face Crop and Alignment Verification Report

**Phase Goal:** Implement face crop and alignment pipeline
**Verified:** 2026-03-10T17:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                        | Status     | Evidence                                                                                           |
|----|------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------------|
| 1  | Alignment angle computed correctly from eye landmark positions               | VERIFIED   | `compute_alignment_angle` uses `arctan2(dy, abs(dx))`; horizontal eyes return 0.0 (test passes)   |
| 2  | Affine transform rotates tilted face to upright orientation                  | VERIFIED   | `build_alignment_transform` + `apply_alignment` via skimage; `test_align_true_with_tilted_face` passes |
| 3  | Padded crop box expands by configurable factor and clamps to image bounds    | VERIFIED   | `compute_padded_crop_box` clamps to `(0, img_w)` / `(0, img_h)`; 3 crop-box tests pass            |
| 4  | Face mask generated from oval landmarks as binary float32 array              | VERIFIED   | `generate_face_mask` uses `polygon2mask`; binary + float32 + non-empty tests pass                 |
| 5  | User can crop a face from an image with configurable padding                 | VERIFIED   | `FaceCropAlign.crop_and_align` accepts `padding` FLOAT; output is `[1, H, W, 3]` tensor           |
| 6  | Tilted faces are aligned to upright orientation                              | VERIFIED   | `align=True` path invokes `build_alignment_transform`; non-zero angle test passes                 |
| 7  | User can select which face by index when multiple detected                   | VERIFIED   | `idx = min(face_index, len(landmarks)-1)`; `test_face_index_selection` verifies different crop boxes |
| 8  | Node outputs cropped face image, alignment transform data, and face mask     | VERIFIED   | `RETURN_TYPES = ("IMAGE", "ALIGN_DATA", "MASK")`; `test_align_data_fields` checks all 5 keys      |
| 9  | Out-of-range face index is clamped gracefully (no crash)                     | VERIFIED   | `face_index=5` with 1 face clamps to 0; `test_face_index_clamped` passes                          |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact                      | Expected                                              | Lines  | Min Required | Status     | Details                                          |
|-------------------------------|-------------------------------------------------------|--------|-------------|------------|--------------------------------------------------|
| `utils/alignment.py`          | 5 exported functions + 2 index constants              | 156    | —           | VERIFIED   | All 5 functions present and substantive          |
| `utils/face_mask.py`          | `generate_face_mask` + `FACE_OVAL_INDICES`            | 36     | —           | VERIFIED   | Both exports present                             |
| `face_crop.py`                | `FaceCropAlign` ComfyUI node                          | 100    | 50          | VERIFIED   | 100 lines, well above minimum                    |
| `tests/test_alignment.py`     | Unit tests for alignment math                         | 142    | 40          | VERIFIED   | 12 tests, 142 lines                              |
| `tests/test_face_mask.py`     | Unit tests for mask generation                        | 44     | 20          | VERIFIED   | 4 tests (class + 2 index tests), 44 lines        |
| `tests/test_face_crop.py`     | Node-level tests for FaceCropAlign                    | 160    | 50          | VERIFIED   | 10 tests, 160 lines                              |
| `__init__.py`                 | `FaceCropAlign` in `NODE_CLASS_MAPPINGS`              | 31     | —           | VERIFIED   | Registered at line 27                            |
| `tests/conftest.py`           | Deterministic landmark fixtures                       | 152    | —           | VERIFIED   | 4 fixtures: deterministic, tilted, multi-face, tensor |

### Key Link Verification

| From                  | To                               | Via                                         | Status   | Details                                                     |
|-----------------------|----------------------------------|---------------------------------------------|----------|-------------------------------------------------------------|
| `utils/alignment.py`  | `skimage.transform.AffineTransform` | import and use for rotation matrix         | WIRED    | `from skimage.transform import AffineTransform, warp` line 8 |
| `utils/face_mask.py`  | `skimage.draw.polygon2mask`      | import for mask generation                  | WIRED    | `from skimage.draw import polygon2mask` line 8              |
| `face_crop.py`        | `utils/alignment.py`             | `from .utils.alignment import`              | WIRED    | Lines 12-17 import all 4 alignment functions used in method  |
| `face_crop.py`        | `utils/face_mask.py`             | `from .utils.face_mask import`              | WIRED    | Line 18 imports `generate_face_mask`, called at line 81     |
| `__init__.py`         | `face_crop.py`                   | `from .face_crop import FaceCropAlign`      | WIRED    | Line 5 inside try block; registered at lines 27-28           |

### Requirements Coverage

| Requirement | Source Plan  | Description                                                              | Status    | Evidence                                                                   |
|-------------|-------------|--------------------------------------------------------------------------|-----------|----------------------------------------------------------------------------|
| DET-02      | 02-01, 02-02 | Node crops face region with configurable padding margin                  | SATISFIED | `compute_padded_crop_box` with `padding_factor`; node exposes `padding` input |
| DET-03      | 02-01, 02-02 | Node aligns tilted/rotated faces to upright orientation based on eye positions | SATISFIED | `build_alignment_transform` + `apply_alignment`; `align` toggle in node   |
| DET-04      | 02-02        | User can select which face by index when multiple faces detected         | SATISFIED | `face_index` input with clamping; `test_face_index_selection` verifies it  |
| DET-05      | 02-01, 02-02 | Node outputs cropped face image, alignment transform data, and face mask | SATISFIED | `RETURN_TYPES = ("IMAGE", "ALIGN_DATA", "MASK")`; ALIGN_DATA has 5 fields  |

No orphaned requirements: all DET-02 through DET-05 are claimed by plans and implemented.

### Anti-Patterns Found

No blockers or warnings found in Phase 2 files.

| File              | Line | Pattern     | Severity | Impact                          |
|-------------------|------|-------------|----------|---------------------------------|
| `utils/landmarks.py` | 19 | `return []` | Info     | Legitimate early-return for zero faces, not a stub |

### Human Verification Required

None. All phase goal behaviors are verifiable programmatically:

- Correct alignment math: verified by unit tests with deterministic fixtures
- Crop box clamping: verified by boundary tests
- ComfyUI node conventions: verified by attribute checks
- Output tensor shapes and dtypes: verified by type/shape assertions
- Node registration: verified by __init__.py inspection

The only behaviors that would normally need human verification (visual quality of the aligned crop, correct face oval mask appearance) are adequately covered by the deterministic fixture approach: known landmark positions produce predictable crop boxes and non-empty binary masks that are machine-verifiable.

### Test Execution Results

All 28 Phase 2 tests pass with zero failures:

```
tests/test_alignment.py   12 passed
tests/test_face_mask.py    6 passed  (4 tests + 2 index tests)
tests/test_face_crop.py   10 passed
Total: 28 passed in 0.08s
```

All 7 task commits from both plans are present in git history:
- Plan 01: `257be91` (test RED), `3dcd477` (feat GREEN), `f19d4ba` (test RED), `52613b0` (feat GREEN)
- Plan 02: `d3a3836` (test RED), `ca9932b` (feat GREEN), `17de881` (feat registration)

---

_Verified: 2026-03-10T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
