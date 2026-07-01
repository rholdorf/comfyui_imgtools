# Dimension tables: list of (width, height) tuples
# SD 1.5: ~262k pixels, divisible by 8
SD_DIMENSIONS = [
    (512, 512),   # 1:1
    (640, 512),   # 5:4
    (512, 640),   # 4:5
    (704, 512),   # ~1.37:1
    (512, 704),   # ~1:1.37
    (768, 512),   # 3:2
    (512, 768),   # 2:3
]

# Flux: ~1MP, divisible by 32
FLUX_DIMENSIONS = [
    (1024, 1024),  # 1:1
    (1152, 896),   # 9:7
    (896, 1152),   # 7:9
    (1216, 832),   # 19:13
    (832, 1216),   # 13:19
    (1344, 768),   # 7:4
    (768, 1344),   # 4:7
    (1536, 640),   # 12:5
    (640, 1536),   # 5:12
    (1920, 1080),  # 16:9
    (1080, 1920),  # 9:16
]

# Z-Turbo: ~1MP, divisible by 32 (similar to Flux)
ZTURBO_DIMENSIONS = [
    (1024, 1024),  # 1:1
    (1152, 896),   # 9:7
    (896, 1152),   # 7:9
    (1216, 832),   # 19:13
    (832, 1216),   # 13:19
    (1344, 768),   # 7:4
    (768, 1344),   # 4:7
    (1536, 640),   # 12:5
    (640, 1536),   # 5:12
]

# Krea 2: ~1MP, divisible by 32. Krea does not publish exact pixel dimensions;
# these are computed from the documented aspect ratios (1:1, 4:3, 3:2, 16:9, 4:5
# and their portrait counterparts) targeting 1024x1024 total pixels, with each
# side floored to the nearest multiple of 32 so we never upscale past the target.
KREA2_DIMENSIONS = [
    (1024, 1024),  # 1:1
    (1152, 864),   # 4:3   (ratio 1.333 exact)
    (864, 1152),   # 3:4
    (1248, 832),   # 3:2   (ratio 1.5 exact)
    (832, 1248),   # 2:3
    (1344, 768),   # 16:9  (ratio 1.75)
    (768, 1344),   # 9:16
    (1120, 896),   # 5:4   (ratio 1.25 exact)
    (896, 1120),   # 4:5
]

MODEL_DIMENSIONS = {
    "SD": SD_DIMENSIONS,
    "Flux": FLUX_DIMENSIONS,
    "Z-Turbo": ZTURBO_DIMENSIONS,
    "Krea 2": KREA2_DIMENSIONS,
}


def find_closest_dimensions(width: int, height: int, model: str) -> tuple[int, int]:
    """Find the closest standard dimensions for the given model based on aspect ratio.

    Ties in ratio-distance resolve to the smaller total-pixel candidate so we
    never upscale past what's needed.
    """
    dimensions = MODEL_DIMENSIONS[model]
    input_ratio = width / height
    return min(
        dimensions,
        key=lambda d: (abs(input_ratio - d[0] / d[1]), d[0] * d[1]),
    )


class ImagePaddingCalculator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "target_width": ("INT", {"default": 1024, "min": 1}),
                "target_height": ("INT", {"default": 1024, "min": 1}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "INT")
    RETURN_NAMES = ("left", "top", "right", "bottom")
    FUNCTION = "calculate_padding"
    CATEGORY = "rholdorf/image"

    def calculate_padding(self, image, target_width, target_height):
        _, h, w, _ = image.shape
        pad_x = max(target_width - w, 0)
        pad_y = max(target_height - h, 0)
        left = pad_x // 2
        right = pad_x - left
        top = pad_y // 2
        bottom = pad_y - top
        return (left, top, right, bottom)


class PathSplitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("directory", "filename", "stem")
    FUNCTION = "split_path"
    CATEGORY = "rholdorf/utils"

    def split_path(self, path):
        import os
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        stem = os.path.splitext(filename)[0]
        return (directory, filename, stem)


class ImageDimensionFitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {
                    "default": 1024, "min": 1, "max": 16384, "step": 1,
                    "tooltip": "Reference width — used to detect the closest model resolution.",
                }),
                "height": ("INT", {
                    "default": 1024, "min": 1, "max": 16384, "step": 1,
                    "tooltip": "Reference height — used to detect the closest model resolution.",
                }),
                "model": (["SD", "Flux", "Z-Turbo", "Krea 2"],),
            },
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("target_width", "target_height")
    FUNCTION = "fit_dimensions"
    CATEGORY = "rholdorf/image"

    def fit_dimensions(self, width, height, model):
        target_w, target_h = find_closest_dimensions(width, height, model)
        return (target_w, target_h)
