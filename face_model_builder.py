"""FaceModelBuilder ComfyUI node - builds canonical face model from image directory."""

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

from .utils.model_builder import build_face_model
from .utils.morph_utils import MORPH_CONTROL_INDICES
from .utils.face_mask import FACE_OVAL_INDICES


def format_quality_report(
    results: list[dict],
    save_path: str,
    yaw_thresh: float,
    pitch_thresh: float,
) -> str:
    """Format per-image results as an aligned plain-text quality report.

    Sort order: ACCEPTED first (by weight descending), then REJECTED
    (by yaw ascending), then NO FACE (by filename).

    Args:
        results: List of per-image result dicts from build_face_model.
        save_path: Path where the model was saved.
        yaw_thresh: Yaw threshold used.
        pitch_thresh: Pitch threshold used.

    Returns:
        Formatted multi-line string.
    """
    accepted = sorted(
        [r for r in results if r["status"] == "ACCEPTED"],
        key=lambda r: r["weight"],
        reverse=True,
    )
    rejected = sorted(
        [r for r in results if r["status"] == "REJECTED"],
        key=lambda r: abs(r["yaw"]),
    )
    no_face = sorted(
        [r for r in results if r["status"] == "NO FACE"],
        key=lambda r: r["filename"],
    )

    ordered = accepted + rejected + no_face

    # Build rows
    headers = ("File", "Status", "Yaw", "Pitch", "Roll", "Conf", "Weight")
    rows = []
    for r in ordered:
        if r["status"] == "NO FACE":
            rows.append((
                r["filename"], r["status"],
                "N/A", "N/A", "N/A", "N/A", "N/A",
            ))
        elif r["status"] == "REJECTED":
            rows.append((
                r["filename"], r["status"],
                f"{r['yaw']:+.1f}", f"{r['pitch']:+.1f}", f"{r['roll']:+.1f}",
                f"{r['confidence']:.2f}", "-",
            ))
        else:
            rows.append((
                r["filename"], r["status"],
                f"{r['yaw']:+.1f}", f"{r['pitch']:+.1f}", f"{r['roll']:+.1f}",
                f"{r['confidence']:.2f}", f"{r['weight']:.3f}",
            ))

    # Calculate column widths
    all_rows = [headers] + rows
    widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(headers))]

    def fmt_row(row):
        return " | ".join(str(col).ljust(widths[i]) for i, col in enumerate(row))

    lines = []
    lines.append(fmt_row(headers))
    lines.append("-+-".join("-" * w for w in widths))
    for row in rows:
        lines.append(fmt_row(row))

    # Summary counts
    n_accepted = len(accepted)
    n_rejected = len(rejected)
    n_noface = len(no_face)
    total = len(results)
    lines.append("")
    lines.append(
        f"Total: {total} | Accepted: {n_accepted} | "
        f"Rejected: {n_rejected} | No face: {n_noface}"
    )
    lines.append(f"Thresholds: yaw={yaw_thresh:.1f} deg, pitch={pitch_thresh:.1f} deg")
    lines.append(f"Model saved to: {save_path}")

    return "\n".join(lines)


def render_preview(
    canonical_2d: np.ndarray,
    control_indices: list[int],
    oval_indices: list[int],
    n_images: int,
) -> np.ndarray:
    """Render a 512x512 preview of control points and face contour.

    Args:
        canonical_2d: (478, 2) array of landmark XY coordinates.
        control_indices: Indices of morph control points (drawn as green dots).
        oval_indices: Indices of face oval contour (drawn as white lines).
        n_images: Number of images used (shown in header text).

    Returns:
        numpy array (512, 512, 3) uint8.
    """
    size = 512
    img = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Header text
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((10, 10), f"FaceModel ({n_images} images)", fill=(255, 255, 255), font=font)

    # Compute bounding box of control points for scaling
    ctrl_pts = canonical_2d[control_indices]  # (N, 2)
    x_min, y_min = ctrl_pts.min(axis=0)
    x_max, y_max = ctrl_pts.max(axis=0)

    margin = 50
    canvas_w = size - 2 * margin
    canvas_h = size - 2 * margin - 30  # leave room for header

    data_w = x_max - x_min
    data_h = y_max - y_min

    if data_w < 1e-9 or data_h < 1e-9:
        return np.array(img, dtype=np.uint8)

    scale = min(canvas_w / data_w, canvas_h / data_h)

    # Center offset
    scaled_w = data_w * scale
    scaled_h = data_h * scale
    offset_x = margin + (canvas_w - scaled_w) / 2
    offset_y = margin + 30 + (canvas_h - scaled_h) / 2  # 30px for header

    def to_pixel(pt):
        x = (pt[0] - x_min) * scale + offset_x
        y = (pt[1] - y_min) * scale + offset_y
        return (x, y)

    # Draw face oval contour as connected white lines
    oval_pts = [to_pixel(canonical_2d[idx]) for idx in oval_indices]
    for i in range(len(oval_pts)):
        p1 = oval_pts[i]
        p2 = oval_pts[(i + 1) % len(oval_pts)]
        draw.line([p1, p2], fill=(255, 255, 255), width=1)

    # Draw control points as green filled circles
    radius = 3
    for idx in control_indices:
        px, py = to_pixel(canonical_2d[idx])
        draw.ellipse(
            [px - radius, py - radius, px + radius, py + radius],
            fill=(0, 255, 0),
        )

    return np.array(img, dtype=np.uint8)


class FaceModelBuilder:
    """Build a canonical face model from a directory of face images.

    Scans a directory for images, detects faces, filters by head pose,
    and computes a weighted average of normalized 3D landmarks. Outputs
    the model dict, a quality report string, and a 512x512 preview image.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {"default": ""}),
            },
            "optional": {
                "yaw_threshold": (
                    "FLOAT",
                    {"default": 45.0, "min": 0.0, "max": 90.0, "step": 1.0},
                ),
                "pitch_threshold": (
                    "FLOAT",
                    {"default": 30.0, "min": 0.0, "max": 90.0, "step": 1.0},
                ),
                "save_path": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("FACE_MODEL", "STRING", "IMAGE")
    RETURN_NAMES = ("face_model", "quality_report", "preview")
    FUNCTION = "build_model"
    CATEGORY = "imgtools/face"

    def build_model(
        self,
        directory: str,
        yaw_threshold: float = 45.0,
        pitch_threshold: float = 30.0,
        save_path: str = "",
    ):
        model_dict, results, actual_save_path = build_face_model(
            directory, yaw_threshold, pitch_threshold, save_path
        )

        # Format quality report
        report = format_quality_report(
            results, actual_save_path, yaw_threshold, pitch_threshold
        )

        # Render preview image
        canonical_2d = model_dict["canonical_landmarks"]
        n_accepted = sum(1 for r in results if r["status"] == "ACCEPTED")
        preview_np = render_preview(
            canonical_2d, MORPH_CONTROL_INDICES, FACE_OVAL_INDICES, n_accepted
        )

        # Convert to ComfyUI IMAGE tensor: [1, H, W, 3] float32
        preview_tensor = torch.from_numpy(
            preview_np.astype(np.float32) / 255.0
        ).unsqueeze(0)

        return (model_dict, report, preview_tensor)
