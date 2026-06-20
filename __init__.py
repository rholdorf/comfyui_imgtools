from .nodes import ImageDimensionFitter, ImagePaddingCalculator, PathSplitter
from .text_nodes import RandomLineConcatenator

NODE_CLASS_MAPPINGS = {
    "ImageDimensionFitter": ImageDimensionFitter,
    "ImagePaddingCalculator": ImagePaddingCalculator,
    "PathSplitter": PathSplitter,
    "RandomLineConcatenator": RandomLineConcatenator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageDimensionFitter": "Image Dimension Fitter",
    "ImagePaddingCalculator": "Image Padding Calculator",
    "PathSplitter": "Path Splitter",
    "RandomLineConcatenator": "rholdorf Random Line Concatenator",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
