from __future__ import annotations

import torch
from torch import nn
import torch.distributed as dist


class AdaptiveToyModel(nn.Module):
    """Adaptive linear model that adjusts its dimensions based on input data."""

    def __init__(self, hidden_dim: int = 2) -> None:
        super().__init__()
        self.image_keys: list[str] = []
        self.state_keys: list[str] = []
        self.action_keys: list[str] = []
        self.hidden_dim = hidden_dim
        self.flattened_action_tensors: torch.Tensor | None = None
        self._is_batched: bool = False
        self.input_dim: int = 921621
        self.action_dim: int = 8
        self.network = nn.Sequential(
            nn.Linear(self.input_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(self.hidden_dim // 2, self.action_dim),
        ).cuda()
        self.initial = False

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """Forward pass with lazy initialization of the network."""
        if not self.initial:
            self._initialize_network_from_batch(batch)
            self.initial = True

        self._is_batched = batch[self.image_keys[0]].ndim == 4
        # Assume uniform batch size across all fields
        batch_size = batch[self.image_keys[0]].shape[0] if self._is_batched else 1

        flat_images = self._prep_and_flatten_tensors(
            batch, self.image_keys, batch_size, use_cpu=False
        )
        flat_states = self._prep_and_flatten_tensors(
            batch, self.state_keys, batch_size, use_cpu=False
        )

        self.flattened_action_tensors = self._prep_and_flatten_tensors(
            batch, self.action_keys, batch_size, use_cpu=False
        )

        concatenated_input = torch.cat([flat_images, flat_states], dim=1)
        return self.network(concatenated_input)  # type: ignore

    def _initialize_network_from_batch(self, batch: dict[str, torch.Tensor]):
        """Defines network dimensions and layers from the first batch."""
        sample_keys = batch.keys()
        self.image_keys = [k for k in sample_keys if k.startswith("observation.images")]
        self.state_keys = [k for k in sample_keys if k.startswith("observation.state")]
        self.action_keys = [
            k for k in sample_keys if k.startswith(("action", "observations.actions"))
        ]

        # Temporarily process a batch to infer dimensions
        self._is_batched = batch[self.image_keys[0]].ndim == 4

        batch_size = batch[self.image_keys[0]].shape[0] if self._is_batched else 1
        image_dim = self._get_dim(batch, batch_size, self.image_keys)
        state_dim = self._get_dim(batch, batch_size, self.state_keys)
        self.input_dim = image_dim + state_dim

        self.action_dim = self._get_dim(batch, batch_size, self.action_keys)
        self._initialize_weights()

    def _get_dim(
        self, batch: dict[str, torch.Tensor], batch_size: int, keys: list[str]
    ) -> int:
        corresponding_tensors = [batch[k] for k in keys]
        assert all(isinstance(item, torch.Tensor) for item in corresponding_tensors), (
            "Image, state, or action items must be tensors"
        )
        total_elements_per_tensor = [item.numel() for item in corresponding_tensors]
        return int(sum(total_elements_per_tensor) / batch_size)

    def _prep_and_flatten_tensors(
        self,
        batch: dict[str, torch.Tensor],
        keys: list[str],
        batch_size: int,
        use_cpu=True,
    ):
        tensors = []
        for key in keys:
            tensor = batch[key]
            if use_cpu:
                tensor = tensor.cpu()
            else:
                tensor = tensor.cuda()
            tensors.append(tensor)
        return torch.cat([t.reshape(batch_size, -1) for t in tensors], dim=1)

    def _initialize_weights(self):
        """Initialize network weights."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)
