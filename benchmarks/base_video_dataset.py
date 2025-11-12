from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from videodataset.dataset import BaseVideoDataset

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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


def iter_data(
    data_dir: Path, batch_size: int, num_worker: int, warmup_steps: int, max_steps: int
):
    dataset = CustomDataset(root=data_dir)
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
    throughput = len(dataset.video_keys) * batch_size * train_step / elapsed_time
    logger.info(
        "iter with %d workers, batch_size: %d elapsed: %f seconds, throughput is %f",
        num_worker,
        batch_size,
        elapsed_time,
        throughput,
    )


def main(
    data_dir: Path,
    batch_size: int,
    num_workers: list[int],
    warmup_steps: int,
    max_steps: int,
):
    for num_worker in tqdm(num_workers, desc="iter data (num_workers)"):
        iter_data(
            data_dir=data_dir,
            batch_size=batch_size,
            num_worker=num_worker,
            warmup_steps=warmup_steps,
            max_steps=max_steps,
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
        default=[0, 2, 4, 8, 16],
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
        default=50,
        help="Number of steps",
    )
    args = parser.parse_args()
    main(**vars(args))
