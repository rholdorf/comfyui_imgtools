---
phase: 3
slug: face-shape-morphing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed, configured in pyproject.toml) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `conda run -n comfyui pytest tests/test_face_morph.py tests/test_morph_utils.py -x` |
| **Full suite command** | `conda run -n comfyui pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n comfyui pytest tests/test_face_morph.py tests/test_morph_utils.py -x`
- **After every plan wave:** Run `conda run -n comfyui pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | N/A | unit | `conda run -n comfyui pytest tests/test_face_crop.py::TestCropLandmarks -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | MORPH-03 | unit | `conda run -n comfyui pytest tests/test_morph_utils.py::TestControlPoints -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | MORPH-01 | unit | `conda run -n comfyui pytest tests/test_face_morph.py::TestMorphWarp -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | MORPH-02 | unit | `conda run -n comfyui pytest tests/test_face_morph.py::TestStrength -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | MORPH-04 | unit | `conda run -n comfyui pytest tests/test_face_morph.py::TestFeatureCoherence -x` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 1 | MORPH-05 | unit | `conda run -n comfyui pytest tests/test_face_morph.py::TestOutputs -x` | ❌ W0 | ⬜ pending |
| 03-01-07 | 01 | 1 | N/A | unit | `conda run -n comfyui pytest tests/test_face_morph.py::TestGracefulDegradation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_face_morph.py` — stubs for MORPH-01, MORPH-02, MORPH-04, MORPH-05, graceful degradation
- [ ] `tests/test_morph_utils.py` — stubs for MORPH-03 (control point selection, normalization, boundary anchors)
- [ ] Update `tests/test_face_crop.py` — add tests for new crop-space landmarks output

*Existing infrastructure covers framework installation (pytest already configured).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual morph quality | MORPH-01 | Subjective visual assessment | Load source/target face pair in ComfyUI, run FaceMorph node at strength 0.5, visually confirm face shape changes toward target |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
