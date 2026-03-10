# Technology Stack

**Analysis Date:** 2026-03-10

## Languages

**Primary:**
- Python 3.10+ - All source code and custom node implementation

## Runtime

**Environment:**
- Python 3.10 or higher (ComfyUI requirement)

**Package Manager:**
- pip (implied by ComfyUI ecosystem)
- Lockfile: Not present in this project (inherited from ComfyUI)

## Frameworks

**Core:**
- ComfyUI 0.16.4 - Node-based image generation framework
  - Purpose: Custom node plugin architecture that this project extends

**Dependencies (inherited from ComfyUI):**
- PyTorch (torch, torchvision, torchaudio) - Deep learning framework for tensor operations
- NumPy >= 1.25.0 - Numerical computing and tensor manipulation
- Pillow - Image processing library (used for image operations)
- PyYAML - Configuration file handling
- Transformers >= 4.50.3 - Hugging Face models integration

## Key Dependencies

**Critical:**
- torch - PyTorch tensor operations (CPU/GPU agnostic). Used for image tensor shape handling and center crop operations in `nodes.py`
- numpy >= 1.25.0 - Array operations for image dimensions
- Pillow - Image format handling and conversions

**Infrastructure:**
- ComfyUI framework - Provides the node registration system (`NODE_CLASS_MAPPINGS`, `NODE_DISPLAY_NAMES`)
- torchvision - Vision-specific utilities compatible with PyTorch
- torchsde - Stochastic differential equations (required by ComfyUI)
- transformers >= 4.50.3 - Model transformers library (required by ComfyUI)

## Configuration

**Environment:**
- No environment variables required for this custom node
- Inherits all ComfyUI configuration from parent installation

**Build:**
- No build configuration needed
- Python module deployed as-is in `custom_nodes/` directory

## Platform Requirements

**Development:**
- Python 3.10+
- ComfyUI installation (0.16.4 or compatible)
- PyTorch installation (includes torch, torchvision, torchaudio)
- All ComfyUI dependencies from `requirements.txt`

**Production:**
- Deployment target: Any ComfyUI instance with Python 3.10+
- Installation: Copy directory to `ComfyUI/custom_nodes/comfyui_imgtools/`
- Restart ComfyUI to load node

## Integration Points

**Module Integration:**
- Integrates with ComfyUI's plugin system via `__init__.py`
- Exposes three custom nodes: `ImageDimensionFitter`, `ImagePaddingCalculator`, `PathSplitter`
- Uses standard ComfyUI node interface pattern (`INPUT_TYPES`, `RETURN_TYPES`, `CATEGORY`, `FUNCTION`)

**Tensor Format:**
- Input/Output: Standard ComfyUI IMAGE tensor format `[batch, height, width, channels]` (float32)
- Compatible with all ComfyUI image nodes (VAE Encode, KSampler, etc.)

---

*Stack analysis: 2026-03-10*
