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
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xFFFFFFFFFFFFFFFF,
                    "control_after_generate": True,
                    "tooltip": "Seed for picking a line from random_choice.",
                }),
                "adjust_whitespace": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Collapse runs of whitespace and join parts with a single space.",
                }),
                "start": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "dynamicPrompts": False,
                    "tooltip": "Text prepended before the random line.",
                }),
                "random_choice": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "dynamicPrompts": False,
                    "tooltip": "One option per line; a single non-empty line is picked using seed.",
                }),
                "end": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "dynamicPrompts": False,
                    "tooltip": "Text appended after the random line.",
                }),
            },
            "optional": {
                "text_in": ("STRING", {
                    "default": "",
                    "forceInput": True,
                    "tooltip": "Optional upstream string; prepended before start/chosen/end.",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "concatenate"
    CATEGORY = "rholdorf/text"
    DESCRIPTION = "Pick one line at random from a multi-line list and concatenate it between optional prefix/suffix strings."

    def concatenate(self, seed, adjust_whitespace, start="", random_choice="", end="", text_in=""):
        text_in = text_in or ""
        start = start or ""
        random_choice = random_choice or ""
        end = end or ""

        lines = [l for l in random_choice.splitlines() if l.strip()]
        chosen = random.Random(seed).choice(lines) if lines else ""

        if adjust_whitespace:
            parts = [p for p in (_collapse(text_in), _collapse(start), _collapse(chosen), _collapse(end)) if p]
            return (" ".join(parts),)
        return (f"{text_in}{start}{chosen}{end}",)
