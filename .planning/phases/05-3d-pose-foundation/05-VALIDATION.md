---
phase: 5
slug: 3d-pose-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | None (uses default discovery in `tests/`) |
| **Quick run command** | `conda run -n comfyui python -m pytest tests/test_pose_utils.py -x -v` |
| **Full suite command** | `conda run -n comfyui python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n comfyui python -m pytest tests/test_pose_utils.py -x -v`
- **After every plan wave:** Run `conda run -n comfyui python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 0 | POSE-01 | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_extract_pose_identity -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 0 | POSE-01 | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_extract_pose_known_rotation -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 0 | POSE-01 | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_extract_pose_with_scale -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 0 | POSE-02 | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_frontalize_identity -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 0 | POSE-02 | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_frontalize_accuracy -x` | ❌ W0 | ⬜ pending |
| 05-01-06 | 01 | 0 | POSE-02 | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_frontalize_no_matrix -x` | ❌ W0 | ⬜ pending |
| 05-01-07 | 01 | 0 | POSE-03 | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_normalize_ipd -x` | ❌ W0 | ⬜ pending |
| 05-01-08 | 01 | 0 | POSE-03 | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_normalize_cross_face -x` | ❌ W0 | ⬜ pending |
| 05-01-09 | 01 | 0 | POSE-03 | unit | `conda run -n comfyui python -m pytest tests/test_pose_utils.py::test_normalize_zero_ipd -x` | ❌ W0 | ⬜ pending |
| 05-REG | ALL | ALL | ALL | regression | `conda run -n comfyui python -m pytest tests/ -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_pose_utils.py` — stubs for POSE-01, POSE-02, POSE-03
- [ ] Test fixtures for known rotation matrices (identity, 30-deg yaw, 45-deg yaw, 30-deg pitch)
- [ ] Test fixtures for synthetic 3D landmarks (frontal face with known geometry)

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
