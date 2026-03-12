"""LoadFaceModel ComfyUI node - loads a saved .facemodel.npz file."""

from .utils.model_io import load_face_model


class LoadFaceModel:
    """Load a face model from a .facemodel.npz file.

    Wraps the load_face_model() utility to provide a ComfyUI node that
    accepts a file path and outputs a FACE_MODEL dict for downstream
    morph nodes.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("FACE_MODEL",)
    RETURN_NAMES = ("face_model",)
    FUNCTION = "load_model"
    CATEGORY = "imgtools/face"

    def load_model(self, file_path: str):
        if not file_path.strip():
            print("[LoadFaceModel] Warning: Empty file path provided")
            return ({},)

        try:
            model = load_face_model(file_path)
            return (model,)
        except FileNotFoundError as e:
            print(f"[LoadFaceModel] Warning: {e}")
            return ({},)
        except ValueError as e:
            print(f"[LoadFaceModel] Warning: {e}")
            return ({},)
        except Exception as e:
            print(f"[LoadFaceModel] Warning: Unexpected error: {e}")
            return ({},)
