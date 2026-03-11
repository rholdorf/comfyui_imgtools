---
phase: 6
slug: model-persistence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | none (uses default discovery) |
| **Quick run command** | `conda run -n comfyui pytest tests/test_model_io.py -x -v` |
| **Full suite command** | `conda run -n comfyui pytest tests/ -x -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n comfyui pytest tests/test_model_io.py -x -v`
- **After every plan wave:** Run `conda run -n comfyui pytest tests/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | MODL-03a | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_save_creates_file -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | MODL-03b | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_round_trip -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | MODL-03c | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_missing_field_raises -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | MODL-03d | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_wrong_version_raises -x` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 1 | MODL-03e | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_wrong_shape_raises -x` | ❌ W0 | ⬜ pending |
| 06-01-06 | 01 | 1 | MODL-03f | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_file_size -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_model_io.py` — stubs for MODL-03 (all sub-requirements)
- [ ] `utils/model_io.py` — the module under test

*Wave 0 creates both the test file and implementation module.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
