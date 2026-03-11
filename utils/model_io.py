"""Face model NPZ persistence: save and load .facemodel.npz files.

Schema (MODEL_VERSION = "2"):
    version:              0-d unicode string
    canonical_landmarks:  float64 (478, 2)
    head_dimensions:      float64 (3,)  -- [width, height, depth]
    control_indices:      int64   (N,)  -- variable length
    landmark_stddev:      float64 (478, 3)  -- 3D per-landmark standard deviations
"""

from pathlib import Path

import numpy as np

MODEL_VERSION = "2"

# Expected keys: (dtype_kind, expected_shape or None for variable)
_SCHEMA = {
    "version": ("U", ()),
    "canonical_landmarks": ("f", (478, 2)),
    "head_dimensions": ("f", (3,)),
    "control_indices": ("i", None),  # 1-d, variable length
    "landmark_stddev": ("f", (478, 3)),
}


def save_face_model(
    path: str | Path,
    *,
    canonical_landmarks,
    head_dimensions: dict,
    control_indices,
    landmark_stddev,
) -> None:
    """Save a face model to a .facemodel.npz file.

    Args:
        path: Destination file path (should end with .facemodel.npz).
        canonical_landmarks: (478, 2) array of normalized landmark positions.
        head_dimensions: Dict with 'width', 'height', 'depth' float keys.
        control_indices: 1-d array of control point landmark indices.
        landmark_stddev: (478, 3) array of per-landmark 3D standard deviations.
    """
    path = Path(path)

    head_dims_arr = np.array(
        [head_dimensions["width"], head_dimensions["height"], head_dimensions["depth"]],
        dtype=np.float64,
    )

    np.savez_compressed(
        path,
        version=np.array(MODEL_VERSION),
        canonical_landmarks=np.asarray(canonical_landmarks, dtype=np.float64),
        head_dimensions=head_dims_arr,
        control_indices=np.asarray(control_indices, dtype=np.int64),
        landmark_stddev=np.asarray(landmark_stddev, dtype=np.float64),
    )


def load_face_model(path: str | Path) -> dict:
    """Load and validate a .facemodel.npz file.

    Returns:
        Dict with keys: version, canonical_landmarks, head_dimensions,
        control_indices, landmark_stddev.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If file has missing fields, wrong version, or wrong shapes.
    """
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

    # Validate dtype kinds and shapes
    for key, (expected_kind, expected_shape) in _SCHEMA.items():
        arr = data[key]
        if arr.dtype.kind != expected_kind:
            raise ValueError(
                f"Field '{key}': expected dtype kind '{expected_kind}', "
                f"got '{arr.dtype.kind}'"
            )
        if expected_shape is not None and arr.shape != expected_shape:
            raise ValueError(
                f"Field '{key}': expected shape {expected_shape}, got {arr.shape}"
            )

    # Extract all arrays into plain dict (closes NpzFile handle)
    result = {
        "version": version,
        "canonical_landmarks": np.array(data["canonical_landmarks"]),
        "head_dimensions": {
            "width": float(data["head_dimensions"][0]),
            "height": float(data["head_dimensions"][1]),
            "depth": float(data["head_dimensions"][2]),
        },
        "control_indices": np.array(data["control_indices"]),
        "landmark_stddev": np.array(data["landmark_stddev"]),
    }

    data.close()
    return result
