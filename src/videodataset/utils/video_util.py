import torch


def nv12_to_rgb(nv12_tensor, width, height):
    nv12_tensor = nv12_tensor.to(dtype=torch.float32)
    y_plane = nv12_tensor[:height, :width]
    uv_plane = (
        nv12_tensor[height : height + height // 2, :]
        .view(height // 2, width // 2, 2)
        .repeat_interleave(2, dim=0)
        .repeat_interleave(2, dim=1)
    )
    u_plane = uv_plane[:, :, 0] - 128
    v_plane = uv_plane[:, :, 1] - 128
    r = y_plane + 1.402 * v_plane
    g = y_plane - 0.344136 * u_plane - 0.714136 * v_plane
    b = y_plane + 1.772 * u_plane
    rgb_tensor = torch.stack((r, g, b), dim=2).clamp(0, 255).byte()
    return rgb_tensor
