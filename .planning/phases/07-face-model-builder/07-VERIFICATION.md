---
phase: 07-face-model-builder
verified: 2026-03-11T23:55:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 7: FaceModelBuilder Verification Report

**Phase Goal:** User can build a canonical face model from a directory of target images, with quality feedback on which images contributed
**Verified:** 2026-03-11T23:55:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                      | Status     | Evidence                                                                                     |
|----|--------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------|
| 1  | model_io schema accepts (478,3) stddev and version is bumped to 2                          | VERIFIED   | `MODEL_VERSION = "2"`, `_SCHEMA["landmark_stddev"] = ("f", (478, 3))` in utils/model_io.py  |
| 2  | Directory of images is scanned, faces detected, extreme poses rejected by yaw/pitch thresholds | VERIFIED | `scan_images` + `process_image` in utils/model_builder.py; abs(yaw)>45 or abs(pitch)>30 returns REJECTED |
| 3  | Accepted faces are weighted by cos(yaw)*cos(pitch) and averaged into canonical 3D landmarks | VERIFIED  | `weight = math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))` in model_builder.py line 144; `compute_weighted_average` produces (478,3) mean |
| 4  | Missing transformation matrix falls back to frontal pose assumption with weight=1.0        | VERIFIED   | `if pose is None:` branch in process_image returns status=ACCEPTED, weight=1.0, no frontalization |
| 5  | FaceModelBuilder appears in ComfyUI node list under imgtools/face category                 | VERIFIED   | `NODE_CLASS_MAPPINGS["FaceModelBuilder"] = FaceModelBuilder` in __init__.py; `CATEGORY = "imgtools/face"` |
| 6  | Node accepts directory path and outputs FACE_MODEL, quality_report STRING, and preview IMAGE | VERIFIED | `RETURN_TYPES = ("FACE_MODEL", "STRING", "IMAGE")`; "directory" in required INPUT_TYPES      |
| 7  | Quality report shows per-image table with File/Status/Yaw/Pitch/Roll/Confidence/Weight columns, sorted correctly | VERIFIED | `format_quality_report` function: ACCEPTED (weight desc), REJECTED (yaw asc), NO FACE (filename); N/A and "-" shown correctly |
| 8  | Preview image is 512x512 showing green control points and white face oval contour           | VERIFIED   | `render_preview` returns (512,512,3) uint8; test_green_pixels_exist and test_white_contour_below_header both pass |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact                           | Expected                                   | Status      | Details                                                              |
|------------------------------------|--------------------------------------------|-------------|----------------------------------------------------------------------|
| `utils/model_io.py`                | MODEL_VERSION=2, (478,3) stddev schema     | VERIFIED    | Line 15: `MODEL_VERSION = "2"`, line 23: `"landmark_stddev": ("f", (478, 3))` |
| `utils/model_builder.py`           | Core pipeline: scan_images, process_image, compute_weighted_average, build_face_model | VERIFIED | All 4 functions present, substantive, 274 lines |
| `tests/test_model_io.py`           | Updated tests for v2 schema                | VERIFIED    | `_make_model_data()` uses (478,3) stddev; v1 rejection test present; wrong stddev shape test present |
| `tests/test_face_model_builder.py` | Tests for builder pipeline + node          | VERIFIED    | 28 tests across TestScanImages, TestProcessImage, TestComputeWeightedAverage, TestBuildFaceModel, TestQualityReport, TestPreviewImage, TestNodeRegistration |
| `face_model_builder.py`            | FaceModelBuilder ComfyUI node class        | VERIFIED    | 235 lines; FaceModelBuilder class with correct INPUT_TYPES, RETURN_TYPES, FUNCTION, CATEGORY; format_quality_report and render_preview functions |
| `__init__.py`                      | Node registration with FaceModelBuilder    | VERIFIED    | `from .face_model_builder import FaceModelBuilder` in try block; registered in NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS |

---

### Key Link Verification

| From                    | To                     | Via                                                       | Status  | Details                                                                 |
|-------------------------|------------------------|-----------------------------------------------------------|---------|-------------------------------------------------------------------------|
| `utils/model_builder.py` | `utils/pose_utils.py`  | `from utils.pose_utils import frontalize_landmarks, normalize_landmarks_3d, extract_pose_angles, compute_head_dimensions` | VERIFIED | Lines 21-25 import all required functions; all are called in process_image body |
| `utils/model_builder.py` | `utils/model_io.py`    | `from utils.model_io import save_face_model`              | VERIFIED | Line 19; `save_face_model(save_path, ...)` called in build_face_model   |
| `face_model_builder.py` | `utils/model_builder.py` | `from .utils.model_builder import build_face_model`     | VERIFIED | Line 7; called in `build_model` method line 213                         |
| `face_model_builder.py` | `utils/morph_utils.py` | `from .utils.morph_utils import MORPH_CONTROL_INDICES`    | VERIFIED | Line 8; passed to `render_preview` and used in build_face_model         |
| `__init__.py`           | `face_model_builder.py` | `from .face_model_builder import FaceModelBuilder`       | VERIFIED | Line 8 in try block; registered at line 36 in NODE_CLASS_MAPPINGS       |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                              | Status    | Evidence                                                                               |
|-------------|-------------|------------------------------------------------------------------------------------------|-----------|----------------------------------------------------------------------------------------|
| MODL-01     | 07-01, 07-02 | User can build a canonical face model from a directory of target images via FaceModelBuilder node | SATISFIED | FaceModelBuilder node accepts directory, calls build_face_model, returns FACE_MODEL dict |
| MODL-02     | 07-01        | FaceModelBuilder auto-rejects extreme-pose images and weights averaging by cos(yaw)*cos(pitch) | SATISFIED | process_image rejects abs(yaw)>45 or abs(pitch)>30; weight formula verified in code and tests |
| MODL-04     | 07-02        | FaceModelBuilder outputs per-image quality report (used/rejected, yaw/pitch/roll, confidence) | SATISFIED | format_quality_report produces aligned table with File/Status/Yaw/Pitch/Roll/Conf/Weight columns |
| MODL-05     | 07-02        | FaceModelBuilder outputs a landmark preview visualization for model validation           | SATISFIED | render_preview produces 512x512 canvas with green control points and white face oval; converted to ComfyUI IMAGE tensor |

Note: MODL-03 (model saved as versioned .facemodel.npz with ~6KB) was completed in Phase 6 and is not a Phase 7 responsibility. The traceability table in REQUIREMENTS.md confirms this. MODL-03 is not listed in either plan's `requirements` field — correctly so.

No orphaned requirements: all Phase 7 requirement IDs (MODL-01, MODL-02, MODL-04, MODL-05) are accounted for by plans 07-01 and 07-02.

---

### Anti-Patterns Found

None. Grep over all .py files in the package returned no matches for TODO, FIXME, XXX, HACK, PLACEHOLDER, or similar markers. No empty implementations, no stub return values, no console.log equivalents found.

---

### Human Verification Required

#### 1. Node loads in ComfyUI without error

**Test:** Launch ComfyUI with this custom node installed, open the node browser, search for "FaceModelBuilder"
**Expected:** Node appears under imgtools/face category with directory, yaw_threshold, pitch_threshold, and save_path inputs; outputs face_model, quality_report, preview
**Why human:** Cannot launch ComfyUI headlessly to verify node registry in the live application

#### 2. End-to-end run on a real image directory

**Test:** Connect FaceModelBuilder to a directory of real face images, execute, inspect quality_report STRING output and preview IMAGE output
**Expected:** Quality report shows per-image table; preview shows recognizable face landmark layout with green dots and white contour; model file written to disk
**Why human:** Requires real MediaPipe model file and actual face images; not feasible in automated test without GPU/model overhead

---

### Test Results

**Phase 07 tests:** 38/38 passed (10 model_io + 28 model_builder/node)
**Full regression suite:** 184/184 passed — no regressions introduced

---

### Summary

Phase 7 goal is fully achieved. All eight observable truths are verified against actual codebase contents:

- `utils/model_io.py` has the v2 schema with (478,3) stddev — confirmed by reading MODEL_VERSION and _SCHEMA
- `utils/model_builder.py` implements the complete pipeline (scan, process, filter, weight, average) with substantive logic throughout — no stubs
- `face_model_builder.py` wraps the pipeline in a proper ComfyUI node class with correct RETURN_TYPES, format_quality_report, and render_preview functions
- `__init__.py` wires FaceModelBuilder into NODE_CLASS_MAPPINGS under the correct display name
- All key links are live (imports verified, callsites verified)
- All four phase 7 requirements (MODL-01, MODL-02, MODL-04, MODL-05) are satisfied with code evidence
- 184 tests pass with no regressions

---

_Verified: 2026-03-11T23:55:00Z_
_Verifier: Claude (gsd-verifier)_
