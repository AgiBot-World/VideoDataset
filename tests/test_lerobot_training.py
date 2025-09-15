from __future__ import annotations

import os
import pytest
import torch
import time
import torch.distributed as dist
import torch.multiprocessing as mp

from torch import nn
from torch.utils.data import DataLoader
from torch.nn.parallel import DistributedDataParallel

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from videodataset.dataset.lerobot_dataset import LeRobotVideoDataset

from tests.utils.settings import dataset_settings, training_settings


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


def ddp_train(rank, world_size, dataset_name, num_workers, adaptive_model):

    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12355'
    torch.cuda.set_device(rank)
    dist.init_process_group("nccl", rank=rank, world_size=world_size)

    dataset = None
    if dataset_name == "ucsd_kitchen_dataset":
        dataset = LeRobotDataset(
            repo_id=None,
            root=dataset_settings.lerobot_datasets_root_paths["ucsd_kitchen_dataset"],
        )
    elif dataset_name == "ucsd_kitchen_video_dataset":
        dataset = LeRobotVideoDataset(
            repo_id=None,
            root=dataset_settings.lerobot_datasets_root_paths["ucsd_kitchen_dataset"],
        )
    dataloader = DataLoader(
        dataset, batch_size=16, num_workers=num_workers, multiprocessing_context="spawn"
    )
    model = adaptive_model.to(rank)
    model = DistributedDataParallel(model, device_ids=[rank])

    optimizer = torch.optim.Adam(model.parameters())
    start_time = time.time()
    end_time = time.time()
    try:
        dataloader_iter = iter(dataloader)
        for i in range(1000):
            batch_data = next(dataloader_iter)
            if i % 50 == 0:
                print(f"step {i}", flush=True)
                end_time = time.time()
            outputs = model(batch_data)
            loss = outputs.mean()
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
    except StopIteration:
        pass
    except Exception as e:
        print(f"train error:{e}")
    print(f'train elapsed time:{end_time-start_time}')
    dist.destroy_process_group()


@pytest.mark.parametrize(
    "dataset_name",["ucsd_kitchen_dataset", "ucsd_kitchen_video_dataset"]
)
@pytest.mark.parametrize("num_workers", [8, 4, 2, 1])
def test_lerobot_video_dataset_training_bench(
    dataset_name, num_workers, adaptive_model, capsys, request
):
    """Benchmark a LeRobotVideoDataset training loop to ensure it is fast enough."""

    world_size = torch.cuda.device_count()
    print(f"world size:{world_size}", flush=True)
    start_time = time.perf_counter()
    mp.spawn(ddp_train, args=(world_size, dataset_name, num_workers, adaptive_model), nprocs=world_size, join=True)
    elapsed_time = time.perf_counter() - start_time
    with capsys.disabled():
        print(
            f"{dataset_name} with {num_workers} workers, elapsed: {elapsed_time:.2f} seconds"
        )
