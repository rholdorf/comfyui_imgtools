class ImageDimensionFitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "model": (["SD", "Flux", "Z-Turbo"],),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "fit_dimensions"
    CATEGORY = "image/transform"

    def fit_dimensions(self, image, model):
        # Placeholder - just return input for now
        return (image,)
