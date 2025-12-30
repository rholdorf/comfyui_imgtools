# Phase 3: Crop Logic

## Context
ImageDimensionFitter node exists with dimension tables and matching algorithm.
Currently returns unchanged image with target dimensions.
Need to implement actual centered cropping.

## Tasks

### Task 1: Implement center_crop function
- Calculate offsets to center the crop region
- Extract crop region from tensor
- Handle ComfyUI tensor format [batch, H, W, C]

### Task 2: Handle edge cases
- If image is smaller than target, do not crop (return as-is)
- Log warning if dimensions mismatch significantly

### Task 3: Update fit_dimensions method
- Call center_crop with calculated target dimensions
- Ensure batch dimension is preserved

## Checkpoints
None - fully autonomous execution

## Expected Outcome
- Image is center-cropped to match closest standard dimensions
- Batch processing works correctly
- Edge cases handled gracefully
