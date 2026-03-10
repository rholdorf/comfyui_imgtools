# Testing Patterns

**Analysis Date:** 2026-03-10

## Test Framework

**Runner:**
- Not detected

**Assertion Library:**
- Not detected

**Run Commands:**
- No test infrastructure present

## Test File Organization

**Location:**
- No test files found in codebase

**Naming:**
- Not applicable - no test files present

**Structure:**
- Not applicable - no test files present

## Test Coverage

**Current State:**
- No unit tests implemented
- No integration tests implemented
- No test fixtures or test data

**Coverage Tools:**
- Not configured

## What Should Be Tested

Based on codebase analysis, testing should focus on these areas:

### Unit Tests for Core Functions

**`center_crop()` function** (`nodes.py`, lines 48-70):
- Test cases needed:
  - Crop with image larger than target dimensions (normal case)
  - Crop with image exactly matching target dimensions (should return unchanged)
  - Crop with image smaller than target (should return unchanged per line 62-63)
  - Batch processing (multiple images in tensor)
  - Various aspect ratios
  - Edge cases: width-only smaller, height-only smaller

**`find_closest_dimensions()` function** (`nodes.py`, lines 73-88):
- Test cases needed:
  - Exact match returns first dimension (ratio match)
  - Aspect ratio matching accuracy
  - All model types: SD, Flux, Z-Turbo
  - Square images (1:1 ratio)
  - Wide images (2:1 ratio)
  - Tall images (1:2 ratio)
  - Invalid model name should raise KeyError (currently no validation)

**`ImagePaddingCalculator.calculate_padding()` method** (`nodes.py`, lines 107-115):
- Test cases needed:
  - Image smaller than target (requires padding)
  - Image equal to target (zero padding)
  - Image larger than target (negative padding clamped to zero)
  - Asymmetric padding calculation (even vs odd offsets)
  - Return order correctness: (left, top, right, bottom)

**`PathSplitter.split_path()` method** (`nodes.py`, lines 132-137):
- Test cases needed:
  - Unix paths (/home/user/image.jpg)
  - Windows paths (C:\Users\image.jpg)
  - Filenames with multiple dots (image.backup.jpg)
  - Paths without extension
  - Paths without directory component

**`ImageDimensionFitter.fit_dimensions()` method** (`nodes.py`, lines 155-163):
- Test cases needed:
  - SD model selection
  - Flux model selection
  - Z-Turbo model selection
  - Batch processing (multiple images)
  - Return tuple format validation
  - Chained behavior: finding dimensions and cropping together

### Integration Tests

**Workflow integration:**
- Test node class registration in `__init__.py`
- Verify NODE_CLASS_MAPPINGS contains all three node classes
- Verify NODE_DISPLAY_NAME_MAPPINGS matches class mappings

**ComfyUI node protocol:**
- INPUT_TYPES returns correct structure
- RETURN_TYPES count matches return value count
- RETURN_NAMES count matches RETURN_TYPES count
- FUNCTION references valid method

## Recommended Testing Approach

### Framework Choice
- **pytest** - Recommended for Python projects
  - Simple assertion syntax
  - Fixtures for tensor creation
  - Parametrize decorator for testing multiple inputs

### Test File Structure
- Location: `tests/` directory at project root
- File naming: `test_nodes.py`, `test_functions.py`
- Or co-located: `nodes_test.py` next to implementation

### Test Data Strategy

**Tensor fixtures needed:**
```python
import torch

@pytest.fixture
def sample_image_tensor():
    # [batch=1, height=512, width=512, channels=3]
    return torch.randn(1, 512, 512, 3)

@pytest.fixture
def wide_image_tensor():
    # [batch=1, height=512, width=1024, channels=3]
    return torch.randn(1, 512, 1024, 3)

@pytest.fixture
def tall_image_tensor():
    # [batch=1, height=1024, width=512, channels=3]
    return torch.randn(1, 1024, 512, 3)

@pytest.fixture
def batch_image_tensor():
    # [batch=4, height=512, width=512, channels=3]
    return torch.randn(4, 512, 512, 3)
```

**Dimension tables:**
- Use constants from `nodes.py`: `SD_DIMENSIONS`, `FLUX_DIMENSIONS`, `ZTURBO_DIMENSIONS`
- Parametrize tests to verify all dimensions work correctly

### Example Test Pattern

```python
import pytest
from nodes import center_crop, find_closest_dimensions, ImagePaddingCalculator

@pytest.mark.parametrize("width,height,model,expected", [
    (512, 512, "SD", (512, 512)),
    (1920, 1080, "SD", (768, 512)),  # Approximately 1.5:1 ratio
    (1000, 1000, "Flux", (1024, 1024)),
])
def test_find_closest_dimensions(width, height, model, expected):
    result = find_closest_dimensions(width, height, model)
    assert result == expected

def test_center_crop_normal(sample_image_tensor):
    target_w, target_h = 256, 256
    result = center_crop(sample_image_tensor, target_w, target_h)
    assert result.shape == (1, target_h, target_w, 3)

def test_center_crop_unchanged_when_small(small_image_tensor):
    # Image is 256x256, request 512x512
    target_w, target_h = 512, 512
    result = center_crop(small_image_tensor, target_w, target_h)
    assert torch.equal(result, small_image_tensor)
```

## Test Coverage Goals

**Recommended minimums:**
- Core utility functions: 100% coverage (simple, critical)
- Node class methods: 90% coverage (handles most paths)
- Error paths: All error cases tested

**Currently:**
- 0% coverage (no tests exist)

**Priority:**
1. Test `center_crop()` - critical for image quality
2. Test `find_closest_dimensions()` - core matching logic
3. Test node class integration - ensures ComfyUI compatibility

## Mocking Considerations

**What to mock:**
- File system calls in `PathSplitter.split_path()` if filesystem operations added later
- ComfyUI framework if needed for unit testing node classes

**What NOT to mock:**
- Tensor operations (test with real tensors)
- Dimension matching logic (test actual behavior)
- Array slicing operations

## Dependencies Needed for Testing

```
pytest>=7.0
pytest-cov>=3.0
numpy>=1.20  # For array comparison
torch>=1.9   # Tensors for image data
```

---

*Testing analysis: 2026-03-10*
