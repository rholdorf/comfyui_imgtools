# Phase 6: Model Persistence - Research

**Researched:** 2026-03-11
**Domain:** NumPy NPZ file persistence, versioned binary format, round-trip fidelity
**Confidence:** HIGH

## Summary

Phase 6 implements save/load for a `.facemodel.npz` file that stores a canonical face model (~6 KB). The file contains canonical landmarks (478x2 float64), head dimensions (dict with width/height/depth floats), control point indices (int array), per-landmark stddev (478x2 float64), and version metadata.

NumPy's `np.savez_compressed` is the standard tool for this. It produces a zip-compressed archive of named `.npy` arrays with full dtype/shape preservation. Round-trip fidelity is guaranteed by NumPy's binary format -- save and load produce bit-identical arrays. The main engineering work is: (1) defining the schema, (2) validation on load with clear error messages, and (3) version metadata for future-proofing.

**Primary recommendation:** Use `np.savez_compressed` for writing and `np.load` for reading, with a strict validation function that checks every expected key, dtype, and shape before returning the model dict.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODL-03 | FaceModelBuilder saves model as versioned .facemodel.npz (~6KB) with canonical landmarks and head dimensions | NPZ format via `np.savez_compressed` handles all array types; version stored as 0-d string array; validation function ensures fidelity |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | (existing) | `savez_compressed` / `load` for NPZ I/O | Already a dependency; NPZ is NumPy's native archive format with guaranteed round-trip fidelity |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | Path handling for model files | File path construction and validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| NPZ | JSON + base64 | Human-readable but ~4x larger, slower, no dtype guarantee |
| NPZ | pickle | Smaller code but security risk with untrusted files, not needed |
| NPZ | HDF5 (h5py) | Overkill for ~6KB; adds dependency |

**Installation:**
No new dependencies required. NumPy is already in the project.

## Architecture Patterns

### Recommended Project Structure
```
utils/
    model_io.py          # save_face_model() and load_face_model()
tests/
    test_model_io.py     # Round-trip, validation, error handling tests
```

### Pattern 1: Flat NPZ with Version Key
**What:** Store all model data as named arrays in a single NPZ file, including a version string as a 0-d numpy array.
**When to use:** Always -- this is the only pattern needed for this phase.
**Example:**
```python
import numpy as np
from pathlib import Path

# Current schema version
MODEL_VERSION = "1"

# Expected keys and their (dtype_kind, shape) constraints
_SCHEMA = {
    "version":           ("U", ()),           # 0-d unicode string
    "canonical_landmarks": ("f", (478, 2)),   # float64
    "head_dimensions":   ("f", (3,)),          # [width, height, depth] float64
    "control_indices":   ("i", None),          # 1-d int, length varies
    "landmark_stddev":   ("f", (478, 2)),      # float64
}


def save_face_model(path: str | Path, *, canonical_landmarks, head_dimensions,
                    control_indices, landmark_stddev):
    """Save a face model to a .facemodel.npz file."""
    path = Path(path)
    # head_dimensions stored as array [width, height, depth]
    head_dims_arr = np.array([
        head_dimensions["width"],
        head_dimensions["height"],
        head_dimensions["depth"],
    ], dtype=np.float64)

    np.savez_compressed(
        path,
        version=np.array(MODEL_VERSION),
        canonical_landmarks=np.asarray(canonical_landmarks, dtype=np.float64),
        head_dimensions=head_dims_arr,
        control_indices=np.asarray(control_indices, dtype=np.int64),
        landmark_stddev=np.asarray(landmark_stddev, dtype=np.float64),
    )


def load_face_model(path: str | Path) -> dict:
    """Load and validate a .facemodel.npz file. Raises ValueError on issues."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")

    data = np.load(path, allow_pickle=False)

    # Check all required keys present
    missing = set(_SCHEMA.keys()) - set(data.files)
    if missing:
        raise ValueError(f"Model file missing fields: {sorted(missing)}")

    # Check version
    version = str(data["version"])
    if version != MODEL_VERSION:
        raise ValueError(
            f"Unsupported model version '{version}' (expected '{MODEL_VERSION}')"
        )

    # Validate shapes and dtype kinds
    for key, (expected_kind, expected_shape) in _SCHEMA.items():
        arr = data[key]
        if arr.dtype.kind != expected_kind:
            raise ValueError(
                f"Field '{key}': expected dtype kind '{expected_kind}', "
                f"got '{arr.dtype.kind}'"
            )
        if expected_shape is not None and arr.shape != expected_shape:
            raise ValueError(
                f"Field '{key}': expected shape {expected_shape}, "
                f"got {arr.shape}"
            )

    # Reconstruct model dict
    return {
        "version": version,
        "canonical_landmarks": data["canonical_landmarks"],
        "head_dimensions": {
            "width": float(data["head_dimensions"][0]),
            "height": float(data["head_dimensions"][1]),
            "depth": float(data["head_dimensions"][2]),
        },
        "control_indices": data["control_indices"],
        "landmark_stddev": data["landmark_stddev"],
    }
```

### Pattern 2: Dict-to-Head-Dimensions Array Conversion
**What:** Convert the head_dimensions dict (width/height/depth) to a flat `(3,)` float64 array for NPZ storage, reconstruct on load.
**Why:** NPZ cannot store Python dicts natively. A fixed-order array is the cleanest approach -- no pickle needed, dtype preserved exactly.

### Anti-Patterns to Avoid
- **Using `allow_pickle=True` in `np.load`:** Security risk. All data MUST be storable as plain numpy arrays. The head_dimensions dict must be converted to an array.
- **Storing version as Python string via pickle:** Use `np.array("1")` which creates a 0-d unicode array, no pickle needed.
- **Not validating on load:** Silent failures when fields are missing or shapes wrong. Always validate completely before returning.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Compressed binary array storage | Custom serialization | `np.savez_compressed` | Handles dtype, shape, endianness, compression automatically |
| Array equality checking (tests) | Manual element comparison | `np.testing.assert_array_equal` | Handles NaN, dtype, shape comparison with clear error messages |
| Temporary file handling (tests) | Manual cleanup | `pytest.tmp_path` fixture | Automatic cleanup, unique paths per test |

## Common Pitfalls

### Pitfall 1: allow_pickle=True Default
**What goes wrong:** Older NumPy versions defaulted `allow_pickle=True` in `np.load`. If any array was saved with object dtype, loading with `allow_pickle=False` (the safe default since NumPy 1.16.3) raises an error.
**Why it happens:** Storing Python dicts or mixed-type data directly in NPZ triggers object arrays.
**How to avoid:** Convert ALL data to concrete numpy dtypes before saving. Use `allow_pickle=False` explicitly in `np.load`.
**Warning signs:** `ValueError: Object arrays cannot be loaded when allow_pickle=False`.

### Pitfall 2: String Arrays in NPZ
**What goes wrong:** `np.array("1")` creates a 0-d array with dtype `<U1`. On load, `str(data["version"])` returns `"1"` correctly. But if stored as `np.array(1)` (integer), comparison with string `"1"` fails silently.
**How to avoid:** Always store version as `np.array(MODEL_VERSION)` where MODEL_VERSION is a string. On load, cast with `str()` before comparing.

### Pitfall 3: Float Precision Assumptions
**What goes wrong:** Mixing float32 and float64 between save and load causes round-trip fidelity failures.
**How to avoid:** Explicitly cast to `np.float64` on save. Verify dtype in validation. The requirement says "identical data (dtype, shape, values)" -- this means exact bit-level match.

### Pitfall 4: Missing .npz Extension
**What goes wrong:** `np.savez_compressed` appends `.npz` if not present. If path is `model.facemodel`, the actual file becomes `model.facemodel.npz`.
**How to avoid:** The custom extension is `.facemodel.npz` -- this already ends in `.npz`, so NumPy won't double-append. Document this clearly.

### Pitfall 5: File Not Closed After np.load
**What goes wrong:** `np.load` returns a `NpzFile` that holds an open file handle. Not closing it leaks resources (matters on Windows).
**How to avoid:** Use `with np.load(...) as data:` context manager, or extract all arrays before the NpzFile goes out of scope. In the load function, extract everything into a plain dict before returning.

## Code Examples

### Round-Trip Test Pattern
```python
def test_round_trip(tmp_path):
    """Save and load must produce identical data."""
    path = tmp_path / "test.facemodel.npz"

    original_landmarks = np.random.rand(478, 2).astype(np.float64)
    original_head_dims = {"width": 1.85, "height": 2.4, "depth": 1.1}
    original_indices = np.array([10, 21, 54, 67, 93], dtype=np.int64)
    original_stddev = np.random.rand(478, 2).astype(np.float64)

    save_face_model(
        path,
        canonical_landmarks=original_landmarks,
        head_dimensions=original_head_dims,
        control_indices=original_indices,
        landmark_stddev=original_stddev,
    )

    loaded = load_face_model(path)

    np.testing.assert_array_equal(loaded["canonical_landmarks"], original_landmarks)
    np.testing.assert_array_equal(loaded["control_indices"], original_indices)
    np.testing.assert_array_equal(loaded["landmark_stddev"], original_stddev)
    assert loaded["head_dimensions"] == original_head_dims
    assert loaded["version"] == MODEL_VERSION
```

### Validation Error Test Pattern
```python
def test_missing_field_raises(tmp_path):
    """Loading a file with missing fields raises ValueError."""
    path = tmp_path / "bad.facemodel.npz"
    # Save incomplete data
    np.savez_compressed(path, version=np.array("1"))

    with pytest.raises(ValueError, match="missing fields"):
        load_face_model(path)


def test_wrong_version_raises(tmp_path):
    """Loading a file with wrong version raises ValueError."""
    path = tmp_path / "old.facemodel.npz"
    np.savez_compressed(
        path,
        version=np.array("99"),
        canonical_landmarks=np.zeros((478, 2)),
        head_dimensions=np.zeros(3),
        control_indices=np.zeros(5, dtype=np.int64),
        landmark_stddev=np.zeros((478, 2)),
    )

    with pytest.raises(ValueError, match="Unsupported model version"):
        load_face_model(path)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `np.load(allow_pickle=True)` default | `allow_pickle=False` default | NumPy 1.16.3 (2019) | Must ensure no object arrays |
| `np.savez` (uncompressed) | `np.savez_compressed` | Available since early NumPy | ~50-70% smaller files for float data |

## Open Questions

1. **Control point indices source**
   - What we know: `MORPH_CONTROL_INDICES` in `morph_utils.py` has 42 indices. Phase 7 (FaceModelBuilder) will use these.
   - What's unclear: Should the model store the current `MORPH_CONTROL_INDICES` or allow the builder to specify different indices?
   - Recommendation: Store whatever indices the builder computed with. The save/load layer should be agnostic to the specific indices -- just persist and validate as a 1-d int array.

2. **Stddev source**
   - What we know: Phase 6 needs to persist per-landmark stddev (478x2). This comes from averaging multiple images in Phase 7.
   - What's unclear: Phase 6 (persistence) is before Phase 7 (builder). We need to define the storage format without the producer existing yet.
   - Recommendation: Define the schema now with the shapes from the requirements. Phase 7 will produce data matching this schema. Tests can use synthetic data.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none (uses default discovery) |
| Quick run command | `conda run -n comfyui pytest tests/test_model_io.py -x -v` |
| Full suite command | `conda run -n comfyui pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODL-03a | .facemodel.npz stores canonical landmarks (478x2), head dims, control indices, stddev, version | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_save_creates_file -x` | No -- Wave 0 |
| MODL-03b | Round-trip produces identical data (dtype, shape, values) | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_round_trip -x` | No -- Wave 0 |
| MODL-03c | Missing fields raises clear ValueError | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_missing_field_raises -x` | No -- Wave 0 |
| MODL-03d | Wrong version raises clear ValueError | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_wrong_version_raises -x` | No -- Wave 0 |
| MODL-03e | Wrong shape raises clear ValueError | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_wrong_shape_raises -x` | No -- Wave 0 |
| MODL-03f | File size is approximately 6KB | unit | `conda run -n comfyui pytest tests/test_model_io.py::test_file_size -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `conda run -n comfyui pytest tests/test_model_io.py -x -v`
- **Per wave merge:** `conda run -n comfyui pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_model_io.py` -- covers MODL-03 (all sub-requirements)
- [ ] `utils/model_io.py` -- the module under test

## Sources

### Primary (HIGH confidence)
- [numpy.savez_compressed docs (v2.4)](https://numpy.org/doc/stable/reference/generated/numpy.savez_compressed.html) - API, behavior, extension handling
- [numpy.load docs](https://numpy.org/doc/stable/reference/generated/numpy.load.html) - allow_pickle default, NpzFile behavior
- Project codebase: `utils/pose_utils.py`, `utils/morph_utils.py` - existing data structures and patterns

### Secondary (MEDIUM confidence)
- [NumPy NPZ guide (nkmk)](https://note.nkmk.me/en/python-numpy-load-save-savez-npy-npz/) - practical usage patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - NumPy NPZ is the obvious choice, no new dependencies
- Architecture: HIGH - Simple save/load module, patterns well-established in codebase
- Pitfalls: HIGH - Well-known NumPy gotchas, verified against official docs

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable domain, NumPy NPZ format is frozen)
