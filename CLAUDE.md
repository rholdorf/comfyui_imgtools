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

- `nodes.py` — pure-tensor image utilities. `ImageDimensionFitter` finds the closest standard resolution for SD/Flux/Z-Turbo from the per-model dimension tables and center-crops to it; `ImagePaddingCalculator` returns padding values; `PathSplitter` splits a path string. Image tensors follow ComfyUI's convention: `[batch, height, width, channels]`.
- `loader_nodes.py` — `LoadImagesWithCaptionsFromDir`. Replicates the Inspire pack's `Load Image List From Dir` (same `directory`/`image_load_cap`/`start_index`/`load_always`/`sort_method` inputs and the same per-item `OUTPUT_IS_LIST = True` semantics, images returned at their original size) and adds a `caption` STRING output read from the sidecar `.txt` (see the LoRA pair convention below). Captions for images without a `.txt` come back as empty strings — never raises.
- `save_nodes.py` — `SaveImageWithCaption`. Mirrors ComfyUI's built-in SaveImage but also writes a matching `.txt` caption beside each PNG (for LoRA training pairs). Imports `folder_paths` and `comfy.cli_args` from the host ComfyUI runtime — these are only resolvable when loaded inside ComfyUI, not standalone. Uses `get_save_image_path` for the prefix/counter logic, and respects `--disable-metadata`.
- `text_nodes.py` — `RandomLineConcatenator`. Picks one line from a toggleable pool and concatenates it with optional `start`/`end`/`text_in` strings. `_parse_options` accepts both the current JSON format (`[{enabled, text}, ...]`) and the legacy newline-separated format — keep both paths working when editing.

### LoRA image+caption pair convention

Several nodes here speak a shared file-pair convention used for LoRA training: an image (`.png`, `.jpg`, `.jpeg`, `.webp`) and a UTF-8 `.txt` caption with the **same base name** in the **same directory** — e.g. `imagem001.png` ↔ `imagem001.txt`. `SaveImageWithCaption` writes this pair when generating training data; `LoadImagesWithCaptionsFromDir` reads it back. Matching is by stem only (`os.path.splitext`), and the caption side is optional: a missing `.txt` is treated as an empty string rather than an error, because real training folders routinely contain unlabelled images. Always preserve this "missing-is-empty" behavior — workflows depend on the loader never breaking on incomplete folders.

### Frontend extension — `web/random_line_options.js`

Loaded because `WEB_DIRECTORY = "./web"`. It registers a ComfyUI app extension via `app.registerExtension` and, in `beforeRegisterNodeDef`, attaches a DOM widget (`options_editor`) that renders rows with checkbox + text + delete for the `random_choice` widget. Key persistence trick: the underlying `random_choice` STRING widget is *hidden* (`type = "hidden"`, `computeSize = () => [0, -4]`) but not removed, because workflow save/load uses `widgets_values` and the hidden widget is what carries the serialized JSON across reloads. The DOM editor sets `serialize = false` and writes through to the hidden widget on every edit. `onConfigure` re-renders the rows from the (possibly legacy-formatted) value after a workflow loads.

When changing the schema in `text_nodes.py::RandomLineConcatenator.INPUT_TYPES`, the widget name `random_choice` must stay in sync with `SOURCE_WIDGET` in the JS.

### ComfyUI node conventions used here

- `INPUT_TYPES` is a `@classmethod` returning `{"required": {...}, "optional": {...}, "hidden": {...}}`. `hidden` inputs like `prompt: "PROMPT"` and `extra_pnginfo: "EXTRA_PNGINFO"` are auto-injected by ComfyUI.
- `forceInput: True` on a STRING input makes it connection-only (no widget); the node implementation treats a present upstream value as overriding the widget default (see `SaveImageWithCaption.save_images` and the `text_in` handling in `RandomLineConcatenator`).
- `OUTPUT_NODE = True` marks a terminal node (saves files, no downstream consumers).
- `OUTPUT_IS_LIST = (True, ...)` per-output tuple tells ComfyUI each output is a Python list; downstream nodes execute once per item rather than receiving a batched tensor. Used by `LoadImagesWithCaptionsFromDir` so each image/caption pair flows through the workflow separately.
- `IS_CHANGED` as a `@classmethod` lets a node opt out of ComfyUI's input-hash cache by returning `float("NaN")` (always re-run) or any stable hash to participate in caching. Loaders use this so a `load_always` toggle can force a re-read.
- `control_after_generate: True` on an INT widget gives the standard ComfyUI seed-control dropdown.
