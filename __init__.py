from .nodes import ImageDimensionFitter, ImagePaddingCalculator, PathSplitter

NODE_CLASS_MAPPINGS = {
    "ImageDimensionFitter": ImageDimensionFitter,
    "ImagePaddingCalculator": ImagePaddingCalculator,
    "PathSplitter": PathSplitter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageDimensionFitter": "Image Dimension Fitter",
    "ImagePaddingCalculator": "Image Padding Calculator",
    "PathSplitter": "Path Splitter",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
