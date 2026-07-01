from .loader_nodes import LoadImagesWithCaptionsFromDir, LoadImageWithCaption
from .nodes import ImageDimensionFitter, ImagePaddingCalculator, PathSplitter
from .resize_nodes import ImageResizeLanczos3NonSeparable
from .resolution_nodes import ResolutionSelectorFromDimensions
from .save_nodes import SaveImageWithCaption
from .text_nodes import RandomLineConcatenator

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {
    "ImageDimensionFitter": ImageDimensionFitter,
    "ImagePaddingCalculator": ImagePaddingCalculator,
    "ImageResizeLanczos3NonSeparable": ImageResizeLanczos3NonSeparable,
    "LoadImageWithCaption": LoadImageWithCaption,
    "LoadImagesWithCaptionsFromDir": LoadImagesWithCaptionsFromDir,
    "PathSplitter": PathSplitter,
    "RandomLineConcatenator": RandomLineConcatenator,
    "ResolutionSelectorFromDimensions": ResolutionSelectorFromDimensions,
    "SaveImageWithCaption": SaveImageWithCaption,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageDimensionFitter": "Image Dimension Fitter (rholdorf)",
    "ImagePaddingCalculator": "Image Padding Calculator (rholdorf)",
    "ImageResizeLanczos3NonSeparable": "Image Resize (Lanczos 3 non-separable) (rholdorf)",
    "LoadImageWithCaption": "Load Image with Caption (rholdorf)",
    "LoadImagesWithCaptionsFromDir": "Load Images with Captions from Dir (rholdorf)",
    "PathSplitter": "Path Splitter (rholdorf)",
    "RandomLineConcatenator": "Random Line Concatenator (rholdorf)",
    "ResolutionSelectorFromDimensions": "Resolution Selector from Dimensions (rholdorf)",
    "SaveImageWithCaption": "Save Image with Caption (rholdorf)",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
