from __future__ import annotations

import torch
from torch import nn


class AdaptiveToyModel(nn.Module):
    """Adaptive linear model that adjusts its dimensions based on input data."""

    def __init__(self, input_dim: int = 0, action_dim: int = 0) -> None:
        super().__init__()
        self.image_keys: list = []

        self.input_dim: int = input_dim
        self.action_dim = action_dim

        self.network = nn.Sequential(
            nn.Linear(self.input_dim, self.action_dim),
        ).cuda()
        self._initialize_weights()

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        if not self.image_keys:
            sample_keys = batch.keys()
            self.image_keys = [
                k for k in sample_keys if k.startswith("observation.images")
            ]

        flat_images = self._flatten_tensors(batch, use_cpu=False)
        flat_images = flat_images[:, : self.input_dim]

        return self.network(flat_images)  # type: ignore

    def _flatten_tensors(
        self,
        batch: dict[str, torch.Tensor],
        use_cpu=True,
    ):
        batch_size = batch[self.image_keys[0]].shape[0]
        tensors = []
        for key in self.image_keys:
            tensor = batch[key]
            tensor = tensor.cpu() if use_cpu else tensor.cuda()
            tensors.append(tensor)
        return torch.cat([t.reshape(batch_size, -1) for t in tensors], dim=1)

    def _initialize_weights(self):
        """Initialize network weights."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)
