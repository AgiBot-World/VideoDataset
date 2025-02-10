from __future__ import annotations

import argparse
import json
import logging
import multiprocessing as mp
import random
import time
from multiprocessing import Process, Queue
from pathlib import Path

from huggingface_hub import snapshot_download
from torch.utils.data import Dataset

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


def worker_process(
    process_id: int,
    repo_id: str,
    local_dir: Path,
    warmup_steps: int,
    max_steps: int,
    result_queue: Queue,
):
    logger.info("Start worker process %d", process_id)

    if repo_id:
        download_dataset(repo_id, local_dir)
    logger.info("Download Data finish %d", process_id)

    dataset = CustomDataset(root=local_dir)

    length = len(dataset)
    random.seed(42)
    indices = list(range(length))
    random.shuffle(indices)

    start_time = None
    end_time = None
    current_step = 0
    try:
        for _ in range(max_steps):
            if current_step == warmup_steps:
                start_time = time.time()
            dataset[indices[current_step]]
            current_step += 1
        end_time = time.time()
    except StopIteration:
        end_time = time.time()

    elapsed_time = end_time - start_time
    train_step = current_step - warmup_steps
    throughput = VIDEO_GOP / 2 * len(dataset.video_keys) * train_step / elapsed_time
    logger.info(
        "iter dataset, elapsed: %f seconds, throughput is %f",
        elapsed_time,
        throughput,
    )
    result_queue.put(
        {
            "process_id": process_id,
            "elapsed_time": elapsed_time,
            "throughput": throughput,
            "train_step": train_step,
        }
    )


def main(
    repo_id: str,
    local_dir: Path,
    warmup_steps: int,
    max_steps: int,
    num_processes: int,
):
    result_queue: Queue[dict] = Queue()
    processes = []
    for i in range(num_processes):
        process = Process(
            target=worker_process,
            args=(i, repo_id, local_dir, warmup_steps, max_steps, result_queue),
        )
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    results = []
    while not result_queue.empty():
        try:
            result = result_queue.get_nowait()
            results.append(result)
        except Exception:
            break

    total_throughput = 0
    for result in results:
        logger.info(
            "process %d elapsed: %f seconds, throughput is %f",
            result["process_id"],
            result["elapsed_time"],
            result["throughput"],
        )
        total_throughput += result["throughput"]
    logging.info("total throughput is %f", total_throughput)


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)

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
    parser.add_argument(
        "--num-processes", type=int, default=4, help="Number of processes"
    )
    args = parser.parse_args()
    main(**vars(args))
