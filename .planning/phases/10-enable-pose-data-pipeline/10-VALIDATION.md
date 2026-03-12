---
phase: 10
slug: enable-pose-data-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest, via conda env) |
| **Config file** | implicit (tests/ directory) |
| **Quick run command** | `conda run -n comfyui python -m pytest tests/ -x -v -k "not slow"` |
| **Full suite command** | `conda run -n comfyui python -m pytest tests/ -x -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n comfyui python -m pytest tests/ -x -v -k "not slow"`
- **After every plan wave:** Run `conda run -n comfyui python -m pytest tests/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | POSE-04 | unit | `conda run -n comfyui python -m pytest tests/test_face_detection.py -x -v -k "pose"` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | MRPH-01 | integration | `conda run -n comfyui python -m pytest tests/test_integration_pipeline.py -x -v -k "pose_aware"` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | POSE-04 | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py::TestPoseAttenuation -x -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_face_detection.py` — add test asserting `pose` is not None for detected faces
- [ ] `tests/test_face_detection.py` — add test asserting pose dict has expected keys (yaw, pitch, roll, matrix)
- [ ] `tests/test_integration_pipeline.py` — add test verifying pose-aware morph path is exercised end-to-end

*Existing infrastructure covers framework and fixtures; only new test stubs needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
