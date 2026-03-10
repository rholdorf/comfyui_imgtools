# Research Summary: Face Shape Morphing for comfyui_imgtools

**Domain:** Face geometry pre-processing nodes for ComfyUI face swap workflows
**Researched:** 2026-03-10
**Overall confidence:** MEDIUM (Python version compatibility is the main risk)

## Executive Summary

The face shape morphing stack for this project centers on two primary libraries: MediaPipe (v0.10.32) for face landmark detection and scikit-image (v0.26.0) for Thin Plate Spline warping. Both have native macOS ARM64 wheels and run entirely on CPU, meeting the Apple Silicon constraint. The only other new dependency is scikit-image itself -- everything else (numpy, scipy, torch, opencv, Pillow) is already in ComfyUI's dependency tree.

The biggest risk is Python version compatibility. MediaPipe only supports Python 3.9-3.12, but the system Python is 3.14 and ComfyUI recommends 3.13. This must be resolved before any development begins -- either by confirming ComfyUI runs in a 3.12 venv, or by sourcing community-built MediaPipe wheels for newer Python versions.

The architecture is a three-node pipeline (FaceCropAlign, FaceShapeMorph, FaceComposite) following ComfyUI's stateless node conventions. This mirrors FaceShaper V2's approach but with cleaner separation, no non-commercial dependencies (no Insightface), and explicit Mac support. The warping technique is Thin Plate Spline using ~60 face contour control points (not all 478 landmarks), with interior facial features pinned as anchors to prevent distortion.

The existing competitor, ComfyUI_FaceShaper, validates demand but has limitations: it requires LivePortrait model files, has no explicit Mac support, and its Insightface option carries non-commercial license restrictions. Our approach is deliberately simpler and Mac-first.

## Key Findings

**Stack:** MediaPipe 0.10.32 (face landmarks) + scikit-image 0.26.0 (TPS warping) + existing ComfyUI deps. Two new pip packages total.

**Architecture:** Three stateless nodes: crop/align, morph (TPS), composite (feathered mask). Custom LANDMARKS and TRANSFORM types passed between nodes.

**Critical pitfall:** Python 3.14/3.13 incompatibility with MediaPipe (only supports 3.9-3.12). Must verify/resolve before development.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Environment & Detection Setup** - Verify Python compatibility, install MediaPipe, implement face landmark detection
   - Addresses: Python version risk, model file distribution, basic face detection
   - Avoids: Building on an incompatible foundation

2. **Face Crop & Alignment** - Build FaceCropAlign node with eye-line rotation and padded crop
   - Addresses: Face normalization, rotation handling, coordinate space management
   - Avoids: Rotation black-corner artifacts, coordinate mismatch bugs

3. **Face Shape Morphing** - Build FaceShapeMorph node with TPS warping and strength control
   - Addresses: Core value proposition, landmark subset selection, feature anchoring
   - Avoids: Full-478-point TPS (too slow), feature distortion

4. **Compositing & Integration** - Build FaceComposite node, end-to-end pipeline testing
   - Addresses: Feathered blending, reverse transform, workflow integration with ReActor
   - Avoids: Seam artifacts, compositing color mismatches

**Phase ordering rationale:**
- Phase 1 must come first because MediaPipe compatibility is a potential blocker
- Phase 2 before Phase 3 because TPS warping requires aligned, cropped faces
- Phase 4 last because compositing depends on all upstream outputs being correct

**Research flags for phases:**
- Phase 1: Needs investigation -- verify Python version in ComfyUI's actual runtime environment
- Phase 2: Standard patterns, unlikely to need research
- Phase 3: May need experimentation with TPS control point selection and regularization
- Phase 4: Standard patterns, feathered blending is well-documented

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | MediaPipe and scikit-image are well-verified, but Python 3.14 compatibility is unresolved |
| Features | HIGH | Feature set is well-defined by PROJECT.md and validated by FaceShaper's existence |
| Architecture | HIGH | Three-node pattern follows ComfyUI conventions; data flow is straightforward |
| Pitfalls | HIGH | Well-documented domain; TPS, compositing, and coordinate space issues are known |

## Gaps to Address

- **Python version**: Must verify what Python version ComfyUI actually uses at runtime (not just system Python)
- **TPS control point tuning**: Exact landmark indices for optimal face contour warping will require experimentation
- **face_landmarker.task model distribution**: Need to decide bundling vs auto-download strategy
- **MediaPipe new API stability**: The Face Landmarker task API is newer; verify it works correctly on macOS ARM64 with actual test images
- **scikit-image TPS performance**: The `from_estimate` API is new in 0.26.0; verify it produces smooth warps with face landmark data
