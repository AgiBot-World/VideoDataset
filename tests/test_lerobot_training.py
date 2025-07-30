from __future__ import annotations

import pytest
import torch
from torch import nn
from torch.utils.data import DataLoader

from tests.utils.settings import training_settings


@pytest.mark.parametrize(
    ("dataset_fixture", "dataloader_kwargs"),
    [
        (
            "ucsd_kitchen_video_dataset",
            {
                "num_workers": training_settings.num_workers,
                "multiprocessing_context": "spawn",
            },
        ),
    ],
)
def test_lerobot_fwd_pass(dataset_fixture, dataloader_kwargs, adaptive_model, request):
    """Test the forward pass for both vanilla and video datasets."""
    dataset = request.getfixturevalue(dataset_fixture)
    dataloader = DataLoader(dataset=dataset, batch_size=16, **dataloader_kwargs)

    with torch.no_grad():
        for i, batch in enumerate(dataloader):
            if i > 20:
                break
            predicted_actions = adaptive_model(batch)
            assert predicted_actions.shape[1] == adaptive_model.action_dim


@pytest.mark.parametrize(
    ("dataset_fixture", "dataloader_kwargs"),
    [
        (
            "ucsd_kitchen_video_dataset",
            {
                "num_workers": training_settings.num_workers,
                "multiprocessing_context": "spawn",
            },
        ),
    ],
)
def test_lerobot_training(dataset_fixture, dataloader_kwargs, adaptive_model, request):
    """Test a short training loop to ensure model and data are compatible."""
    num_epochs = 2
    termination_step = training_settings.train_iteration_limit
    dataset = request.getfixturevalue(dataset_fixture)
    dataloader = DataLoader(
        dataset=dataset, batch_size=training_settings.batch_size, **dataloader_kwargs
    )

    model = adaptive_model
    criterion = nn.MSELoss()
    optimizer = None

    model.train()
    steps = 0
    terminated = False
    for epoch in range(num_epochs):
        if terminated:
            break
        for batch_idx, batch in enumerate(dataloader):
            steps += 1
            if optimizer:
                optimizer.zero_grad()

            predicted_actions = model(batch)
            target_actions = model.flattened_action_tensors

            assert predicted_actions.shape == target_actions.shape, (
                f"Action shape mismatch: predicted {predicted_actions.shape}, target {target_actions.shape}"
            )

            loss = criterion(predicted_actions, target_actions)

            loss.backward()

            if optimizer is None:
                optimizer = torch.optim.Adam(model.parameters(), lr=1e-5)

            optimizer.step()

            if batch_idx % 10 == 0:
                print(
                    f"Epoch {epoch + 1}/{num_epochs}, Batch {batch_idx}/{len(dataloader)}, "
                    f"Loss: {loss.item():.6f}"
                )

            if steps == termination_step:
                print(f"Early termination step reached at step {termination_step}")
                terminated = True
                break
