import json
import random
import re

_WS_RE = re.compile(r"\s+")


def _collapse(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _parse_options(raw: str) -> list[dict]:
    """Parse the random_choice widget value.

    Accepts the new JSON format (list of {enabled, text} dicts produced by the
    frontend editor) and the legacy newline-separated format. Returns a list
    of normalized {enabled, text} dicts.
    """
    raw = (raw or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            normalized = []
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                normalized.append({
                    "enabled": entry.get("enabled", True) is not False,
                    "text": str(entry.get("text", "")),
                })
            return normalized
    # Legacy fallback: one entry per non-empty line, all enabled.
    return [
        {"enabled": True, "text": line.strip()}
        for line in raw.splitlines()
        if line.strip()
    ]


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
                    "default": "[]",
                    "multiline": False,
                    "dynamicPrompts": False,
                    "tooltip": "Options pool. Edit via the toggleable rows in the node UI.",
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
    DESCRIPTION = "Pick one line at random from a toggle-able list and concatenate it between optional prefix/suffix strings."

    def concatenate(self, seed, adjust_whitespace, start="", random_choice="[]", end="", text_in=""):
        text_in = text_in or ""
        start = start or ""
        end = end or ""

        entries = _parse_options(random_choice)
        candidates = [e["text"] for e in entries if e["enabled"] and e["text"].strip()]
        chosen = random.Random(seed).choice(candidates) if candidates else ""

        if adjust_whitespace:
            parts = [p for p in (_collapse(text_in), _collapse(start), _collapse(chosen), _collapse(end)) if p]
            return (" ".join(parts),)
        return (f"{text_in}{start}{chosen}{end}",)
