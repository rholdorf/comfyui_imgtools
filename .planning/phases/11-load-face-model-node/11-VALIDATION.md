---
phase: 11
slug: load-face-model-node
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `tests/` directory (default discovery) |
| **Quick run command** | `conda run -n comfyui pytest tests/test_load_face_model.py -x -v` |
| **Full suite command** | `conda run -n comfyui pytest tests/ -x -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n comfyui pytest tests/test_load_face_model.py -x -v`
- **After every plan wave:** Run `conda run -n comfyui pytest tests/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | SC-1 | unit | `conda run -n comfyui pytest tests/test_load_face_model.py::TestLoadFaceModelNode::test_load_valid_model -x` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | SC-2 | unit | `conda run -n comfyui pytest tests/test_load_face_model.py::TestLoadFaceModelNode::test_round_trip_fidelity -x` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | SC-3 | unit | `conda run -n comfyui pytest tests/test_load_face_model.py::TestLoadFaceModelNode::test_error_cases -x` | ❌ W0 | ⬜ pending |
| 11-01-04 | 01 | 1 | SC-4 | unit | `conda run -n comfyui pytest tests/test_load_face_model.py::TestLoadFaceModelRegistration -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_load_face_model.py` — stubs for SC-1 through SC-4
- Existing `tests/test_model_io.py` already covers the underlying utility (9 tests)

*Existing infrastructure covers test framework requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
