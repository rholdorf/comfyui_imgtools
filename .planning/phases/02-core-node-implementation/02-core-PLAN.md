# PLAN: Phase 2 - Core Node Implementation

## Objective
Implement the ImageDimensionFitter node with model-specific dimension tables and matching algorithm to find the closest standard resolution for any input image.

## Execution Context
- Project: ComfyUI Image Tools (ImageDimensionFitter node)
- Phase: 2 of 4 (Core Node Implementation)
- Dependencies: Phase 1 completed (skeleton node exists)
- File to modify: `nodes.py`

## Context

### Current State
The `nodes.py` file contains a placeholder `ImageDimensionFitter` class that:
- Accepts IMAGE input and model selection dropdown (SD, Flux, Z-Turbo)
- Returns IMAGE unchanged (placeholder behavior)

### Model Dimension Tables (Research Results)

**Stable Diffusion 1.5 (SD)**
- Native: 512x512
- Must stay near ~262k pixels (512x512)
- Dimensions divisible by 8

Standard resolutions:
- 512x512 (1:1)
- 512x768 / 768x512 (2:3 / 3:2)
- 512x704 / 704x512 (~1.37:1)
- 640x512 / 512x640 (5:4 / 4:5)
- 768x512 / 512x768 (3:2 / 2:3)

**Flux**
- Native: 1024x1024 (works up to ~2MP)
- Dimensions divisible by 32
- Best quality near 1MP (~1024x1024)

Standard resolutions:
- 1024x1024 (1:1)
- 1152x896 / 896x1152 (9:7 / 7:9)
- 1216x832 / 832x1216 (19:13 / 13:19)
- 1344x768 / 768x1344 (7:4 / 4:7)
- 1536x640 / 640x1536 (12:5 / 5:12)
- 1920x1080 / 1080x1920 (16:9 / 9:16)

**Z-Image Turbo (Z-Turbo)**
- Native: 1024x1024
- Dimensions divisible by 32
- Keep total pixels near 1MP for best quality

Standard resolutions (same as Flux, since both are ~1MP models):
- 1024x1024 (1:1)
- 1152x896 / 896x1152 (9:7 / 7:9)
- 1216x832 / 832x1216 (19:13 / 13:19)
- 1344x768 / 768x1344 (7:4 / 4:7)
- 1536x640 / 640x1536 (12:5 / 5:12)
- 1920x512 / 512x1920 (ultra-wide/tall for Z-Turbo)

### Dimension Matching Algorithm

The algorithm should:
1. Calculate input image aspect ratio (width/height)
2. For each standard resolution in the model's table, calculate its aspect ratio
3. Find the resolution whose aspect ratio is closest to the input's aspect ratio
4. Return the target (width, height) for cropping

Note: This phase only finds the target dimensions. Actual cropping happens in Phase 3.

## Tasks

### Task 1: Define dimension tables as module constants
**File:** `nodes.py`

Add dimension tables at module level (before the class):

```python
# Dimension tables: list of (width, height) tuples
# SD 1.5: ~262k pixels, divisible by 8
SD_DIMENSIONS = [
    (512, 512),   # 1:1
    (640, 512),   # 5:4
    (512, 640),   # 4:5
    (704, 512),   # ~1.37:1
    (512, 704),   # ~1:1.37
    (768, 512),   # 3:2
    (512, 768),   # 2:3
]

# Flux: ~1MP, divisible by 32
FLUX_DIMENSIONS = [
    (1024, 1024),  # 1:1
    (1152, 896),   # 9:7
    (896, 1152),   # 7:9
    (1216, 832),   # 19:13
    (832, 1216),   # 13:19
    (1344, 768),   # 7:4
    (768, 1344),   # 4:7
    (1536, 640),   # 12:5
    (640, 1536),   # 5:12
    (1920, 1080),  # 16:9
    (1080, 1920),  # 9:16
]

# Z-Turbo: ~1MP, divisible by 32 (similar to Flux)
ZTURBO_DIMENSIONS = [
    (1024, 1024),  # 1:1
    (1152, 896),   # 9:7
    (896, 1152),   # 7:9
    (1216, 832),   # 19:13
    (832, 1216),   # 13:19
    (1344, 768),   # 7:4
    (768, 1344),   # 4:7
    (1536, 640),   # 12:5
    (640, 1536),   # 5:12
]

MODEL_DIMENSIONS = {
    "SD": SD_DIMENSIONS,
    "Flux": FLUX_DIMENSIONS,
    "Z-Turbo": ZTURBO_DIMENSIONS,
}
```

### Task 2: Implement dimension matching function
**File:** `nodes.py`

Add a helper function to find the closest matching dimensions:

```python
def find_closest_dimensions(width: int, height: int, model: str) -> tuple[int, int]:
    """Find the closest standard dimensions for the given model based on aspect ratio."""
    dimensions = MODEL_DIMENSIONS[model]
    input_ratio = width / height

    best_match = dimensions[0]
    best_diff = abs(input_ratio - (best_match[0] / best_match[1]))

    for w, h in dimensions[1:]:
        target_ratio = w / h
        diff = abs(input_ratio - target_ratio)
        if diff < best_diff:
            best_diff = diff
            best_match = (w, h)

    return best_match
```

### Task 3: Update node to output target dimensions
**File:** `nodes.py`

Modify the `ImageDimensionFitter` class to:
1. Add WIDTH and HEIGHT integer outputs
2. Calculate and return target dimensions
3. Still pass through image unchanged (cropping is Phase 3)

```python
class ImageDimensionFitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "model": (["SD", "Flux", "Z-Turbo"],),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("image", "target_width", "target_height")
    FUNCTION = "fit_dimensions"
    CATEGORY = "image/transform"

    def fit_dimensions(self, image, model):
        # image tensor shape: [batch, height, width, channels]
        _, h, w, _ = image.shape
        target_w, target_h = find_closest_dimensions(w, h, model)

        # For now, just return input image and target dimensions
        # Actual cropping will be implemented in Phase 3
        return (image, target_w, target_h)
```

### Task 4: Verify implementation
**Action:** Run Python import test

```bash
cd /Volumes/rui/src/pg/ComfyUI/custom_nodes/comfyui_imgtools
python -c "from nodes import ImageDimensionFitter, find_closest_dimensions, MODEL_DIMENSIONS; print('Import OK'); print(find_closest_dimensions(1920, 1080, 'Flux'))"
```

Expected output: `(1920, 1080)` since 16:9 is in the Flux table.

Test edge case:
```bash
python -c "from nodes import find_closest_dimensions; print(find_closest_dimensions(800, 600, 'SD'))"
```

Expected: `(768, 512)` or `(704, 512)` - closest to 4:3 ratio.

## Verification

- [ ] `nodes.py` contains SD_DIMENSIONS, FLUX_DIMENSIONS, ZTURBO_DIMENSIONS constants
- [ ] `nodes.py` contains MODEL_DIMENSIONS dict mapping model names to dimension lists
- [ ] `find_closest_dimensions()` function exists and returns correct dimensions
- [ ] ImageDimensionFitter returns ("IMAGE", "INT", "INT") types
- [ ] No Python syntax errors (module imports successfully)
- [ ] Dimension matching works for various aspect ratios

## Success Criteria

1. Module imports without errors
2. `find_closest_dimensions(1920, 1080, "Flux")` returns `(1920, 1080)`
3. `find_closest_dimensions(1920, 1080, "SD")` returns `(768, 512)` (closest 3:2 in SD table)
4. `find_closest_dimensions(1000, 1000, "Z-Turbo")` returns `(1024, 1024)` (closest 1:1)
5. Node outputs target_width and target_height as INT values

## Output

After completing this phase:
- Dimension tables defined for all three models
- Aspect ratio matching algorithm implemented
- Node outputs target dimensions (ready for Phase 3 cropping)
- Image still passes through unchanged (cropping is next phase)

## Notes

- Keep dimension tables simple and focused on common aspect ratios
- The matching algorithm prioritizes aspect ratio similarity over pixel count
- Phase 3 will implement the actual crop to these target dimensions
- No external dependencies needed - pure Python implementation
