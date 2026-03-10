# Phase 1: Environment and Detection - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Verify MediaPipe Face Landmarker works on macOS Apple Silicon in the ComfyUI Python environment, and implement a face landmark detection node that returns structured landmark data for all detected faces. Cropping, alignment, and face index selection are Phase 2.

</domain>

<decisions>
## Implementation Decisions

### MediaPipe model choice
- Use the **Full** Face Landmarker model (~6MB) — good accuracy/speed balance for face morphing
- **Auto-download** the .task model file on first use from Google's CDN; store in a models/ subfolder within the extension
- Detect **all faces** in the image (not just the largest); face index selection is added in Phase 2
- If MediaPipe cannot be installed (Python version incompatible): **fail with a clear error message** stating supported Python versions — no fallback detector

### Detection node outputs
- **Custom FACE_LANDMARKS type** for landmark data — list of per-face landmark dicts, type-safe ComfyUI connections
- Output a **debug/preview IMAGE** with landmarks drawn on the input image (optional output for inspection)
- Output a **face count INT** so users can branch workflow logic on single vs multi-face images
- When **no face detected**: return empty FACE_LANDMARKS and count=0 — no error, no workflow interruption

### Node file organization
- **Separate files** for face nodes (not in nodes.py) — e.g., face_detection.py for this phase
- **utils/ subfolder** for shared utilities — e.g., utils/mediapipe_helper.py, utils/landmarks.py
- Node display names **prefixed with "ImgTools"** — e.g., "ImgTools Face Detect"

### Claude's Discretion
- ComfyUI CATEGORY namespace for face nodes (e.g., "face/detection" vs "image/face/detection")

### Dependency strategy
- Declare dependencies in **requirements.txt** (standard for ComfyUI custom nodes)
- Use **minimum version pins** (e.g., mediapipe>=0.10.14) — avoids conflicts with other extensions
- **Only add MediaPipe** in Phase 1; scikit-image added later in Phase 3 when TPS warping is needed
- **Import-time check with warning**: try importing MediaPipe when extension loads; print clear warning with install instructions if it fails, but don't crash ComfyUI

</decisions>

<specifics>
## Specific Ideas

- Model file goes in models/ subfolder within the extension directory
- Match ReActor's multi-face UX pattern (detect all, select by index)
- Keep existing utility nodes (ImageDimensionFitter, ImagePaddingCalculator, PathSplitter) untouched in nodes.py

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None directly reusable for face detection — existing nodes are image dimension/path utilities

### Established Patterns
- ComfyUI node pattern: class with INPUT_TYPES (classmethod), RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY
- Image tensors are [batch, height, width, channels] format
- All nodes currently in nodes.py, registered in __init__.py via NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS

### Integration Points
- __init__.py must be updated to import and register new face detection node(s)
- New node files must follow the same class-based pattern as nodes.py
- Custom FACE_LANDMARKS type needs to be compatible with ComfyUI's type system

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-environment-and-detection*
*Context gathered: 2026-03-10*
