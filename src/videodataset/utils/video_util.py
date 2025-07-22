from __future__ import annotations

import torch


def nv12_to_rgb(nv12_tensor: torch.Tensor, width: int, height: int) -> torch.Tensor:
    """Convert NV12 format tensor to RGB format.

    Args:
        nv12_tensor (torch.Tensor): Tensor in NV12 format.
        width (int): Width of the tensor.
        height (int): Height of the tensor.

    Returns:
        torch.Tensor: Tensor in RGB format.
    """
    nv12_tensor_f = nv12_tensor.to(dtype=torch.float32)

    # Extract Y and UV components
    y_plane = nv12_tensor_f[:height, :width]
    uv_plane = nv12_tensor_f[height:, :].contiguous().view(height // 2, width // 2, 2)

    # Repeat UV components to match Y plane dimensions
    uv_plane_upsampled = (
        uv_plane.repeat_interleave(2, dim=0).repeat_interleave(2, dim=1).contiguous()
    )
    u_plane = uv_plane_upsampled[:, :, 0]
    v_plane = uv_plane_upsampled[:, :, 1]

    # Apply NV12 to RGB conversion formulas
    r = 1.164 * y_plane + 1.596 * v_plane - 222.921
    g = 1.164 * y_plane - 0.392 * u_plane - 0.813 * v_plane + 135.576
    b = 1.164 * y_plane + 2.018 * u_plane - 276.836

    # Stack and clamp the RGB channels
    return torch.stack((r, g, b), dim=2).clamp(0, 255).byte()
