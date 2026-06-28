from .loader_nodes import LoadImagesWithCaptionsFromDir
from .nodes import ImageDimensionFitter, ImagePaddingCalculator, PathSplitter
from .resize_nodes import ImageResizeLanczos3NonSeparable
from .save_nodes import SaveImageWithCaption
from .text_nodes import RandomLineConcatenator

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {
    "ImageDimensionFitter": ImageDimensionFitter,
    "ImagePaddingCalculator": ImagePaddingCalculator,
    "ImageResizeLanczos3NonSeparable": ImageResizeLanczos3NonSeparable,
    "LoadImagesWithCaptionsFromDir": LoadImagesWithCaptionsFromDir,
    "PathSplitter": PathSplitter,
    "RandomLineConcatenator": RandomLineConcatenator,
    "SaveImageWithCaption": SaveImageWithCaption,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageDimensionFitter": "Image Dimension Fitter (rholdorf)",
    "ImagePaddingCalculator": "Image Padding Calculator (rholdorf)",
    "ImageResizeLanczos3NonSeparable": "Image Resize (Lanczos 3 non-separable) (rholdorf)",
    "LoadImagesWithCaptionsFromDir": "Load Images with Captions from Dir (rholdorf)",
    "PathSplitter": "Path Splitter (rholdorf)",
    "RandomLineConcatenator": "Random Line Concatenator (rholdorf)",
    "SaveImageWithCaption": "Save Image with Caption (rholdorf)",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
