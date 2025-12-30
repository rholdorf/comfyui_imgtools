---
phase: 04-testing-polish
type: execute
---

<objective>
Validate ImageDimensionFitter node works correctly in real ComfyUI workflows.

Purpose: Verify the node functions as expected with SD, Flux, and Z-Turbo workflows before release.
Output: Confirmed working node with any edge-case fixes applied.
</objective>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03-crop-logic/SUMMARY.md
@nodes.py
@__init__.py
</context>

<tasks>
<task type="auto">
  <name>Task 1: Verify Python module loads without errors</name>
  <files>nodes.py, __init__.py</files>
  <action>Run Python import check to verify the module loads correctly. Test: `python -c "from nodes import ImageDimensionFitter; print('OK')"` from the project directory.</action>
  <verify>Command exits 0 and prints "OK"</verify>
  <done>Module imports without errors</done>
</task>

<task type="auto">
  <name>Task 2: Unit test dimension matching for all models</name>
  <files>nodes.py</files>
  <action>
Run inline Python tests to verify find_closest_dimensions returns correct values:
- SD 1:1 image (512x512) -> 512x512
- SD 3:2 image (600x400) -> 768x512 (closest landscape)
- Flux 1:1 image (1000x1000) -> 1024x1024
- Flux 16:9 image (1920x1080) -> 1920x1080 (exact match)
- Z-Turbo portrait (800x1200) -> 832x1216 (closest portrait)

Execute via: python -c "from nodes import find_closest_dimensions; ..."
  </action>
  <verify>All assertions pass, no output (Python assert behavior)</verify>
  <done>Dimension matching returns expected values for representative inputs across all three models</done>
</task>

<task type="auto">
  <name>Task 3: Unit test center_crop edge cases</name>
  <files>nodes.py</files>
  <action>
Create test tensor and verify center_crop behavior:
1. Normal crop: 800x600 image cropped to 640x480 -> returns 640x480
2. Undersized image: 400x300 to 640x480 -> returns 400x300 unchanged
3. Exact size: 512x512 to 512x512 -> returns 512x512 unchanged
4. Batch handling: batch of 3 images processes all correctly

Use torch or numpy to create test tensors matching ComfyUI format [B, H, W, C].
  </action>
  <verify>Python test script exits 0</verify>
  <done>center_crop handles normal, undersized, exact, and batch cases correctly</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Verified module loads and unit tests pass</what-built>
  <how-to-verify>
    1. Start/restart ComfyUI: `cd /path/to/ComfyUI && python main.py`
    2. Open browser to http://localhost:8188
    3. Search for "Image Dimension Fitter" in node menu (right-click -> Add Node -> search)
    4. Confirm node appears under "image/transform" category
    5. Verify node has: IMAGE input, model dropdown (SD/Flux/Z-Turbo), IMAGE + 2x INT outputs
  </how-to-verify>
  <resume-signal>Type "node visible" if found, or describe the issue</resume-signal>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Node implementation ready for workflow testing</what-built>
  <how-to-verify>
    **Test 1: SD Workflow**
    1. Load any image (e.g., 1920x1080)
    2. Connect: Load Image -> Image Dimension Fitter (model=SD) -> Preview Image
    3. Queue prompt
    4. Verify: Output image is one of SD dimensions (likely 768x512 for 16:9 input)
    5. Verify: target_width/target_height outputs match cropped image size

    **Test 2: Flux Workflow**
    1. Same image -> Image Dimension Fitter (model=Flux) -> Preview Image
    2. Verify: Output is a Flux dimension (likely 1920x1080 if exact, or 1536x640)

    **Test 3: Connect to KSampler**
    1. Build minimal workflow: Image Dimension Fitter -> VAE Encode -> KSampler -> VAE Decode -> Preview
    2. Use appropriate checkpoint for model type
    3. Queue prompt
    4. Verify: No artifacts, proper generation at target dimensions
  </how-to-verify>
  <resume-signal>Type "workflows pass" or describe issues encountered</resume-signal>
</task>

<task type="auto">
  <name>Task 6: Add error handling if issues found</name>
  <files>nodes.py</files>
  <action>
If previous verification revealed issues:
- Add any missing input validation
- Handle unexpected tensor shapes gracefully
- Add informative error messages

If no issues found, this task is a no-op.
  </action>
  <verify>Re-run unit tests if changes made</verify>
  <done>Any discovered issues are fixed, or task skipped if none found</done>
</task>
</tasks>

<verification>
Before declaring phase complete:
- [ ] Python module imports without errors
- [ ] Unit tests for dimension matching pass
- [ ] Unit tests for center_crop pass
- [ ] Node appears in ComfyUI UI
- [ ] SD workflow tested successfully
- [ ] Flux workflow tested successfully
- [ ] KSampler integration produces no artifacts
</verification>

<success_criteria>
- Node loads in ComfyUI without errors
- All three models (SD, Flux, Z-Turbo) produce correct target dimensions
- Center crop produces correctly sized output images
- Real workflows with KSampler generate images without dimension-related artifacts
- No unhandled exceptions during normal usage
</success_criteria>

<output>
After completion, create `.planning/phases/04-testing-polish/SUMMARY.md`:

# Phase 4 Summary: Testing & Polish

## Test Results
[Pass/fail status for each verification item]

## Issues Found & Fixed
[Any bugs discovered and their fixes, or "None"]

## Files Modified
[List of files changed during this phase]

## Release Readiness
[Confirmation that v1.0 is ready, or list remaining blockers]
</output>
