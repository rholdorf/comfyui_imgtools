from .nodes import ImageDimensionFitter

NODE_CLASS_MAPPINGS = {
    "ImageDimensionFitter": ImageDimensionFitter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageDimensionFitter": "Image Dimension Fitter",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
