# Phase 7: FaceModelBuilder Node - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

User-facing ComfyUI node that reads a directory of target images, runs face detection + pose extraction on each, rejects extreme-pose images, weighted-averages remaining landmarks into a canonical face model, and outputs: FACE_MODEL, quality report string, and landmark preview image. Model is saved to disk as .facemodel.npz.

</domain>

<decisions>
## Implementation Decisions

### Directory Input & Image Handling
- STRING input for directory path (connects to existing PathSplitter node)
- Flat directory scan only — no recursive subdirectory traversal
- Accept common formats: jpg, jpeg, png, webp, bmp (filter by extension, skip non-matching silently)
- Minimum 1 valid image, no maximum — single valid image becomes the model directly

### Averaging Pipeline
- Average 3D frontalized landmarks (478x3) with cos(yaw)*cos(pitch) weighting, then project to 2D (drop Z) for canonical_landmarks
- Per-landmark stddev computed in 3D space (requires model_io schema update from (478,2) to (478,3) — Phase 6 has no downstream consumers yet)
- Head dimensions computed per-image (weighted average), not from final averaged landmarks
- Images with no face detected are logged in quality report but obviously don't contribute to averaging

### Quality Report Format
- Plain text table with aligned columns: File | Status | Yaw | Pitch | Roll | Confidence | Weight
- Sorted by status then filename: ACCEPTED first (by weight descending), then REJECTED (by yaw), then NO FACE
- Summary line at end: total images / accepted / rejected / no face, with yaw/pitch thresholds shown
- Last line: model save path ("Model saved to: /path/to/model.facemodel.npz")

### Landmark Preview Image
- 512x512 black background canvas
- Show 42 MORPH_CONTROL_INDICES as green dots, connected by white face oval contour lines
- Landmarks plotted in normalized space, scaled to fit canvas
- Minimal text header at top: "FaceModel (N images)"
- No stddev visualization — keep it clean

### Claude's Discretion
- Exact dot size and line thickness for preview
- Font choice for header text (PIL default is fine)
- How to scale/center normalized landmarks onto 512x512 canvas
- Internal function decomposition within the builder module
- Whether to save model before or after generating preview

</decisions>

<specifics>
## Specific Ideas

- Rejection thresholds carried from Phase 5: yaw ±45°, pitch ±30°
- cos(yaw)*cos(pitch) weighting from Phase 5 requirements
- Rejection messages include actual angles: "image_03.jpg: REJECTED (yaw=52°, threshold=45°)" (Phase 5 decision)
- Missing transformation matrix: fall back to 2D landmarks, assume frontal pose, image still contributes (Phase 5 decision)
- Green dots + white contour matches MediaPipe's green landmark convention

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `utils/pose_utils.py`: `extract_pose_angles()`, `frontalize_landmarks()`, `normalize_landmarks_3d()`, `compute_head_dimensions()` — core pipeline functions
- `utils/model_io.py`: `save_face_model()`, `load_face_model()` — NPZ persistence (schema needs stddev update to 3D)
- `utils/morph_utils.py`: `MORPH_CONTROL_INDICES` (42 points), `FACE_OVAL_INDICES` — for preview rendering
- `utils/mediapipe_helper.py`: `get_landmarker()`, `comfyui_to_mediapipe()` — face detection pipeline
- `utils/landmarks.py`: `extract_landmarks()` — returns face dicts with landmarks_3d and pose data

### Established Patterns
- Face data as dict: `{"landmarks": (478,2), "landmarks_3d": (478,3), "pose": {...}}` — Phase 5 extended this
- Module per concern: face_detection.py, face_crop.py, face_morph.py — new face_model_builder.py follows this
- Node registration via `__init__.py` with try/except ImportError guard
- ComfyUI node pattern: `INPUT_TYPES()`, `RETURN_TYPES`, `FUNCTION`, `CATEGORY`

### Integration Points
- New `face_model_builder.py` module at package root (same level as face_detection.py)
- Register in `__init__.py` as "FaceModelBuilder" / "ImgTools Face Model Builder"
- FACE_MODEL output type — new custom type for the model dict
- Connects to FaceModelMorph (Phase 8) which consumes FACE_MODEL

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-face-model-builder*
*Context gathered: 2026-03-11*
