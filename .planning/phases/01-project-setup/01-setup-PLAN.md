# PLAN: Phase 1 - Project Setup

## Objective
Establish ComfyUI custom node structure and verify integration works correctly.

## Execution Context
- Project: ComfyUI Image Tools (ImageDimensionFitter node)
- Phase: 1 of 4 (Project Setup)
- Dependencies: None (first phase)

## Context

### ComfyUI Custom Node Requirements
Based on analysis of existing nodes (comfyui-previewlatent, comfyui_essentials):

1. **`__init__.py`** must export:
   - `NODE_CLASS_MAPPINGS`: dict mapping internal names to classes
   - `NODE_DISPLAY_NAME_MAPPINGS`: dict mapping internal names to display names

2. **Node class structure** requires:
   - `INPUT_TYPES(cls)`: classmethod returning input specifications
   - `RETURN_TYPES`: tuple of output types (e.g., `("IMAGE",)`)
   - `RETURN_NAMES`: tuple of output names (e.g., `("image",)`)
   - `FUNCTION`: string name of the method to execute
   - `CATEGORY`: string for node menu category
   - The actual processing method matching FUNCTION name

### Project Structure Target
```
comfyui_imgtools/
├── __init__.py           # Node registration
└── nodes.py              # ImageDimensionFitter class
```

## Tasks

### Task 1: Create node file with placeholder class
**File:** `nodes.py`

Create the ImageDimensionFitter node class with:
- IMAGE input type
- Dropdown for model selection (SD, Flux, Z-Turbo) - placeholder values for now
- IMAGE return type
- Placeholder processing function that passes through input unchanged

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

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "fit_dimensions"
    CATEGORY = "image/transform"

    def fit_dimensions(self, image, model):
        # Placeholder - just return input for now
        return (image,)
```

### Task 2: Create __init__.py with node registration
**File:** `__init__.py`

Register the node with ComfyUI:
```python
from .nodes import ImageDimensionFitter

NODE_CLASS_MAPPINGS = {
    "ImageDimensionFitter": ImageDimensionFitter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageDimensionFitter": "Image Dimension Fitter",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
```

### Task 3: Verify node loads in ComfyUI
**Action:** Manual verification by user

Steps:
1. Restart ComfyUI (or use Manager to reload custom nodes)
2. Search for "Image Dimension Fitter" in node browser
3. Verify node appears and can be added to canvas
4. Verify dropdown shows SD, Flux, Z-Turbo options
5. Connect an image and confirm no errors on execution

## Verification

- [ ] `nodes.py` exists with ImageDimensionFitter class
- [ ] `__init__.py` exports NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS
- [ ] No Python syntax errors (can import the module)
- [ ] Node appears in ComfyUI interface
- [ ] Node accepts image input without errors

## Success Criteria

1. Node appears in ComfyUI under "image/transform" category
2. Model dropdown displays all three options
3. Node can be connected to an image source without errors
4. When executed, the image passes through unchanged (placeholder behavior)

## Output

After completing this phase:
- Basic node skeleton ready for dimension logic implementation
- ComfyUI integration verified working
- Ready to proceed to Phase 2 (Core Node Implementation)

## Notes

- Keep the node minimal - only what's needed for Phase 1
- Don't add dimension tables or crop logic yet
- Focus on verifying the structure works with ComfyUI
