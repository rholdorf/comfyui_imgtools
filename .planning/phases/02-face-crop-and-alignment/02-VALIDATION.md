---
phase: 2
slug: face-crop-and-alignment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (configured in pyproject.toml) |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/ -x -m "not slow"` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -m "not slow"`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | DET-02 | unit | `python -m pytest tests/test_alignment.py::test_padded_crop_box -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | DET-02 | unit | `python -m pytest tests/test_alignment.py::test_padding_range -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | DET-03 | unit | `python -m pytest tests/test_alignment.py::test_alignment_angle -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 0 | DET-03 | unit | `python -m pytest tests/test_alignment.py::test_zero_angle -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 0 | DET-04 | unit | `python -m pytest tests/test_face_crop.py::test_face_index_selection -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 0 | DET-04 | unit | `python -m pytest tests/test_face_crop.py::test_face_index_clamped -x` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 0 | DET-05 | unit | `python -m pytest tests/test_face_crop.py::test_output_types -x` | ❌ W0 | ⬜ pending |
| 02-01-08 | 01 | 0 | DET-05 | unit | `python -m pytest tests/test_face_mask.py::test_mask_shape -x` | ❌ W0 | ⬜ pending |
| 02-01-09 | 01 | 0 | DET-05 | unit | `python -m pytest tests/test_face_crop.py::test_align_data_fields -x` | ❌ W0 | ⬜ pending |
| 02-01-10 | 01 | 1 | ALL | integration | `python -m pytest tests/test_face_crop.py -m slow -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_alignment.py` — stubs for DET-02, DET-03 (alignment math unit tests)
- [ ] `tests/test_face_mask.py` — stubs for DET-05 mask generation
- [ ] `tests/test_face_crop.py` — stubs for DET-04, DET-05 node-level tests
- [ ] `tests/conftest.py` — add `mock_multi_face_landmarks` fixture (two faces for index testing)

*Existing test infrastructure from Phase 1 covers pytest config and basic fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual quality of aligned face | DET-03 | Subjective quality assessment | Load test image with tilted face, run FaceCropAlign, visually inspect output is upright |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
