# Architecture

**Analysis Date:** 2026-03-10

## Pattern Overview

**Overall:** Node-based plugin architecture following ComfyUI custom node convention

**Key Characteristics:**
- Pluggable node classes that register via NODE_CLASS_MAPPINGS
- Stateless node design with input type definitions and output declarations
- Model-aware dimension mapping with mathematical aspect ratio matching
- Image tensor manipulation using NumPy-style operations on batch dimensions
- Utility-focused nodes for image transformation, padding calculation, and path handling

## Layers

**Node Interface Layer:**
- Purpose: Define ComfyUI node contract through INPUT_TYPES() and RETURN_TYPES
- Location: `nodes.py` (classes: ImageDimensionFitter, ImagePaddingCalculator, PathSplitter)
- Contains: Node class definitions with INPUT_TYPES classmethod, FUNCTION name, RETURN_TYPES, CATEGORY
- Depends on: ComfyUI runtime (IMAGE, INT, STRING types), core algorithm functions
- Used by: ComfyUI node registry during workflow execution

**Algorithm Layer:**
- Purpose: Core image processing and dimension matching logic
- Location: `nodes.py` (functions: center_crop, find_closest_dimensions)
- Contains: Pure functions for tensor operations and aspect ratio matching
- Depends on: Shape introspection of image tensors, dimension lookup tables
- Used by: Node interface layer (ImageDimensionFitter specifically)

**Data Definition Layer:**
- Purpose: Model-specific standard dimensions and dimension mappings
- Location: `nodes.py` (constants: SD_DIMENSIONS, FLUX_DIMENSIONS, ZTURBO_DIMENSIONS, MODEL_DIMENSIONS)
- Contains: Dimension tuples (width, height) organized by model, lookup dictionary
- Depends on: Nothing (pure data)
- Used by: find_closest_dimensions() algorithm

**Registration Layer:**
- Purpose: Export nodes to ComfyUI plugin system
- Location: `__init__.py`
- Contains: NODE_CLASS_MAPPINGS dict, NODE_DISPLAY_NAME_MAPPINGS dict
- Depends on: Node class imports from nodes.py
- Used by: ComfyUI loader during plugin initialization

## Data Flow

**Image Dimension Fitting Flow:**

1. User selects ImageDimensionFitter node in ComfyUI workflow
2. ComfyUI invokes fit_dimensions(image, model) with tensor and model selection
3. fit_dimensions() extracts dimensions: _, h, w, _ = image.shape (batch-aware)
4. find_closest_dimensions(w, h, model) looks up MODEL_DIMENSIONS[model]
5. Aspect ratio matching: calculates input_ratio, compares against each standard dimension
6. Returns best match tuple (target_w, target_h) with minimum ratio difference
7. center_crop(image, target_w, target_h) applies center crop to all batch items
8. Returns cropped image tensor + output dimensions (target_w, target_h)
9. ComfyUI passes outputs downstream to next nodes in workflow

**Padding Calculation Flow:**

1. User connects ImagePaddingCalculator with image and target dimensions
2. calculate_padding(image, target_width, target_height) extracts image.shape
3. Calculates total padding needed: pad_x = max(target_width - w, 0)
4. Distributes padding: left = pad_x // 2, right = pad_x - left
5. Returns tuple (left, top, right, bottom) for use with PAD nodes

**Path Splitting Flow:**

1. User inputs file path string to PathSplitter node
2. split_path(path) uses os.path operations for decomposition
3. Returns tuple (directory, filename, stem) as STRING outputs

**State Management:**
- No state management: All nodes are stateless, pure transformations
- Each invocation independent, no caching or side effects
- Image tensors passed by value through ComfyUI workflow graph

## Key Abstractions

**Dimension Matching:**
- Purpose: Find closest standard dimensions based on input aspect ratio
- Examples: `find_closest_dimensions()` in `nodes.py` (lines 73-88)
- Pattern: Brute-force comparison against dimension table, return tuple with minimal ratio difference

**Center Cropping:**
- Purpose: Resize image to target dimensions while preserving center content
- Examples: `center_crop()` in `nodes.py` (lines 48-70)
- Pattern: Calculate centered offsets, use tensor slicing [batch, y:y+h, x:x+w, channels]

**ComfyUI Node Interface:**
- Purpose: Adapt algorithms to ComfyUI's node invocation contract
- Examples: ImageDimensionFitter.INPUT_TYPES(), ImagePaddingCalculator.FUNCTION
- Pattern: INPUT_TYPES classmethod returns dict of parameter names→types; RETURN_TYPES tuple; FUNCTION string names the execution method

## Entry Points

**Plugin Initialization:**
- Location: `__init__.py`
- Triggers: ComfyUI loader discovers custom_nodes/comfyui_imgtools
- Responsibilities: Export NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS for registration

**Node Execution:**
- Location: `nodes.py` - ImageDimensionFitter.fit_dimensions(), ImagePaddingCalculator.calculate_padding(), PathSplitter.split_path()
- Triggers: ComfyUI runtime invokes node during workflow execution
- Responsibilities: Process input tensors/strings, execute algorithm, return typed outputs

## Error Handling

**Strategy:** Minimal error handling; relies on ComfyUI type checking and NumPy tensor validation

**Patterns:**
- Dimension mismatch (e.g., image smaller than target): center_crop returns image unchanged (lines 61-63)
- Invalid model name: find_closest_dimensions raises KeyError if model not in MODEL_DIMENSIONS (expected behavior)
- Missing image tensor: ComfyUI type system prevents node execution with wrong types

## Cross-Cutting Concerns

**Logging:** Not implemented - nodes are silent operations suitable for batch workflows

**Validation:** Input validation delegated to ComfyUI type system (IMAGE, INT, STRING types specified in INPUT_TYPES)

**Error Handling:** Graceful degradation for edge cases (small images, missing input); hard failures for logic errors (invalid model selection)

**Batch Processing:** All image operations preserve batch dimension (first dimension), allowing multi-image processing in single node invocation

---

*Architecture analysis: 2026-03-10*
