# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-11
**Phases:** 4 | **Plans:** 8

### What Was Built
- FaceDetect node with MediaPipe 478-point landmark detection
- FaceCropAlign node with rotation correction and configurable padding
- FaceShapeMorph node with TPS warping, Procrustes alignment, and strength control
- FaceComposite node with feathered rectangular blending
- 123 tests covering all nodes and utilities

### What Worked
- TDD approach (RED → GREEN → refactor) caught issues early
- Split node architecture enabled debugging each stage independently
- scikit-image-only constraint kept dependencies light and Mac-compatible
- Phase research before planning identified key pitfalls (TPS control point selection, Procrustes normalization)

### What Was Inefficient
- FaceComposite went through 6 iterations before settling on simplest approach (direct paste)
- Initial morph control points included interior features (eyes, nose, lips) causing distortion — took 3 iterations to realize only face oval + eyebrows needed
- Reverse warp composite was over-engineered; the morphed face just needed to be pasted back

### Patterns Established
- Face oval + eyebrow endpoints (~42 points) is the right control point set for face shape morphing
- Direct paste composite (no reverse warp) when alignment is identity-like
- Procrustes with scale normalization + separate head_scale for clean shape delta

### Key Lessons
1. Start with the simplest composite approach (paste) before adding complexity (warp)
2. TPS control points should only include the geometric features you want to change — interior features should be excluded to prevent distortion
3. User visual validation is essential for face processing — automated tests can't catch "looks wrong"

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v1.0 | 4 | Initial development, TDD, iterative composite simplification |

### Cumulative Quality

| Milestone | Tests | Zero-Dep Additions |
|-----------|-------|--------------------|
| v1.0 | 123 | 2 (mediapipe, scikit-image) |

### Top Lessons (Verified Across Milestones)

1. Simplest approach first — complexity can always be added later
2. Face processing needs human-in-the-loop validation
