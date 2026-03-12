# Phase 11: LoadFaceModel Node - Research

**Researched:** 2026-03-12
**Domain:** ComfyUI node implementation (thin wrapper over existing utility)
**Confidence:** HIGH

## Summary

Phase 11 closes the model persistence gap identified in the v1.1 milestone audit: `utils/model_io.py` already exports a fully tested `load_face_model()` function, but no ComfyUI node wraps it. Users can save `.facemodel.npz` files via FaceModelBuilder but cannot reload them in new sessions.

This is the simplest possible phase -- a single ComfyUI node class (`LoadFaceModel`) that accepts a file path string, calls `load_face_model()`, and outputs a `FACE_MODEL` dict. The entire load/validate/error-handling logic already exists in `utils/model_io.py` with 9 passing tests covering round-trip fidelity, missing files, wrong versions, wrong shapes, and wrong dtypes.

**Primary recommendation:** Create a single-file `face_model_loader.py` node following the exact same patterns as `face_model_builder.py` (try/except error boundary, `[NodeName]` prefixed print diagnostics, empty dict fallback on error). Register it in `__init__.py` under the existing `_face_nodes_available` guard.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | (existing) | NPZ file loading via `np.load` | Already used by `load_face_model()` |

### Supporting
No new dependencies. `load_face_model()` in `utils/model_io.py` handles all file I/O.

## Architecture Patterns

### Existing Node Registration Pattern (from `__init__.py`)

All face nodes follow this exact pattern:
1. Import in the `try` block under `_face_nodes_available`
2. Add to `NODE_CLASS_MAPPINGS` with class name as key
3. Add to `NODE_DISPLAY_NAME_MAPPINGS` with `"ImgTools "` prefix

```python
# In __init__.py try block:
from .face_model_loader import LoadFaceModel

# In if _face_nodes_available block:
NODE_CLASS_MAPPINGS["LoadFaceModel"] = LoadFaceModel
NODE_DISPLAY_NAME_MAPPINGS["LoadFaceModel"] = "ImgTools Load Face Model"
```

### Existing Node Class Pattern (from FaceModelBuilder, FaceModelMorph)

Every node in this project follows:
```python
class NodeName:
    """Docstring."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": { ... },
            "optional": { ... },
        }

    RETURN_TYPES = (...)
    RETURN_NAMES = (...)
    FUNCTION = "method_name"
    CATEGORY = "imgtools/face"

    def method_name(self, ...):
        try:
            # Core logic
            return (result,)
        except ValueError as e:
            print(f"[NodeName] Warning: {e}")
            return (fallback,)
        except Exception as e:
            print(f"[NodeName] Warning: Unexpected error: {e}")
            return (fallback,)
```

### Error Boundary Pattern (from Phase 9 decisions)

- `try/except` with `ValueError` and generic `Exception` caught separately
- Print with `[LoadFaceModel]` prefix for grep-friendly diagnostics
- Return empty dict `{}` as fallback FACE_MODEL (consistent with FaceModelBuilder error path)
- FaceModelMorph already handles empty/invalid face_model dicts gracefully (lines 123-136 in face_model_morph.py)

### The `load_face_model` Function (already implemented and tested)

```python
# Source: utils/model_io.py
def load_face_model(path: str | Path) -> dict:
    """Load and validate a .facemodel.npz file.

    Returns:
        Dict with keys: version, canonical_landmarks, head_dimensions,
        control_indices, landmark_stddev.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If file has missing fields, wrong version, or wrong shapes.
    """
```

Key facts:
- Uses `allow_pickle=False` for security (Phase 6 decision)
- Validates version, all required keys, dtype kinds, and array shapes
- Reconstructs `head_dimensions` from flat `(3,)` array to `{"width", "height", "depth"}` dict
- Returns plain dict (closes NpzFile handle before returning)
- MODEL_VERSION = "2"

### Anti-Patterns to Avoid
- **Don't duplicate validation logic:** `load_face_model()` already validates everything. The node should NOT add its own schema checks.
- **Don't use `allow_pickle=True`:** Security decision from Phase 6. The utility function already enforces this.
- **Don't return error strings as FACE_MODEL:** Return empty dict `{}` on error (consistent with FaceModelBuilder).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NPZ validation | Custom schema checks in node | `load_face_model()` | Already validates version, keys, dtypes, shapes |
| Error messages | Custom error formatting | Exception messages from `load_face_model()` | Already clear and specific |
| File path resolution | Custom path logic | `pathlib.Path` (already in `load_face_model`) | Handles all OS path variants |

## Common Pitfalls

### Pitfall 1: Forgetting FileNotFoundError in the except chain
**What goes wrong:** `load_face_model` raises `FileNotFoundError` (not `ValueError`) for missing files.
**How to avoid:** Catch both `FileNotFoundError` and `ValueError` explicitly, or catch `Exception` as the outer boundary.

### Pitfall 2: Not testing with FaceModelMorph downstream
**What goes wrong:** LoadFaceModel output might not be consumed correctly by FaceModelMorph.
**How to avoid:** The round-trip test should verify that loading a saved model produces a dict identical to what FaceModelBuilder outputs. The existing `test_model_io.py::TestRoundTrip` already covers this at the utility level; a node-level test should verify the ComfyUI wrapper passes through correctly.

### Pitfall 3: ComfyUI STRING input for file path
**What goes wrong:** Using the wrong widget type for file path input.
**How to avoid:** Use `("STRING", {"default": ""})` -- same pattern as FaceModelBuilder's `save_path` and `directory` inputs. ComfyUI does not have a native file picker widget; STRING is the standard approach for paths.

## Code Examples

### LoadFaceModel Node Implementation Pattern

```python
"""LoadFaceModel ComfyUI node - loads a saved .facemodel.npz file."""

from .utils.model_io import load_face_model


class LoadFaceModel:
    """Load a previously saved .facemodel.npz file as a FACE_MODEL.

    Accepts a file path and outputs a FACE_MODEL dict that can be
    connected to FaceModelMorph for face shape morphing.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("FACE_MODEL",)
    RETURN_NAMES = ("face_model",)
    FUNCTION = "load_model"
    CATEGORY = "imgtools/face"

    def load_model(self, file_path: str):
        if not file_path.strip():
            print("[LoadFaceModel] Warning: empty file path")
            return ({},)

        try:
            model_dict = load_face_model(file_path)
            return (model_dict,)
        except FileNotFoundError as e:
            print(f"[LoadFaceModel] Warning: {e}")
            return ({},)
        except ValueError as e:
            print(f"[LoadFaceModel] Warning: {e}")
            return ({},)
        except Exception as e:
            print(f"[LoadFaceModel] Warning: Unexpected error: {e}")
            return ({},)
```

## State of the Art

No changes -- this phase uses only existing infrastructure (`np.load`, `np.savez_compressed`) that has been stable for years.

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pickle-based model files | NPZ with `allow_pickle=False` | Phase 6 decision | Security -- prevents arbitrary code execution |

## Open Questions

None. The implementation is fully defined by existing patterns and the already-tested `load_face_model()` function.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `tests/` directory (no pytest.ini, uses default discovery) |
| Quick run command | `conda run -n comfyui pytest tests/test_load_face_model.py -x -v` |
| Full suite command | `conda run -n comfyui pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SC-1 | LoadFaceModel accepts file path, outputs FACE_MODEL | unit | `conda run -n comfyui pytest tests/test_load_face_model.py::TestLoadFaceModelNode::test_load_valid_model -x` | Wave 0 |
| SC-2 | Loaded model matches original save data | unit | `conda run -n comfyui pytest tests/test_load_face_model.py::TestLoadFaceModelNode::test_round_trip_fidelity -x` | Wave 0 |
| SC-3 | Invalid/missing file produces clear error | unit | `conda run -n comfyui pytest tests/test_load_face_model.py::TestLoadFaceModelNode::test_error_cases -x` | Wave 0 |
| SC-4 | Node registered in __init__.py | unit | `conda run -n comfyui pytest tests/test_load_face_model.py::TestLoadFaceModelRegistration -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `conda run -n comfyui pytest tests/test_load_face_model.py -x -v`
- **Per wave merge:** `conda run -n comfyui pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_load_face_model.py` -- covers SC-1 through SC-4
- Existing `tests/test_model_io.py` already covers the underlying utility (9 tests); node tests only need to verify the ComfyUI wrapper behavior

## Sources

### Primary (HIGH confidence)
- `utils/model_io.py` -- existing `load_face_model()` implementation with full validation
- `tests/test_model_io.py` -- 9 existing tests proving round-trip fidelity and error handling
- `__init__.py` -- node registration pattern (6 nodes already registered)
- `face_model_builder.py` -- reference node pattern (error boundary, fallback returns)
- `face_model_morph.py` -- downstream consumer showing how FACE_MODEL dict is validated/used
- `.planning/v1.1-MILESTONE-AUDIT.md` -- gap identification (integration issue #2)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing code
- Architecture: HIGH -- follows exact patterns of 6 existing nodes
- Pitfalls: HIGH -- very thin wrapper, minimal surface area for bugs

**Research date:** 2026-03-12
**Valid until:** Indefinite (stable patterns, no external dependencies)
