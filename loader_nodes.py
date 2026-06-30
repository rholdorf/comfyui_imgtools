import hashlib
import os
import re

import numpy as np
import torch
from PIL import Image, ImageOps

import folder_paths


_SORT_METHODS = [
    "None",
    "Alphabetical (ASC)",
    "Alphabetical (DESC)",
    "Numerical (ASC)",
    "Numerical (DESC)",
    "Datetime (ASC)",
    "Datetime (DESC)",
]

_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def _first_number(name: str) -> int:
    match = re.search(r"\d+", name)
    return int(match.group()) if match else float("inf")


def _mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return float("-inf")


def _sort_files(files, directory: str, method):
    if method == "Alphabetical (ASC)":
        return sorted(files)
    if method == "Alphabetical (DESC)":
        return sorted(files, reverse=True)
    if method == "Numerical (ASC)":
        return sorted(files, key=lambda f: _first_number(os.path.splitext(f)[0]))
    if method == "Numerical (DESC)":
        return sorted(files, key=lambda f: _first_number(os.path.splitext(f)[0]), reverse=True)
    if method == "Datetime (ASC)":
        return sorted(files, key=lambda f: _mtime(os.path.join(directory, f)))
    if method == "Datetime (DESC)":
        return sorted(files, key=lambda f: _mtime(os.path.join(directory, f)), reverse=True)
    return files


def _read_caption(image_path: str) -> str:
    # LoRA-pair convention: caption lives next to the image with the same stem and .txt extension.
    txt_path = os.path.splitext(image_path)[0] + ".txt"
    if not os.path.isfile(txt_path):
        return ""
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read()


class LoadImagesWithCaptionsFromDir:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {
                    "default": "",
                    "tooltip": "Folder to scan for image files.",
                }),
            },
            "optional": {
                "image_load_cap": ("INT", {
                    "default": 0, "min": 0, "step": 1,
                    "tooltip": "Stop after this many images (0 = no limit).",
                }),
                "start_index": ("INT", {
                    "default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "step": 1,
                    "tooltip": "Skip this many files at the start of the sorted list.",
                }),
                "load_always": ("BOOLEAN", {
                    "default": False, "label_on": "enabled", "label_off": "disabled",
                    "tooltip": "Re-read the folder every run (defeats ComfyUI caching).",
                }),
                "sort_method": (_SORT_METHODS, {
                    "tooltip": "How to order files before slicing.",
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "caption", "file_path")
    OUTPUT_IS_LIST = (True, True, True, True)
    FUNCTION = "load"
    CATEGORY = "rholdorf/image"
    DESCRIPTION = (
        "Load images from a folder along with their sidecar UTF-8 .txt captions "
        "(same base name, as used for LoRA training pairs). Images without a "
        "matching .txt yield an empty caption string."
    )

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if kwargs.get("load_always"):
            return float("NaN")
        return hash(frozenset(kwargs.items()))

    def load(self, directory, image_load_cap=0, start_index=0, load_always=False, sort_method=None):
        if not os.path.isdir(directory):
            raise FileNotFoundError(f"Directory '{directory}' cannot be found.")

        entries = [
            f for f in os.listdir(directory)
            if f.lower().endswith(_IMAGE_EXTENSIONS)
            and os.path.isfile(os.path.join(directory, f))
        ]
        if not entries:
            raise FileNotFoundError(f"No image files in directory '{directory}'.")

        entries = _sort_files(entries, directory, sort_method)
        paths = [os.path.join(directory, f) for f in entries][start_index:]

        images, masks, captions, file_paths = [], [], [], []
        for idx, image_path in enumerate(paths):
            if image_load_cap > 0 and idx >= image_load_cap:
                break

            pil = Image.open(image_path)
            pil = ImageOps.exif_transpose(pil)
            rgb = np.array(pil.convert("RGB")).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(rgb)[None,]

            if "A" in pil.getbands():
                alpha = np.array(pil.getchannel("A")).astype(np.float32) / 255.0
                mask_tensor = 1.0 - torch.from_numpy(alpha)
            else:
                mask_tensor = torch.zeros((64, 64), dtype=torch.float32)

            images.append(image_tensor)
            masks.append(mask_tensor)
            captions.append(_read_caption(image_path))
            file_paths.append(image_path)

        return (images, masks, captions, file_paths)


class LoadImageWithCaption:
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [
            f for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
        ]
        files = folder_paths.filter_files_content_types(files, ["image"])
        return {
            "required": {
                "image": (sorted(files), {"image_upload": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("image", "mask", "caption")
    FUNCTION = "load"
    CATEGORY = "rholdorf/image"
    DESCRIPTION = (
        "Load a single image (like the built-in Load Image node) and also "
        "return its sidecar UTF-8 .txt caption (same base name) when present. "
        "Use the 'upload pair (.png + .txt)' button to upload both files at "
        "once — multi-select them in the file dialog (Cmd/Ctrl+click). "
        "Returns an empty caption string when no matching .txt is found."
    )

    def load(self, image):
        image_path = folder_paths.get_annotated_filepath(image)

        pil = Image.open(image_path)
        pil = ImageOps.exif_transpose(pil)
        rgb = np.array(pil.convert("RGB")).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(rgb)[None,]

        if "A" in pil.getbands():
            alpha = np.array(pil.getchannel("A")).astype(np.float32) / 255.0
            mask_tensor = (1.0 - torch.from_numpy(alpha)).unsqueeze(0)
        else:
            mask_tensor = torch.zeros((1, 64, 64), dtype=torch.float32)

        return (image_tensor, mask_tensor, _read_caption(image_path))

    @classmethod
    def IS_CHANGED(cls, image):
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, "rb") as f:
            m.update(f.read())
        txt_path = os.path.splitext(image_path)[0] + ".txt"
        if os.path.isfile(txt_path):
            with open(txt_path, "rb") as f:
                m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        if not folder_paths.exists_annotated_filepath(image):
            return f"Invalid image file: {image}"
        return True
