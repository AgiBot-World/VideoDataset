from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path

import torch
import torch.distributed as dist
import torch.multiprocessing as mp
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from torch import nn
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data import DataLoader
from torchvision import transforms
from tqdm import tqdm

from videodataset.dataset.lerobot_dataset import LeRobotVideoDataset

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


data_cls_map = {
    "LeRobotDataset": LeRobotDataset,
    "LeRobotVideoDataset": LeRobotVideoDataset,
}


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


def init_group(rank, world_size):
    os.environ["MASTER_ADDR"] = "localhost"
    os.environ["MASTER_PORT"] = "12355"
    torch.cuda.set_device(rank)
    dist.init_process_group("nccl", rank=rank, world_size=world_size)


def init_dataloader(data_dir, dataset_cls, batch_size, num_worker):
    image_transforms = transforms.Compose(
        [
            transforms.Resize((256, 256)),
        ]
    )
    dataset = dataset_cls(
        repo_id=None,
        root=data_dir,
        image_transforms=image_transforms,
    )
    if num_worker > 0:
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            num_workers=num_worker,
            multiprocessing_context="spawn",
        )
    else:
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            num_workers=num_worker,
        )
    return dataloader


def init_model(rank):
    model = AdaptiveToyModel(input_dim=256 * 256 * 3, action_dim=2)
    model = model.to(rank)
    return DistributedDataParallel(model, device_ids=[rank])


def train(
    rank,
    world_size,
    data_dir,
    dataset_cls,
    batch_size,
    num_worker,
    warmup_steps,
    max_steps,
):
    init_group(rank, world_size)

    dataset_cls = data_cls_map.get(dataset_cls)
    dataloader = init_dataloader(data_dir, dataset_cls, batch_size, num_worker)
    model = init_model(rank)

    optimizer = torch.optim.Adam(model.parameters())
    start_time = None
    end_time = None
    current_step = 0
    try:
        dataloader_iter = iter(dataloader)
        for _ in tqdm(range(max_steps), desc="iter train (steps)", miniters=50):
            if current_step == warmup_steps:
                start_time = time.time()
            batch_data = next(dataloader_iter)
            outputs = model(batch_data)
            loss = outputs.mean()
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            current_step += 1
        dist.barrier()
        end_time = time.time()
    except StopIteration:
        dist.barrier()
        end_time = time.time()
        logger.info("Train stop at step %d", current_step)
    except Exception as e:
        logger.info("Train error at step %d, %s", current_step, str(e))

    elapsed_time = end_time - start_time
    train_step = current_step - warmup_steps
    throughput = batch_size * train_step / elapsed_time

    if rank == 0:
        logger.info(
            "%s with %d workers, batch_size: %d elapsed: %f seconds, throughput is %f",
            dataset_cls.__name__,
            num_worker,
            batch_size,
            elapsed_time,
            throughput,
        )

    dist.destroy_process_group()


def main(
    data_dir: Path,
    batch_size: int,
    num_workers: list[int],
    warmup_steps: int,
    max_steps: int,
):
    mp.set_start_method("spawn", force=True)

    world_size = torch.cuda.device_count()
    logger.info("world size: %d", world_size)

    for num_worker in tqdm(num_workers, desc="iter train (num_workers)"):
        for dataset_cls in tqdm(data_cls_map, desc="iter train(dataset)"):
            mp.spawn(
                train,
                args=(
                    world_size,
                    data_dir,
                    dataset_cls,
                    batch_size,
                    num_worker,
                    warmup_steps,
                    max_steps,
                ),
                nprocs=world_size,
                join=True,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video Dataset Performance Benchmark")

    parser.add_argument("--data-dir", type=str, default="", help="Path to the dataset")
    parser.add_argument(
        "--batch-size", type=int, default=16, help="Batch size for data loading"
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        nargs="*",
        default=[0, 2, 4, 8, 10, 12, 14, 16],
        help="Number of Data Loading Workers",
    )
    parser.add_argument(
        "--warmup-steps",
        type=int,
        default=10,
        help="Number of warmup steps before timing",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=500,
        help="Number of steps",
    )

    args = parser.parse_args()
    main(**vars(args))
