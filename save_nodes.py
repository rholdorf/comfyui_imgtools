import json
import os

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

import folder_paths
from comfy.cli_args import args


class SaveImageWithCaption:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "caption": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Caption written as a UTF-8 .txt file alongside each image (same base name).",
                }),
                "filename_prefix": ("STRING", {
                    "default": "ComfyUI",
                    "tooltip": "Prefix for the saved files. May include formatting like %date:yyyy-MM-dd% or %Empty Latent Image.width%.",
                }),
            },
            "optional": {
                "caption_in": ("STRING", {"default": "", "forceInput": True}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "rholdorf/image"
    DESCRIPTION = "Save images as PNG with standard ComfyUI metadata plus a matching UTF-8 .txt caption file (for LoRA training pairs)."

    def save_images(self, images, caption="", filename_prefix="ComfyUI",
                    caption_in=None, prompt=None, extra_pnginfo=None):
        # An upstream string overrides the widget value when connected.
        text = caption_in if caption_in else caption
        text = text or ""

        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(
            filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0]
        )
        results = []
        for batch_number, image in enumerate(images):
            arr = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for key in extra_pnginfo:
                        metadata.add_text(key, json.dumps(extra_pnginfo[key]))

            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            base = f"{filename_with_batch_num}_{counter:05}_"
            image_file = f"{base}.png"
            text_file = f"{base}.txt"

            img.save(
                os.path.join(full_output_folder, image_file),
                pnginfo=metadata,
                compress_level=self.compress_level,
            )
            with open(os.path.join(full_output_folder, text_file), "w", encoding="utf-8") as f:
                f.write(text)

            results.append({
                "filename": image_file,
                "subfolder": subfolder,
                "type": self.type,
            })
            counter += 1

        return {"ui": {"images": results}}
