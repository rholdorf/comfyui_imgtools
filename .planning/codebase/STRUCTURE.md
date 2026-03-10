# Codebase Structure

**Analysis Date:** 2026-03-10

## Directory Layout

```
comfyui_imgtools/
├── __init__.py           # Plugin registration and exports
├── nodes.py              # All node classes and algorithms
├── README.md             # User documentation
└── .planning/
    └── codebase/         # Architecture analysis documents (this location)
```

## Directory Purposes

**comfyui_imgtools/ (root):**
- Purpose: ComfyUI custom node package
- Contains: Python module files, documentation, configuration
- Key files: `__init__.py`, `nodes.py`

**.planning/codebase/:**
- Purpose: Architecture and design documentation for development guidance
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md
- Key files: ARCHITECTURE.md (this analysis)

## Key File Locations

**Entry Points:**
- `__init__.py`: Plugin entry point - exports NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS for ComfyUI loader

**Configuration:**
- `nodes.py`: Contains all dimension definitions as module-level constants (SD_DIMENSIONS, FLUX_DIMENSIONS, ZTURBO_DIMENSIONS)

**Core Logic:**
- `nodes.py` lines 48-70: center_crop() - tensor-based image cropping algorithm
- `nodes.py` lines 73-88: find_closest_dimensions() - aspect ratio matching algorithm
- `nodes.py` lines 91-115: ImagePaddingCalculator - padding calculation node
- `nodes.py` lines 118-137: PathSplitter - file path decomposition node
- `nodes.py` lines 140-163: ImageDimensionFitter - dimension fitting and cropping node

**Testing:**
- Not currently present - no test directory or test files

## Naming Conventions

**Files:**
- `__init__.py`: Python package marker and plugin registration
- `nodes.py`: Single file containing all node classes and supporting functions
- `README.md`: User-facing documentation

**Functions:**
- Lowercase with underscores: center_crop(), find_closest_dimensions(), split_path(), calculate_padding()
- Algorithm functions: verb-noun pattern (crop, find, split, calculate)

**Classes:**
- PascalCase: ImageDimensionFitter, ImagePaddingCalculator, PathSplitter
- Naming: Adjective-Noun pattern (Dimension Fitter, Padding Calculator, Path Splitter)
- Suffix: Node class names end with semantic label (Fitter, Calculator, Splitter)

**Constants:**
- SCREAMING_SNAKE_CASE: SD_DIMENSIONS, FLUX_DIMENSIONS, ZTURBO_DIMENSIONS, MODEL_DIMENSIONS
- Data tables: _DIMENSIONS suffix for dimension lists

**Variables:**
- Lowercase with underscores: target_w, target_h, x_offset, y_offset, input_ratio, best_match
- Abbreviated where clear from context: w (width), h (height), x, y (coordinates)

**Types:**
- ComfyUI string constants: "IMAGE", "INT", "STRING"
- Dimension tuples: (width, height) order
- Tensor shape order: [batch, height, width, channels]

## Where to Add New Code

**New Feature (image transformation):**
- Primary code: Add function to `nodes.py` above node class that uses it
- Node class: Add new class to `nodes.py` following ImageDimensionFitter pattern
- Registration: Add entry to NODE_CLASS_MAPPINGS in `__init__.py`

**New Dimension Model:**
- Data: Add `MODELNAME_DIMENSIONS` constant list at top of `nodes.py` with (width, height) tuples
- Registration: Add entry to MODEL_DIMENSIONS dict
- Node: No changes needed - find_closest_dimensions() automatically supports new model via dict lookup

**New Utility Node (non-image):**
- Location: Add to `nodes.py` following PathSplitter pattern
- Pattern: Implement INPUT_TYPES() classmethod, RETURN_TYPES, FUNCTION, CATEGORY
- Registration: Add to NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS in `__init__.py`

**Core Algorithm Enhancement:**
- Location: `nodes.py` - add function alongside center_crop() and find_closest_dimensions()
- Design: Keep functions pure (no side effects), preserve tensor batch dimension handling

## Special Directories

**__pycache__:**
- Purpose: Python compiled bytecode cache
- Generated: Yes (automatically by Python)
- Committed: No (in .gitignore)

**.git:**
- Purpose: Version control repository
- Generated: Yes (git repository)
- Committed: No (directory marker)

**.planning:**
- Purpose: GSD planning documents and analysis
- Generated: Manual (created by GSD agents)
- Committed: Yes (tracks architectural decisions)

## Module Organization

**Single-file design:**
- All node classes and algorithms in `nodes.py` (164 lines total)
- Rationale: Small plugin with 3 nodes; monolithic design sufficient
- Refactoring trigger: If >500 lines or >5 nodes, consider splitting into nodes/, utils/, constants/ subdirectories

**Import structure:**
- `__init__.py` imports from `.nodes` (relative import)
- `nodes.py` minimal external imports (only `os` module inside split_path method)
- No circular dependencies
- Pure Python standard library (no external dependencies)

---

*Structure analysis: 2026-03-10*
