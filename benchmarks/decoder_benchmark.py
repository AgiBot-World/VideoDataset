from __future__ import annotations

import argparse
import logging
import multiprocessing as mp
import time
from multiprocessing import Process, Queue
from pathlib import Path

from videodataset import VideoDecoder

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


VIDEO_GOP = 8


def worker_process(
    process_id: int,
    video_path: Path,
    max_steps: int,
    warmup_steps: int,
    result_queue: Queue,
):
    start_time = None
    end_time = None
    current_step = 0
    decoder = VideoDecoder(0, "h265")
    try:
        for i in range(max_steps):
            if current_step == warmup_steps:
                start_time = time.time()
            decoder.decode_to_np(str(video_path), i)
            current_step += 1
        end_time = time.time()
    except StopIteration:
        end_time = time.time()

    elapsed_time = end_time - start_time
    train_step = current_step - warmup_steps
    throughput = VIDEO_GOP / 2 * train_step / elapsed_time
    logger.info(
        " elapsed: %f seconds, throughput is %f",
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
    video_path: Path,
    max_steps: int,
    warmup_steps: int,
    num_processes: int,
):
    result_queue: Queue[dict] = Queue()
    processes = []
    for i in range(num_processes):
        process = Process(
            target=worker_process,
            args=(i, video_path, max_steps, warmup_steps, result_queue),
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
        "--video-path", type=str, default="", help="Path to the dataset"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=50,
        help="Number of steps",
    )
    parser.add_argument(
        "--warmup-steps",
        type=int,
        default=10,
        help="Number of warmup steps before timing",
    )
    parser.add_argument(
        "--num-processes", type=int, default=4, help="Number of processes"
    )
    args = parser.parse_args()
    main(**vars(args))
