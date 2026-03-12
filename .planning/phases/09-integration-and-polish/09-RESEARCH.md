# Phase 9: Integration and Polish - Research

**Researched:** 2026-03-12
**Domain:** Edge case hardening, error handling, end-to-end validation
**Confidence:** HIGH

## Summary

Phase 9 addresses two integration requirements (INTG-01, INTG-02) focused on making the model-based pipeline robust against real-world edge cases. The core pipeline code is already complete and functional from phases 5-8. What remains is adding user-friendly error handling to the ComfyUI node layer and validating the full pipeline end-to-end.

The FaceModelBuilder node currently lets `ValueError` exceptions from `build_face_model()` propagate uncaught, which would crash ComfyUI. The FaceModelMorph node has a broad `except Exception` that silently passes through on any error, but provides no diagnostic information. Both nodes need to produce clear error messages (via quality report strings or ComfyUI conventions) instead of crashes or silent failures.

**Primary recommendation:** Wrap node-level `build_model()` in try/except with descriptive error messages returned through existing output channels (quality_report STRING for FaceModelBuilder, passthrough with logging for FaceModelMorph). Add edge case tests for all specified scenarios. Add one integration test covering the full pipeline chain.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTG-01 | FaceModelBuilder handles edge cases: empty directory, all images rejected, single image, no face detected | Error handling gaps identified in `build_face_model()` and `FaceModelBuilder.build_model()` -- see Architecture Patterns |
| INTG-02 | FaceModelMorph handles edge case: malformed or incompatible model file | Model dict validation gap identified in `FaceModelMorph.morph()` -- see Architecture Patterns |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | existing | Test framework | Already used across 221 tests |
| numpy | existing | Array operations | Already a core dependency |
| torch | existing | ComfyUI tensor format | Already used in all nodes |
| unittest.mock | stdlib | Mocking MediaPipe in tests | Already used in model_builder tests |

### Supporting
No new libraries needed. All edge case handling uses existing Python builtins and project patterns.

## Architecture Patterns

### Current Error Handling Inventory

**FaceModelBuilder flow:**
1. `scan_images(directory)` -- raises `ValueError` if directory doesn't exist; returns `[]` for empty/no-images directory
2. `build_face_model()` -- raises `ValueError("No accepted images...")` if all rejected/no faces
3. `FaceModelBuilder.build_model()` -- **NO try/except** -- exceptions propagate to ComfyUI and crash the workflow

**FaceModelMorph flow:**
1. `FaceModelMorph.morph()` -- **broad `except Exception` on line 218** catches everything and returns passthrough silently
2. No validation of `face_model` dict keys (canonical_landmarks, head_dimensions)
3. No error logging -- user gets no indication of why passthrough occurred

### Pattern 1: FaceModelBuilder Edge Cases (INTG-01)

**What:** Wrap `build_model()` in try/except and return meaningful outputs for all failure modes.

**Edge cases to handle:**
| Case | Current behavior | Required behavior |
|------|-----------------|-------------------|
| Empty directory (no images) | `build_face_model` raises ValueError("No accepted images") | Return error in quality_report STRING, empty model, black preview |
| All images rejected | Same ValueError | Return error in quality_report with rejection details |
| Single image accepted | Works correctly already | Verify with test (should work, stddev=0) |
| No face detected in any image | Same ValueError | Return error in quality_report listing NO FACE images |
| Directory doesn't exist | `scan_images` raises ValueError("Directory not found") | Return error in quality_report |

**Implementation approach:**
```python
def build_model(self, directory, yaw_threshold=45.0, pitch_threshold=30.0, save_path=""):
    try:
        model_dict, results, actual_save_path = build_face_model(
            directory, yaw_threshold, pitch_threshold, save_path
        )
        # ... existing success path ...
        return (model_dict, report, preview_tensor)
    except ValueError as e:
        # Return empty/placeholder outputs with error in report
        error_report = f"ERROR: {str(e)}"
        empty_model = {}  # or a sentinel
        black_preview = torch.zeros(1, 512, 512, 3, dtype=torch.float32)
        return (empty_model, error_report, black_preview)
    except Exception as e:
        error_report = f"ERROR: Unexpected error: {str(e)}"
        empty_model = {}
        black_preview = torch.zeros(1, 512, 512, 3, dtype=torch.float32)
        return (empty_model, error_report, black_preview)
```

**Key design decision:** Return errors through the STRING output (quality_report) rather than raising exceptions. This follows ComfyUI convention where nodes should not crash -- they should return valid outputs with error information.

### Pattern 2: FaceModelMorph Model Validation (INTG-02)

**What:** Validate face_model dict structure before accessing keys. Provide diagnostic logging on failure.

**Edge cases to handle:**
| Case | Current behavior | Required behavior |
|------|-----------------|-------------------|
| Model is empty dict `{}` | KeyError caught by broad except -> silent passthrough | Log warning, passthrough |
| Model missing canonical_landmarks | KeyError -> silent passthrough | Log warning with specific missing key |
| Model has wrong landmark shape | Downstream crash -> silent passthrough | Log warning, passthrough |
| Model from incompatible version | Depends on how model was loaded | Log warning about version mismatch |

**Implementation approach:**
```python
def morph(self, source_image, face_model, source_landmarks, source_align_data, strength=0.5, symmetrize=False):
    h, w = source_image.shape[1], source_image.shape[2]

    # Validate model
    if not face_model or not isinstance(face_model, dict):
        print("[FaceModelMorph] Warning: empty or invalid face_model, returning passthrough")
        return self._passthrough(source_image, h, w, source_align_data)

    required_keys = ("canonical_landmarks", "head_dimensions")
    missing = [k for k in required_keys if k not in face_model]
    if missing:
        print(f"[FaceModelMorph] Warning: face_model missing keys: {missing}, returning passthrough")
        return self._passthrough(source_image, h, w, source_align_data)

    # ... rest of existing code ...
```

### Pattern 3: End-to-End Pipeline Test

**What:** Integration test that chains FaceModelBuilder output -> FaceModelMorph -> FaceComposite using mocked MediaPipe.

**Approach:** Mock `extract_landmarks` at module level (established pattern from Phase 7). Use synthetic images. Verify the pipeline produces valid output shapes without crashes.

### Anti-Patterns to Avoid
- **Silent swallow:** The current `except Exception: return passthrough` in FaceModelMorph loses all diagnostic info. Always log/print a warning.
- **Raising exceptions from ComfyUI nodes:** Nodes must return valid tuples. Never let exceptions propagate to ComfyUI.
- **Over-validating:** Don't add redundant checks deep in utility functions that already work correctly. Validate at the node boundary only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Error reporting | Custom error type system | `print()` warnings + STRING output | ComfyUI has no structured error channel; print() goes to console, STRING goes to user |
| Model validation | Schema validator library | Simple dict key checks | Only 2-3 keys to check, no need for jsonschema etc. |

## Common Pitfalls

### Pitfall 1: Empty Dict as FACE_MODEL Sentinel
**What goes wrong:** Returning `{}` as an empty model from FaceModelBuilder can crash FaceModelMorph if the user connects them.
**Why it happens:** ComfyUI passes outputs to connected inputs automatically.
**How to avoid:** FaceModelMorph must validate model dict before use. Use `{}` (empty dict) as the error sentinel from FaceModelBuilder, and check for it in FaceModelMorph.

### Pitfall 2: Single Image Edge Case
**What goes wrong:** `compute_weighted_average` with a single image produces zero stddev, which is valid but might cause concerns.
**Why it happens:** No variance when N=1.
**How to avoid:** This is actually fine. Test confirms it works. The quality report should note "1 image" for the user.

### Pitfall 3: Test Count Regression
**What goes wrong:** New tests pass but old tests break.
**Why it happens:** Modifying node classes can change import paths or break mocks.
**How to avoid:** Run full test suite (`pytest tests/ -x -v`) after every change. Current count: 221 tests. Must not decrease.

### Pitfall 4: Empty Directory vs Non-Existent Directory
**What goes wrong:** Different error paths for "directory doesn't exist" vs "directory exists but has no images."
**Why it happens:** `scan_images` raises ValueError for non-existent dir but returns `[]` for empty dir.
**How to avoid:** Handle both in the try/except. The "no images found" case flows through to "No accepted images" ValueError.

## Code Examples

### Existing Error Handling Pattern (model_io.py)
```python
# Source: utils/model_io.py lines 61-117
def load_face_model(path):
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    # ... validates keys, version, shapes with clear ValueError messages
```

### Existing Passthrough Pattern (FaceModelMorph)
```python
# Source: face_model_morph.py lines 332-336
@staticmethod
def _passthrough(source_image, h, w, align_data):
    full_mask = torch.ones(1, h, w, dtype=torch.float32)
    return (source_image, full_mask, align_data)
```

### Existing ComfyUI Error Convention (FaceComposite)
```python
# Source: face_composite.py lines 73-155
# Wraps entire composite() in try/except Exception -> _passthrough
# This is the pattern to follow, but add print() warnings
```

### Test Mock Pattern (from test_face_model_builder.py)
```python
# Source: tests/test_face_model_builder.py lines 301-380
@patch("utils.model_builder.process_image")
@patch("utils.model_builder.scan_images")
def test_orchestrates_full_pipeline(self, mock_scan, mock_process, tmp_path):
    # Mock scan and process at module level to avoid real MediaPipe
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | tests/conftest.py |
| Quick run command | `conda run -n comfyui python -m pytest tests/ -x -v` |
| Full suite command | `conda run -n comfyui python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTG-01a | Empty directory -> error in quality_report | unit | `conda run -n comfyui python -m pytest tests/test_face_model_builder.py -x -k "empty_dir"` | No - Wave 0 |
| INTG-01b | All images rejected -> error in quality_report | unit | `conda run -n comfyui python -m pytest tests/test_face_model_builder.py -x -k "all_rejected"` | No - Wave 0 |
| INTG-01c | Single image -> valid model | unit | `conda run -n comfyui python -m pytest tests/test_face_model_builder.py -x -k "single_image"` | No - Wave 0 |
| INTG-01d | No face detected -> error in quality_report | unit | `conda run -n comfyui python -m pytest tests/test_face_model_builder.py -x -k "no_face"` | No - Wave 0 |
| INTG-01e | Directory doesn't exist -> error in quality_report | unit | `conda run -n comfyui python -m pytest tests/test_face_model_builder.py -x -k "nonexistent"` | No - Wave 0 |
| INTG-02a | Empty model dict -> passthrough + warning | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py -x -k "empty_model"` | No - Wave 0 |
| INTG-02b | Model missing keys -> passthrough + warning | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py -x -k "missing_keys"` | No - Wave 0 |
| INTG-02c | Model wrong shape -> passthrough + warning | unit | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py -x -k "wrong_shape"` | No - Wave 0 |
| E2E | Full pipeline chain produces valid output | integration | `conda run -n comfyui python -m pytest tests/test_face_model_morph.py -x -k "e2e_pipeline"` | No - Wave 0 |
| REGR | All 221 existing tests pass | regression | `conda run -n comfyui python -m pytest tests/ -v` | Yes |

### Sampling Rate
- **Per task commit:** `conda run -n comfyui python -m pytest tests/ -x -v`
- **Per wave merge:** `conda run -n comfyui python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] New tests in `tests/test_face_model_builder.py` -- INTG-01 edge case tests (5 tests)
- [ ] New tests in `tests/test_face_model_morph.py` -- INTG-02 edge case tests (3 tests)
- [ ] New E2E test -- either in existing file or new `tests/test_integration_pipeline.py` (1 test)
- No new framework install needed. No new conftest fixtures needed.

## Open Questions

1. **FACE_MODEL sentinel value for errors**
   - What we know: FaceModelBuilder must return a 3-tuple always. When an error occurs, it needs a placeholder for FACE_MODEL.
   - What's unclear: Should it be `{}` (empty dict) or `None`? ComfyUI may not handle `None` for custom types gracefully.
   - Recommendation: Use `{}` (empty dict). FaceModelMorph already needs to validate the model dict anyway (INTG-02), so it will catch this.

2. **Print warnings vs logging**
   - What we know: ComfyUI nodes typically use `print()` for console output. No structured logging framework in project.
   - What's unclear: Whether to use Python `logging` module or simple `print()`.
   - Recommendation: Use `print()` with `[FaceModelBuilder]`/`[FaceModelMorph]` prefix, matching the existing `__init__.py` pattern (`print(f"[ImgTools] Warning: ...")`).

## Sources

### Primary (HIGH confidence)
- Direct code analysis of `face_model_builder.py`, `face_model_morph.py`, `face_composite.py`, `utils/model_builder.py`, `utils/model_io.py`
- Direct analysis of existing test files (221 tests across 13 test files)
- `__init__.py` error handling pattern (lines 3-14)

### Secondary (MEDIUM confidence)
- ComfyUI node conventions (return tuples, don't raise) -- inferred from existing node patterns in this codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, all existing
- Architecture: HIGH - patterns derived from direct code analysis of existing nodes
- Pitfalls: HIGH - identified from actual code gaps in current implementation

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable domain, no external dependencies changing)
