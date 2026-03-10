---
phase: 1
slug: environment-and-detection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `conda run -n ComfyUI pytest tests/ -x -q` |
| **Full suite command** | `conda run -n ComfyUI pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n ComfyUI pytest tests/ -x -q`
- **After every plan wave:** Run `conda run -n ComfyUI pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | DET-01, PLAT-01, PLAT-03 | unit/integration stubs | `conda run -n ComfyUI pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | PLAT-01 | smoke | `conda run -n ComfyUI pytest tests/test_mediapipe_helper.py::test_landmarker_creation -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | DET-01 | integration | `conda run -n ComfyUI pytest tests/test_face_detection.py::test_detect_landmarks_count -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | DET-01 | unit | `conda run -n ComfyUI pytest tests/test_face_detection.py::test_landmarks_data_structure -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | DET-01 | unit | `conda run -n ComfyUI pytest tests/test_face_detection.py::test_no_face_returns_empty -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | PLAT-03 | unit | `conda run -n ComfyUI pytest tests/test_face_detection.py::test_node_conventions -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — package init
- [ ] `tests/conftest.py` — shared fixtures (sample test image with face, mock landmark data, ComfyUI-format tensor fixture)
- [ ] `tests/test_face_detection.py` — covers DET-01, PLAT-03
- [ ] `tests/test_mediapipe_helper.py` — covers PLAT-01 (model download, landmarker creation)
- [ ] `pyproject.toml` [tool.pytest] section — test configuration

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Only mediapipe+scikit-image as new deps | PLAT-02 | Requires inspecting requirements.txt | Verify requirements.txt contains only mediapipe and scikit-image as new dependencies |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
