---
phase: 4
slug: compositing-and-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_face_composite.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_face_composite.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | COMP-03 | unit | `pytest tests/test_face_composite.py::TestReverseTransform -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | COMP-01 | unit | `pytest tests/test_face_composite.py::TestCompositing -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | COMP-02 | unit | `pytest tests/test_face_composite.py::TestBlending -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | COMP-04 | unit | `pytest tests/test_face_composite.py::TestOutputs -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_face_composite.py` — stubs for COMP-01 through COMP-04
- [ ] Test fixtures: deterministic align_data with identity and rotated transforms, synthetic morphed face images, feathered mask arrays

*Existing infrastructure covers framework requirements (pytest already configured in pyproject.toml).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual seam quality | COMP-02 | Perceptual quality requires visual inspection | Load test images in ComfyUI, run full pipeline, inspect face-background transition at 200% zoom |
| Natural-looking end-to-end result | COMP-04 | Subjective visual quality assessment | Run 3-node pipeline with real face images, verify result looks natural |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
