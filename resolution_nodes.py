import math


# Same list and label strings as the built-in Resolution Selector so downstream
# assumptions about the labels don't drift.
_ASPECT_RATIOS = [
    ("1:1 (Square)", 1, 1),
    ("2:3 (Portrait Photo)", 2, 3),
    ("3:2 (Photo)", 3, 2),
    ("3:4 (Portrait Standard)", 3, 4),
    ("4:3 (Standard)", 4, 3),
    ("9:16 (Portrait Widescreen)", 9, 16),
    ("16:9 (Widescreen)", 16, 9),
    ("21:9 (Ultrawide)", 21, 9),
]


def _closest_aspect_ratio(width: int, height: int):
    # log-space distance so `2:3` vs `3:2` are treated symmetrically instead of
    # the landscape ratios always winning by being numerically larger.
    if width <= 0 or height <= 0:
        return _ASPECT_RATIOS[0]
    target = math.log(width / height)
    return min(_ASPECT_RATIOS, key=lambda r: abs(math.log(r[1] / r[2]) - target))


class ResolutionSelectorFromDimensions:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {
                    "default": 1024, "min": 1, "max": 16384, "step": 1,
                    "tooltip": "Reference width — only used to detect the closest aspect ratio.",
                }),
                "height": ("INT", {
                    "default": 1024, "min": 1, "max": 16384, "step": 1,
                    "tooltip": "Reference height — only used to detect the closest aspect ratio.",
                }),
                "megapixels": ("FLOAT", {
                    "default": 1.0, "min": 0.1, "max": 16.0, "step": 0.1,
                    "tooltip": "Target total megapixels. 1.0 MP ≈ 1024x1024 for square.",
                }),
                "multiple": ("INT", {
                    "default": 8, "min": 8, "max": 128, "step": 4,
                    "tooltip": "Nearest multiple to snap the result to.",
                }),
            },
        }

    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("width", "height", "aspect_ratio")
    FUNCTION = "compute"
    CATEGORY = "rholdorf/utils"
    DESCRIPTION = (
        "Same math as the built-in Resolution Selector, but the aspect ratio is "
        "auto-detected from a reference (width, height) pair instead of being "
        "picked from a combo. Output dimensions still honor megapixels and multiple."
    )

    def compute(self, width, height, megapixels, multiple):
        label, w_ratio, h_ratio = _closest_aspect_ratio(width, height)
        total_pixels = megapixels * 1024 * 1024
        scale = math.sqrt(total_pixels / (w_ratio * h_ratio))
        out_width = round(w_ratio * scale / multiple) * multiple
        out_height = round(h_ratio * scale / multiple) * multiple
        return (out_width, out_height, label)
