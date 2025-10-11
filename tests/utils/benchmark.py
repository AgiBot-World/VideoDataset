from __future__ import annotations

import argparse
import logging
import os
import time

import torch
import torch.distributed as dist
import torch.multiprocessing as mp
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data import DataLoader
from torchvision import transforms

from tests.utils.model import AdaptiveToyModel
from videodataset.dataset.lerobot_dataset import LeRobotVideoDataset

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


data_cls_map = {
    "LeRobotDataset": LeRobotDataset,
    "LeRobotVideoDataset": LeRobotVideoDataset,
}


def train(
    rank,
    world_size,
    data,
    dataset_cls,
    batch_size,
    num_workers,
    warmup_steps,
):
    os.environ["MASTER_ADDR"] = "localhost"
    os.environ["MASTER_PORT"] = "12355"
    torch.cuda.set_device(rank)
    dist.init_process_group("nccl", rank=rank, world_size=world_size)

    image_transforms = transforms.Compose(
        [
            transforms.Resize((256, 256)),
        ]
    )

    dataset = dataset_cls(
        repo_id=None,
        root=data,
        image_transforms=image_transforms,
    )

    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        num_workers=num_workers,
        multiprocessing_context="spawn",
    )

    model = AdaptiveToyModel(input_dim=1572919, action_dim=14)
    model = model.to(rank)
    model = DistributedDataParallel(model, device_ids=[rank])

    optimizer = torch.optim.Adam(model.parameters())
    start_time = None
    end_time = None
    current_step = 0
    try:
        dataloader_iter = iter(dataloader)
        for _ in range(500):
            if current_step == warmup_steps:
                start_time = time.time()

            batch_data = next(dataloader_iter)
            outputs = model(batch_data)
            loss = outputs.mean()
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            if current_step % 50 == 0:
                logger.info("Step %d", current_step)
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
            num_workers,
            batch_size,
            elapsed_time,
            throughput,
        )

    dist.destroy_process_group()


def main(data, dataset_cls, batch_size, num_workers, warmup_steps):
    mp.set_start_method("spawn", force=True)

    world_size = torch.cuda.device_count()
    logger.info("world size: %d", world_size)

    mp.spawn(
        train,
        args=(
            world_size,
            data,
            dataset_cls,
            batch_size,
            num_workers,
            warmup_steps,
        ),
        nprocs=world_size,
        join=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video Dataset Performance Benchmark")

    # Benchmark parameters
    parser.add_argument("--data", type=str, default="", help="Path to the dataset")
    parser.add_argument(
        "--data-type",
        type=str,
        default="LeRobotVideoDataset",
        choices=["LeRobotVideoDataset", "LeRobotDataset"],
        help="Dataset type (LeRobotVideoDataset or LeRobotDataset)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=16, help="Batch size for data loading"
    )
    parser.add_argument(
        "--num-workers", type=int, default=8, help="Number of Data Loading Workers"
    )
    parser.add_argument(
        "--warmup-steps",
        type=int,
        default=10,
        help="Number of warmup steps before timing",
    )
    args = parser.parse_args()

    dataset_cls = data_cls_map.get(args.data_type)
    main(args.data, dataset_cls, args.batch_size, args.num_workers, args.warmup_steps)
