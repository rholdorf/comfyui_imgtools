# External Integrations

**Analysis Date:** 2026-03-10

## APIs & External Services

**Model Provider Integration:**
- Hugging Face Models - Supported indirectly through ComfyUI's transformers integration
  - SDK/Client: `transformers>=4.50.3` (from ComfyUI)
  - Auth: None required for standard model loading

**External Service Integrations:**
- Not detected - This is a pure image processing utility node with no external API calls

## Data Storage

**Databases:**
- Not applicable - No database integration in this module
- ComfyUI parent may use SQLAlchemy for workflow persistence, but this node doesn't interact with it

**File Storage:**
- Local filesystem only
- `PathSplitter` node (`nodes.py:118-137`) splits file paths using `os.path` module
- No cloud storage integration

**Caching:**
- Not applicable - No caching layer implemented
- Image tensors are processed in-memory only

## Authentication & Identity

**Auth Provider:**
- Not applicable - No authentication required
- This is an internal ComfyUI node with no external identity system

## Monitoring & Observability

**Error Tracking:**
- Not detected - No error tracking service integrated
- Standard Python exceptions are raised and handled by ComfyUI runtime

**Logs:**
- Console logging only (implicit via Python print/ComfyUI logging)
- No external logging service integration

## CI/CD & Deployment

**Hosting:**
- Source repository: GitHub (parent ComfyUI is hosted at github.com/comfyanonymous/ComfyUI)
- Custom node deployment: Direct directory copy to `ComfyUI/custom_nodes/`

**CI Pipeline:**
- Not detected - No GitHub Actions or CI configuration in this project
- Parent ComfyUI repository has CI configured (`.github/` present in parent)

## Environment Configuration

**Required env vars:**
- None - This custom node requires no environment variables

**Secrets location:**
- Not applicable - No secrets or credentials used

## Webhooks & Callbacks

**Incoming:**
- Not applicable - This is a synchronous image processing node

**Outgoing:**
- Not applicable - No webhooks or external callbacks implemented

## ComfyUI Integration

**Node Registry:**
- `__init__.py` registers three nodes:
  - `ImageDimensionFitter` - Image dimension matching and center crop
  - `ImagePaddingCalculator` - Padding calculation for target dimensions
  - `PathSplitter` - File path decomposition utility

**Node Protocol:**
- Implements standard ComfyUI node interface pattern
- Input/Output types: IMAGE (PyTorch tensors), INT (integers), STRING (paths)
- All nodes are synchronous with no async operations

**Model Compatibility:**
- SD (Stable Diffusion 1.5) - ~262k pixels, divisible by 8
- Flux - ~1MP, divisible by 32
- Z-Turbo - ~1MP, divisible by 32
- Dimension tables defined in `nodes.py:1-45`

---

*Integration audit: 2026-03-10*
