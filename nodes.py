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

MODEL_DIMENSIONS = {
    "SD": SD_DIMENSIONS,
    "Flux": FLUX_DIMENSIONS,
    "Z-Turbo": ZTURBO_DIMENSIONS,
}


def find_closest_dimensions(width: int, height: int, model: str) -> tuple[int, int]:
    """Find the closest standard dimensions for the given model based on aspect ratio."""
    dimensions = MODEL_DIMENSIONS[model]
    input_ratio = width / height

    best_match = dimensions[0]
    best_diff = abs(input_ratio - (best_match[0] / best_match[1]))

    for w, h in dimensions[1:]:
        target_ratio = w / h
        diff = abs(input_ratio - target_ratio)
        if diff < best_diff:
            best_diff = diff
            best_match = (w, h)

    return best_match


class ImageDimensionFitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "model": (["SD", "Flux", "Z-Turbo"],),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("image", "target_width", "target_height")
    FUNCTION = "fit_dimensions"
    CATEGORY = "image/transform"

    def fit_dimensions(self, image, model):
        # image tensor shape: [batch, height, width, channels]
        _, h, w, _ = image.shape
        target_w, target_h = find_closest_dimensions(w, h, model)

        # For now, just return input image and target dimensions
        # Actual cropping will be implemented in Phase 3
        return (image, target_w, target_h)
