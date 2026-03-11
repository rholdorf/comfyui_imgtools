---
phase: 7
slug: face-model-builder
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — default discovery |
| **Quick run command** | `conda run -n comfyui pytest tests/test_face_model_builder.py -x -v` |
| **Full suite command** | `conda run -n comfyui pytest tests/ -x -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n comfyui pytest tests/test_face_model_builder.py tests/test_model_io.py -x -v`
- **After every plan wave:** Run `conda run -n comfyui pytest tests/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | MODL-01 | unit | `conda run -n comfyui pytest tests/test_face_model_builder.py::TestBuildModel -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | MODL-02 | unit | `conda run -n comfyui pytest tests/test_face_model_builder.py::TestPoseFiltering -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | MODL-04 | unit | `conda run -n comfyui pytest tests/test_face_model_builder.py::TestQualityReport -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | MODL-05 | unit | `conda run -n comfyui pytest tests/test_face_model_builder.py::TestPreviewImage -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_face_model_builder.py` — stubs for MODL-01, MODL-02, MODL-04, MODL-05
- [ ] Update `tests/test_model_io.py` — update for (478,3) stddev schema change

*Existing infrastructure (conftest.py, fixtures) covers shared needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Landmark preview visual quality | MODL-05 | Visual correctness needs human review | Load preview image, verify landmarks are plotted at correct positions on canvas |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
