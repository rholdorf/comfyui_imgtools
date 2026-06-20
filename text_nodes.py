import random
import re

_WS_RE = re.compile(r"\s+")


def _collapse(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


class RandomLineConcatenator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "adjust_whitespace": ("BOOLEAN", {"default": True}),
                "start": ("STRING", {"default": "", "multiline": False}),
                "random_choice": ("STRING", {"default": "", "multiline": True}),
                "end": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "input": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "concatenate"
    CATEGORY = "rholdorf/text"

    def concatenate(self, seed, adjust_whitespace, start="", random_choice="", end="", input=""):
        input = input or ""
        start = start or ""
        random_choice = random_choice or ""
        end = end or ""

        lines = [l for l in random_choice.splitlines() if l.strip()]
        chosen = random.Random(seed).choice(lines) if lines else ""

        if adjust_whitespace:
            parts = [p for p in (_collapse(input), _collapse(start), _collapse(chosen), _collapse(end)) if p]
            result = " ".join(parts)
        else:
            result = f"{input}{start}{chosen}{end}"

        return (result,)
