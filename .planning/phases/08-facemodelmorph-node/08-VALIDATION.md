---
phase: 8
slug: facemodelmorph-node
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | none — `pytest tests/ -x -v` from project root |
| **Quick run command** | `conda run -n comfyui pytest tests/test_face_model_morph.py -x -v` |
| **Full suite command** | `conda run -n comfyui pytest tests/ -x -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `conda run -n comfyui pytest tests/test_face_model_morph.py -x -v`
- **After every plan wave:** Run `conda run -n comfyui pytest tests/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | MRPH-01 | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestMorphOutput -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | MRPH-01 | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestStrength -x` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | MRPH-01 | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestPoseAwareDelta -x` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 1 | MRPH-01 | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestFallbackPath -x` | ❌ W0 | ⬜ pending |
| 08-01-05 | 01 | 1 | MRPH-02 | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestAlignData -x` | ❌ W0 | ⬜ pending |
| 08-01-06 | 01 | 1 | MRPH-03 | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestSymmetrize -x` | ❌ W0 | ⬜ pending |
| 08-01-07 | 01 | 1 | POSE-04 | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestPoseAttenuation -x` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | N/A | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestRegistration -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 1 | N/A | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestConventions -x` | ❌ W0 | ⬜ pending |
| 08-02-03 | 02 | 1 | N/A | unit | `conda run -n comfyui pytest tests/test_face_model_morph.py::TestGracefulDegradation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_face_model_morph.py` — all MRPH-01/02/03 and POSE-04 tests
- [ ] Synthetic FACE_MODEL fixture (deterministic canonical_landmarks + head_dimensions)
- [ ] Synthetic source_landmarks fixture with pose data (3D landmarks + transformation matrix)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual morph quality on real photos | MRPH-01 | Subjective visual quality assessment | Load test image in ComfyUI, connect FaceModelMorph, verify face shape changes naturally |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
