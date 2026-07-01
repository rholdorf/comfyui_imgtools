# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development practices

When writing or modifying code in this repo, follow ComfyUI custom-node best practices: match the conventions already used by ComfyUI's built-in nodes (input/output typing, widget options, category strings), keep node interfaces stable so existing workflows still load, prefer the runtime helpers ComfyUI exposes (`folder_paths`, `comfy.cli_args`, etc.) over rolling your own, and respect the tensor layout and frontend extension patterns ComfyUI expects (see the conventions section below).

### Node naming

All nodes in this pack use the suffix `(rholdorf)` in their display name (e.g. `Image Dimension Fitter (rholdorf)`) and live under a `rholdorf/...` category. When adding a new node, follow the same convention: append ` (rholdorf)` to the entry in `NODE_DISPLAY_NAME_MAPPINGS` and set `CATEGORY` to `rholdorf/<subgroup>`. Do not change the internal class id / mapping key — that's what saved workflows reference, and renaming it breaks them.

## What this is

A ComfyUI custom-node package. It is not a standalone application: ComfyUI imports this directory as a Python package at startup, registers the nodes listed in `NODE_CLASS_MAPPINGS`, and serves the JS in `WEB_DIRECTORY` to the browser.

There is no build, lint, or test suite. "Running" means restarting ComfyUI so it re-imports the package; the parent ComfyUI install lives one directory up (`../../`). Logic changes require a ComfyUI restart; pure JS changes under `web/` only need a browser refresh.

## Architecture

### Registration entrypoint — `__init__.py`

Every public node is wired up here via three module-level names that ComfyUI looks for: `NODE_CLASS_MAPPINGS` (internal id → class), `NODE_DISPLAY_NAME_MAPPINGS` (internal id → UI label), and `WEB_DIRECTORY` (path to frontend extensions). Adding a new node means adding both an import and entries in both mappings — there is no autodiscovery.

### Node modules

- `nodes.py` — small stateless dimension/path utilities. `ImageDimensionFitter` takes INT `width`/`height` inputs and, for one of `SD` / `Flux` / `Z-Turbo` / `Krea 2`, snaps to the closest resolution from that model's discrete table by aspect-ratio distance; ties resolve to the smaller total-pixel candidate so it never upscales past what's needed. `ImagePaddingCalculator` returns padding values around a target size (its `image` input follows the ComfyUI `[batch, height, width, channels]` layout). `PathSplitter` splits a path string. The Krea 2 table is computed from Krea's documented ratios (1:1, 4:3, 3:2, 16:9, 4:5 plus portrait counterparts) targeting ~1MP, each side floored to a multiple of 32 — Krea does not publish exact pixel dimensions per ratio, so we approximate downward on purpose.
- `loader_nodes.py` — `LoadImagesWithCaptionsFromDir` (batch) and `LoadImageWithCaption` (single). The batch loader replicates the Inspire pack's `Load Image List From Dir` (same `directory`/`image_load_cap`/`start_index`/`load_always`/`sort_method` inputs and per-item `OUTPUT_IS_LIST = True` semantics, images at their original size) and adds a `caption` STRING output read from the sidecar `.txt` (see the LoRA pair convention below). The single-image loader mirrors ComfyUI's built-in `LoadImage` (dropdown + `image_upload`) and additionally returns the sidecar caption; its JS extension adds the "upload pair" button described in the frontend section. Captions for images without a `.txt` come back as empty strings — never raises.
- `resize_nodes.py` — `ImageResizeLanczos3NonSeparable`. Non-separable (radial) Lanczos-3 resize: the kernel is evaluated on the 2D distance `sqrt(dx²+dy²)` rather than as separable `L(dx)` then `L(dy)`. Result is circularly symmetric and free of the diagonal artifacts the separable form introduces — matches Affinity Photo's "Lanczos 3 (non-separable)". Inputs are `image`, `max_width`, `max_height`; the result fits inside those bounds preserving aspect and never upscales (pass-through when the image already fits). Output rows are chunked so the intermediate gathered `[B, C, chunk, target_w, ky, kx]` tensor stays under a fixed float budget (`max_floats`); do not remove the chunking loop.
- `resolution_nodes.py` — `ResolutionSelectorFromDimensions`. Same math as ComfyUI's built-in `Resolution Selector` (`scale = sqrt(target_pixels / (w_ratio * h_ratio))`, `w = round(w_ratio * scale / multiple) * multiple`, same for `h`), but the aspect ratio is auto-detected in log-space from a `(width, height)` reference pair instead of picked from a combo. Log-space distance is deliberate: it treats 2:3 and 3:2 symmetrically (linear distance in `w/h` biases toward landscape ratios). Outputs `width`, `height`, and the detected `aspect_ratio` label.
- `save_nodes.py` — `SaveImageWithCaption`. Mirrors ComfyUI's built-in SaveImage but also writes a matching `.txt` caption beside each PNG (for LoRA training pairs). Imports `folder_paths` and `comfy.cli_args` from the host ComfyUI runtime — these are only resolvable when loaded inside ComfyUI, not standalone. Uses `get_save_image_path` for the prefix/counter logic, and respects `--disable-metadata`.
- `text_nodes.py` — `RandomLineConcatenator`. Picks one line from a toggleable pool and concatenates it with optional `start`/`end`/`text_in` strings. `_parse_options` accepts both the current JSON format (`[{enabled, text}, ...]`) and the legacy newline-separated format — keep both paths working when editing.

### LoRA image+caption pair convention

Several nodes here speak a shared file-pair convention used for LoRA training: an image (`.png`, `.jpg`, `.jpeg`, `.webp`) and a UTF-8 `.txt` caption with the **same base name** in the **same directory** — e.g. `imagem001.png` ↔ `imagem001.txt`. `SaveImageWithCaption` writes this pair when generating training data; `LoadImagesWithCaptionsFromDir` reads it back. Matching is by stem only (`os.path.splitext`), and the caption side is optional: a missing `.txt` is treated as an empty string rather than an error, because real training folders routinely contain unlabelled images. Always preserve this "missing-is-empty" behavior — workflows depend on the loader never breaking on incomplete folders.

### Frontend extensions — `web/`

Loaded because `WEB_DIRECTORY = "./web"`. Each file registers a ComfyUI app extension via `app.registerExtension` and hooks `beforeRegisterNodeDef` for a specific node. Three files, three distinct patterns worth knowing when adding more:

- `random_line_options.js` — attaches a DOM widget (`options_editor`) with checkbox + text + delete rows for `RandomLineConcatenator`. Persistence trick: the underlying `random_choice` STRING widget is *hidden* (`type = "hidden"`, `computeSize = () => [0, -4]`) but not removed, because workflow save/load uses `widgets_values` and the hidden widget is what carries the serialized JSON across reloads. The DOM editor sets `serialize = false` and writes through to the hidden widget on every edit. `onConfigure` re-renders the rows from the (possibly legacy-formatted) value after a workflow loads. When changing the schema in `text_nodes.py::RandomLineConcatenator.INPUT_TYPES`, the widget name `random_choice` must stay in sync with `SOURCE_WIDGET` in the JS.
- `load_image_with_caption.js` — adds the "upload pair (.png + .txt)" button to `LoadImageWithCaption`. Uploads the image via `/upload/image`, reads back the server-assigned filename (which may differ from the source if `input/` already had one), then re-uploads the `.txt` with `overwrite=true` renamed to match the image's server-side stem. Without that rename step, ComfyUI's collision suffix on the image side would silently desync the pair.
- `resolution_selector_from_dimensions.js` — draws a readonly DOM widget on `ResolutionSelectorFromDimensions` showing the detected aspect-ratio label. Reactivity pattern: **poll `onDrawForeground` with a `lastLabel !== label` guard** rather than wrapping `widget.callback`. This is because workflow reload calls `configure()` which writes `widget.value` directly and does not fire the widget callback — a callback-based hook would only ever see the defaults after a reload. `onDrawForeground` polling catches both live edits and reloads for negligible cost. Use this pattern whenever a DOM widget needs to stay in sync with backing widget values across reloads.

### ComfyUI node conventions used here

- `INPUT_TYPES` is a `@classmethod` returning `{"required": {...}, "optional": {...}, "hidden": {...}}`. `hidden` inputs like `prompt: "PROMPT"` and `extra_pnginfo: "EXTRA_PNGINFO"` are auto-injected by ComfyUI.
- `forceInput: True` on a STRING input makes it connection-only (no widget); the node implementation treats a present upstream value as overriding the widget default (see `SaveImageWithCaption.save_images` and the `text_in` handling in `RandomLineConcatenator`).
- `OUTPUT_NODE = True` marks a terminal node (saves files, no downstream consumers).
- `OUTPUT_IS_LIST = (True, ...)` per-output tuple tells ComfyUI each output is a Python list; downstream nodes execute once per item rather than receiving a batched tensor. Used by `LoadImagesWithCaptionsFromDir` so each image/caption pair flows through the workflow separately.
- `IS_CHANGED` as a `@classmethod` lets a node opt out of ComfyUI's input-hash cache by returning `float("NaN")` (always re-run) or any stable hash to participate in caching. Loaders use this so a `load_always` toggle can force a re-read.
- `control_after_generate: True` on an INT widget gives the standard ComfyUI seed-control dropdown.
