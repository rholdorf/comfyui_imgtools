import math

import torch


def _lanczos_radial(r: torch.Tensor, a: int) -> torch.Tensor:
    """Radial (non-separable) Lanczos kernel: L_a(r) = sinc(r) * sinc(r/a) for r < a."""
    eps = 1e-8
    pi_r = math.pi * r
    pi_r_a = pi_r / a
    sinc1 = torch.where(r < eps, torch.ones_like(r), torch.sin(pi_r) / pi_r)
    sinc2 = torch.where(r < eps, torch.ones_like(r), torch.sin(pi_r_a) / pi_r_a)
    w = sinc1 * sinc2
    return torch.where(r >= a, torch.zeros_like(w), w)


def resize_lanczos_nonseparable(
    image: torch.Tensor,
    target_h: int,
    target_w: int,
    a: int = 3,
) -> torch.Tensor:
    """Resize a ComfyUI image tensor with a non-separable (radial) Lanczos kernel.

    Unlike the separable Lanczos used by PIL/OpenCV (apply L(dx) along X, then L(dy)
    along Y), this evaluates the kernel on the 2D radial distance r = sqrt(dx^2 + dy^2),
    producing a circularly-symmetric filter. Result is sharper and free of the diagonal
    artifacts the separable form introduces — matches Affinity Photo's "Lanczos 3
    (non-separable)" mode.

    Args:
        image: [B, H, W, C] tensor in [0, 1].
        target_h, target_w: output dimensions in pixels.
        a: number of kernel lobes (3 = Lanczos 3).
    """
    if target_h <= 0 or target_w <= 0:
        raise ValueError("target_h and target_w must be positive")

    B, H, W, C = image.shape
    if H == target_h and W == target_w:
        return image

    device = image.device
    work_dtype = torch.float32
    img = image.to(work_dtype).permute(0, 3, 1, 2).contiguous()  # [B, C, H, W]

    scale_y = target_h / H
    scale_x = target_w / W
    # When downscaling, widen the kernel in input-space to band-limit (anti-alias).
    sy = max(1.0, 1.0 / scale_y)
    sx = max(1.0, 1.0 / scale_x)
    rad_y = a * sy
    rad_x = a * sx

    ky = int(math.ceil(rad_y)) * 2 + 1
    kx = int(math.ceil(rad_x)) * 2 + 1

    # Output pixel centers expressed in input coords (pixel-center convention).
    iy_all = (torch.arange(target_h, device=device, dtype=work_dtype) + 0.5) / scale_y - 0.5
    ix_all = (torch.arange(target_w, device=device, dtype=work_dtype) + 0.5) / scale_x - 0.5

    base_x = torch.floor(ix_all).long() - (kx // 2)
    x_offsets = torch.arange(kx, device=device)
    sample_x = base_x.unsqueeze(1) + x_offsets.unsqueeze(0)  # [target_w, kx]
    dx = (sample_x.to(work_dtype) - ix_all.unsqueeze(1)) / sx
    valid_x = (sample_x >= 0) & (sample_x < W)
    sx_clamp = sample_x.clamp(0, W - 1)

    # Chunk output rows so the gathered [B, C, chunk, target_w, ky, kx] tensor stays bounded.
    max_floats = 32 * 1024 * 1024
    elements_per_row = max(1, B * C * target_w * ky * kx)
    chunk_rows = max(1, min(target_h, max_floats // elements_per_row))

    output = torch.empty(B, C, target_h, target_w, dtype=work_dtype, device=device)

    for y_start in range(0, target_h, chunk_rows):
        y_end = min(y_start + chunk_rows, target_h)
        chunk = y_end - y_start

        iy = iy_all[y_start:y_end]
        base_y = torch.floor(iy).long() - (ky // 2)
        y_offsets = torch.arange(ky, device=device)
        sample_y = base_y.unsqueeze(1) + y_offsets.unsqueeze(0)  # [chunk, ky]
        dy = (sample_y.to(work_dtype) - iy.unsqueeze(1)) / sy
        valid_y = (sample_y >= 0) & (sample_y < H)
        sy_clamp = sample_y.clamp(0, H - 1)

        dy_4d = dy.unsqueeze(1).unsqueeze(3)   # [chunk, 1, ky, 1]
        dx_4d = dx.unsqueeze(0).unsqueeze(2)   # [1, target_w, 1, kx]
        r = torch.sqrt(dy_4d * dy_4d + dx_4d * dx_4d)
        w = _lanczos_radial(r, a)              # [chunk, target_w, ky, kx]

        v = valid_y.unsqueeze(1).unsqueeze(3) & valid_x.unsqueeze(0).unsqueeze(2)
        w = w * v.to(work_dtype)
        w_sum = w.sum(dim=(2, 3), keepdim=True)
        w = w / w_sum.clamp_min(1e-12)

        rows = img.index_select(2, sy_clamp.flatten())          # [B, C, chunk*ky, W]
        rows = rows.view(B, C, chunk, ky, W)
        rows = rows.index_select(4, sx_clamp.flatten())         # [B, C, chunk, ky, target_w*kx]
        rows = rows.view(B, C, chunk, ky, target_w, kx)
        rows = rows.permute(0, 1, 2, 4, 3, 5)                   # [B, C, chunk, target_w, ky, kx]

        out_chunk = (rows * w.unsqueeze(0).unsqueeze(0)).sum(dim=(4, 5))
        output[:, :, y_start:y_end, :] = out_chunk

    output = output.clamp(0, 1).permute(0, 2, 3, 1).contiguous()
    return output.to(image.dtype)


class ImageResizeLanczos3NonSeparable:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "max_width": ("INT", {"default": 1024, "min": 1, "max": 16384}),
                "max_height": ("INT", {"default": 1024, "min": 1, "max": 16384}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("image", "width", "height")
    FUNCTION = "resize"
    CATEGORY = "rholdorf/image"

    def resize(self, image, max_width, max_height):
        _, h, w, _ = image.shape
        scale = min(max_width / w, max_height / h)
        if scale >= 1.0:
            return (image, w, h)
        target_w = max(1, round(w * scale))
        target_h = max(1, round(h * scale))
        out = resize_lanczos_nonseparable(image, target_h, target_w, a=3)
        return (out, target_w, target_h)
