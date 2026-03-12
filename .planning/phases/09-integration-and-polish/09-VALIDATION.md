---
phase: 9
slug: integration-and-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | tests/conftest.py |
| **Quick run command** | `conda run -n comfyui python -m pytest tests/ -x -v` |
| **Full suite command** | `conda run -n comfyui python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n comfyui python -m pytest tests/ -x -v`
- **After every plan wave:** Run `conda run -n comfyui python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 0 | INTG-01 | unit | `conda run -n comfyui python -m pytest tests/test_face_model_builder.py -x -k "empty_dir"` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 0 | INTG-01 | unit | `conda run -n comfyui python -m pytest tests/test_face_model_builder.py -x -k "all_rejected"` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 0 | INTG-01 | unit | `conda run -n comfyui python -m pytest tests/test_face_model_builder.py -x -k "single_image"` | ❌ W0 | ⬜ pending |
| 09-01-04 | 01 | 0 | INTG-01 | unit | `conda run -n comfyui python -m pytest tests/test_face_model_builder.py -x -k "no_face"` | ❌ W0 | ⬜ pending |
| 09-01-05 | 01 | 0 | INTG-02 | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py -x -k "empty_model"` | ❌ W0 | ⬜ pending |
| 09-01-06 | 01 | 0 | INTG-02 | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py -x -k "missing_keys"` | ❌ W0 | ⬜ pending |
| 09-01-07 | 01 | 0 | INTG-02 | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py -x -k "wrong_shape"` | ❌ W0 | ⬜ pending |
| 09-01-08 | 01 | 0 | INTG-01, INTG-02 | integration | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py -x -k "e2e_pipeline"` | ❌ W0 | ⬜ pending |
| REGR | - | - | ALL | regression | `conda run -n comfyui python -m pytest tests/ -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_face_model_builder.py` — INTG-01 edge case tests (empty dir, all rejected, single image, no face, nonexistent dir)
- [ ] `tests/test_face_model_morph.py` — INTG-02 edge case tests (empty model, missing keys, wrong shape)
- [ ] E2E pipeline test — full chain produces valid output

*Existing infrastructure (pytest, conftest.py) covers framework needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
