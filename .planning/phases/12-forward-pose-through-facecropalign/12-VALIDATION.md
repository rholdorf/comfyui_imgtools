---
phase: 12
slug: forward-pose-through-facecropalign
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest in conda env) |
| **Config file** | tests/conftest.py |
| **Quick run command** | `conda run -n comfyui python -m pytest tests/test_face_crop.py tests/test_face_model_morph.py -x -v` |
| **Full suite command** | `conda run -n comfyui python -m pytest tests/ -x -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n comfyui python -m pytest tests/test_face_crop.py tests/test_face_model_morph.py -x -v`
- **After every plan wave:** Run `conda run -n comfyui python -m pytest tests/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | POSE-04 | unit | `conda run -n comfyui python -m pytest tests/test_face_crop.py -x -v -k pose` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | MRPH-01 | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py -x -v -k pose_aware` | ✅ partial | ⬜ pending |
| 12-01-03 | 01 | 1 | POSE-04, MRPH-01 | integration | `conda run -n comfyui python -m pytest tests/test_face_crop.py tests/test_face_model_morph.py -x -v -k chain` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_face_crop.py` — add pose forwarding tests (pose present, pose absent, degenerate crop)
- [ ] `tests/test_face_model_morph.py` — add end-to-end test verifying pose-aware path triggers through CropAlign output format

*Existing infrastructure covers framework and fixture basics.*

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
