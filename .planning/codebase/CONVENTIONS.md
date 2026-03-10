# Coding Conventions

**Analysis Date:** 2026-03-10

## Naming Patterns

**Files:**
- `nodes.py` - Main module containing class definitions and helper functions
- `__init__.py` - Package initialization with exports
- Uses snake_case for Python filenames (standard Python convention)

**Functions:**
- All functions use snake_case: `center_crop()`, `find_closest_dimensions()`, `calculate_padding()`, `split_path()`, `fit_dimensions()`
- Private/internal functions use same convention as public ones (no underscore prefix currently used)
- Helper functions at module level precede classes that use them

**Variables:**
- Type hints use snake_case: `target_w`, `target_h`, `pad_x`, `pad_y`
- Constant dimensions use UPPER_SNAKE_CASE: `SD_DIMENSIONS`, `FLUX_DIMENSIONS`, `ZTURBO_DIMENSIONS`, `MODEL_DIMENSIONS`
- Class instance methods use snake_case: `calculate_padding()`, `split_path()`, `fit_dimensions()`

**Classes:**
- Use PascalCase: `ImagePaddingCalculator`, `PathSplitter`, `ImageDimensionFitter`
- All node classes follow ComfyUI convention with uppercase class names
- Node class names describe the function clearly and end with noun

## Code Style

**Formatting:**
- 4-space indentation throughout
- Line length: 80-100 characters typical (not strict)
- Blank lines separate logical sections within functions
- Comments explain "why" rather than "what" where present

**Linting/Formatting:**
- No linting/formatting config file detected (`.pylintrc`, `pyproject.toml`, etc. not present)
- Code follows PEP 8 conventions implicitly
- Consistent import organization observed

## Import Organization

**Order:**
1. Standard library imports (e.g., `os`)
2. Local relative imports (e.g., `from .nodes import`)

**Pattern:**
- Lazy imports used: `import os` inside `split_path()` method (line 133) rather than at module level
- This reduces startup overhead for ComfyUI nodes

**Path Aliases:**
- Relative imports: `.nodes` module in `__init__.py`
- No path aliases configured

## Error Handling

**Patterns:**
- No explicit error handling currently implemented
- Functions assume valid input parameters
- `center_crop()` includes defensive check: returns image unchanged if dimensions are smaller than target (line 62-63)
- `find_closest_dimensions()` assumes `model` parameter is valid (no validation for KeyError)

**Defensive checks:**
- Dimension bounds checking in `calculate_padding()`: uses `max()` to ensure non-negative padding (lines 109-110)
- Array unpacking with safe index access: `_, h, w, _ = image.shape` assumes 4D tensor format

## Logging

**Framework:** None used

**Patterns:**
- No logging statements present
- Code uses pure computation without debug output
- Silent operation expected

## Comments

**When to Comment:**
- Module-level docstrings for dimension tables (lines 1-2, 13, 28)
- Inline comments explain complex calculations and tensor indexing

**JSDoc/TSDoc:**
- Docstrings use triple-quoted format for functions
- Example from `center_crop()` (lines 49-57):
  ```python
  def center_crop(image, target_w: int, target_h: int):
      """Center crop an image tensor to target dimensions.

      Args:
          image: Tensor of shape [batch, height, width, channels]
          target_w: Target width
          target_h: Target height

      Returns:
          Cropped tensor of shape [batch, target_h, target_w, channels]
      """
  ```
- Clear specification of tensor shape and dimensions
- No docstrings on node class methods (INPUT_TYPES, RETURN_TYPES)

## Function Design

**Size:**
- Small, focused functions: typically 5-20 lines
- `center_crop()`: 16 lines, single responsibility (crop images)
- `find_closest_dimensions()`: 14 lines, single responsibility (aspect ratio matching)

**Parameters:**
- Type hints used consistently: `target_w: int`, `target_h: int`, `model: str`
- Parameters are concise and positional
- Default values provided in INPUT_TYPES for UI exposure

**Return Values:**
- Functions return tuples for multiple values: `(w, h)`, `(left, top, right, bottom)`
- Node class methods return tuples matching RETURN_TYPES specification
- Return type specified in docstrings

## Module Design

**Exports:**
- `__init__.py` explicitly exports node mappings via `__all__` (line 15)
- Two dicts exported: `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`
- Classes imported directly: `from .nodes import ImageDimensionFitter, ImagePaddingCalculator, PathSplitter`

**Barrel Files:**
- `__init__.py` serves as entry point for ComfyUI plugin discovery
- Re-exports three node classes for the framework to register
- Clean separation: `nodes.py` contains implementation, `__init__.py` handles registration

## ComfyUI Node Convention

**Required structure:**
- All node classes implement `INPUT_TYPES()` classmethod returning dict of required/optional inputs
- `RETURN_TYPES` class variable: tuple of return type strings
- `RETURN_NAMES` class variable: tuple of human-readable output names
- `FUNCTION` class variable: method name to invoke (e.g., "calculate_padding")
- `CATEGORY` class variable: UI category path (e.g., "image/transform")

**Pattern observed:**
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
        # Implementation
```

---

*Convention analysis: 2026-03-10*
