from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path

import torch
import torch.distributed as dist
import torch.multiprocessing as mp
from huggingface_hub import snapshot_download
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from videodataset.dataset import BaseVideoDataset

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


VIDEO_GOP = 8


class CustomDataset(Dataset, BaseVideoDataset):
    def __init__(
        self,
        root: Path,
    ):
        Dataset.__init__(self)
        BaseVideoDataset.__init__(self)
        self.root = Path(root)

        meta_file = self.root / "meta" / "info.json"
        with meta_file.open() as f:
            self.meta = json.load(f)
        self.total_frames = self.meta.get("total_frames", 0)
        features = self.meta.get("features").keys()
        self.video_keys = [
            key for key in features if key.startswith("observation.images")
        ]

    def __len__(self):
        return self.total_frames

    def __getitem__(self, idx) -> dict:
        data = {}
        for video_key in self.video_keys:
            decoder = self.get_decoder(decoder_key=video_key, codec="hevc")
            video_path = self.root / "videos" / video_key / "chunk-000" / "file-000.mp4"
            frame = self.decode_video_frame(
                decoder=decoder, video_path=video_path, frame_idx=idx
            )
            data[video_key] = frame
        return data


def download_dataset(repo_id: str, local_dir: Path):
    snapshot_download(
        repo_id,
        repo_type="dataset",
        local_dir=local_dir,
    )


def init_group(rank, world_size):
    os.environ["MASTER_ADDR"] = "localhost"
    os.environ["MASTER_PORT"] = "12355"
    torch.cuda.set_device(rank)
    dist.init_process_group("nccl", rank=rank, world_size=world_size)


def iter_data(
    rank,
    world_size,
    repo_id: str,
    local_dir: Path,
    batch_size: int,
    num_worker: int,
    warmup_steps: int,
    max_steps: int,
):
    init_group(rank, world_size)
    if repo_id:
        download_dataset(repo_id, local_dir)
    dataset = CustomDataset(root=local_dir)
    dataloader: DataLoader[CustomDataset]

    if num_worker == 0:
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            num_workers=num_worker,
        )
    else:
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            num_workers=num_worker,
            multiprocessing_context="spawn",
        )

    start_time = None
    end_time = None
    current_step = 0
    try:
        dataloader_iter = iter(dataloader)

        for _ in range(max_steps):
            if current_step == warmup_steps:
                start_time = time.time()

            next(dataloader_iter)
            current_step += 1
        end_time = time.time()
    except StopIteration:
        end_time = time.time()

    elapsed_time = end_time - start_time
    train_step = current_step - warmup_steps
    throughput = (
        VIDEO_GOP / 2 * len(dataset.video_keys) * batch_size * train_step / elapsed_time
    )
    logger.info(
        "iter with %d workers, batch_size: %d elapsed: %f seconds, throughput is %f",
        num_worker,
        batch_size,
        elapsed_time,
        throughput,
    )
    dist.destroy_process_group()


def main(
    repo_id: str,
    local_dir: Path,
    batch_size: int,
    num_workers: list[int],
    world_size: int,
    warmup_steps: int,
    max_steps: int,
):
    mp.set_start_method("spawn", force=True)

    if world_size < 0:
        world_size = torch.cuda.device_count()
    logger.info("world size: %d", world_size)

    for num_worker in tqdm(num_workers, desc="iter data (num_workers)"):
        mp.spawn(
            iter_data,
            args=(
                world_size,
                repo_id,
                local_dir,
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

    parser.add_argument(
        "--repo-id",
        type=str,
        default="AgiBotWorldAdmin/videodataset-benchmark",
        help="repo of the dataset",
    )
    parser.add_argument(
        "--local-dir",
        type=str,
        default="./AgiBotWorldAdmin/videodataset-benchmark",
        help="path to the dataset",
    )
    parser.add_argument(
        "--batch-size", type=int, default=16, help="Batch size for data loading"
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        nargs="*",
        default=[0, 2, 4, 8, 16],
        help="Number of Data Loading Workers",
    )
    parser.add_argument(
        "--world-size",
        type=int,
        default=1,
        help="Total number of processes in distributed training",
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
        default=50,
        help="Number of steps",
    )
    args = parser.parse_args()
    main(**vars(args))
