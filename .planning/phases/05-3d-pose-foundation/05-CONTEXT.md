# Phase 5: 3D Pose Foundation - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract head pose from MediaPipe's transformation matrix, frontalize landmarks to canonical frontal pose, and IPD-normalize for cross-image comparability. Pure infrastructure — no user-facing nodes change (except extending the face dict). Existing v1.0 pipeline must remain fully functional.

</domain>

<decisions>
## Implementation Decisions

### Pose Data Exposure
- Extend existing face dict with `pose` key containing pitch/yaw/roll angles AND raw 4x4 transformation matrix
- Non-breaking addition — existing workflows ignore the new key
- Show pose angles per image in FaceModelBuilder quality report (Phase 7): both accepted and rejected images
- Defer pose axis visualization on preview image to Phase 9

### Frontalization Thresholds
- Yaw rejection threshold: ±45° (accepts 3/4 views, rejects near-profile)
- Pitch rejection threshold: ±30° (stricter than yaw — extreme pitch is rarer and distorts chin/forehead more)
- Frontalization accuracy target: ~2-3% IPD mean landmark error (tight enough for quality morphs, accounts for MediaPipe noise)
- cos(yaw)*cos(pitch) weighting for model averaging (already in requirements)

### Frontalization Output
- Keep frontalized landmarks in 3D coordinates, project to 2D on demand (not eagerly)
- Store both 3D frontalized landmarks AND pre-computed 2D projection in the canonical model file for convenience

### Failure Handling
- Missing transformation matrix: fall back to 2D landmarks (assume frontal pose), log warning, image still contributes to model
- All images rejected (beyond threshold): clear error with guidance — "All N images rejected (yaw/pitch beyond threshold). Provide images with more frontal poses." Show best candidate's angles
- Rejection messages include actual angles: "image_03.jpg: REJECTED (yaw=52°, threshold=45°)"
- Input validation at external boundary only (data from MediaPipe), internal functions trust each other — matches v1.0 pattern

### IPD Normalization
- New `utils/pose_utils.py` module — keeps v1.0 morph_utils.py untouched
- IPD measured in 3D Euclidean space (true physical distance, pose-invariant)
- Head dimensions estimation (bounding box from landmarks) included in pose_utils.py — pose-dependent, logically cohesive

### Claude's Discretion
- SciPy Rotation API usage for matrix decomposition
- Exact frontalization algorithm (de-rotation math)
- Internal function signatures and helper organization within pose_utils.py
- Test fixture design for frontalization accuracy validation

</decisions>

<specifics>
## Specific Ideas

- Rejection report should be human-readable: "image_03.jpg: REJECTED (yaw=52°, threshold=45°)" — user needs to understand why and provide better images
- 3D Euclidean IPD is more accurate than 2D projected IPD for cross-pose comparison
- Head dimensions belong with pose code since perspective changes the bounding box

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `utils/mediapipe_helper.py`: FaceLandmarker setup with `output_face_blendshapes=False`, `output_facial_transformation_matrixes` currently not enabled — needs enabling for Phase 5
- `utils/landmarks.py`: `extract_landmarks()` returns `landmarks_3d` (478x3) — foundation for 3D frontalization
- `utils/morph_utils.py`: `normalize_landmarks()` (2D IPD) and `procrustes_align()` — NOT modified, new 3D versions go in pose_utils.py

### Established Patterns
- Face data as dict: `{"landmarks": (478,2), "landmarks_3d": (478,3)}` — extend with `"pose"` key
- Module per concern: mediapipe_helper, landmarks, morph_utils, alignment, face_mask — new pose_utils follows this pattern
- Cached singleton pattern for landmarker in mediapipe_helper.py
- No OpenCV — SciPy Rotation for 3D math instead of cv2.solvePnP

### Integration Points
- `mediapipe_helper.py`: Enable `output_facial_transformation_matrixes=True` in FaceLandmarkerOptions
- `landmarks.py`: `extract_landmarks()` needs to extract transformation matrix from MediaPipe result
- Face dict: downstream Phase 6-8 code reads the new pose/matrix fields
- Existing 123 tests must pass unchanged (v1.0 regression)

</code_context>

<deferred>
## Deferred Ideas

- Pose axis visualization on FaceDetect preview — Phase 9
- Expression normalization via blendshapes — v1.2 (MENH-02)

</deferred>

---

*Phase: 05-3d-pose-foundation*
*Context gathered: 2026-03-11*
