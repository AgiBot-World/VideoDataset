from __future__ import annotations

import argparse
import logging
import multiprocessing as mp
import time
from multiprocessing import Process, Queue
from pathlib import Path

import cv2
import torchvision
from torchcodec.decoders import VideoDecoder as CodecDecoder

from videodataset import VideoDecoder

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


VIDEO_GOP = 8


def cv2_decoder_process(
    process_id: int,
    video_path: Path,
    max_steps: int,
    warmup_steps: int,
    result_queue: Queue,
):
    start_time = None
    end_time = None
    current_step = 0
    try:
        for i in range(max_steps):
            if current_step == warmup_steps:
                start_time = time.time()
            cap = cv2.VideoCapture(str(video_path))
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            current_frame_index = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

            while current_frame_index < i:
                cap.grab()
                current_frame_index += 1
            cap.retrieve()
            cap.release()
            current_step += 1
        end_time = time.time()
    except StopIteration:
        end_time = time.time()

    elapsed_time = end_time - start_time
    train_step = current_step - warmup_steps
    throughput = train_step / elapsed_time
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


def torchcodec_decoder_process(
    process_id: int,
    video_path: Path,
    max_steps: int,
    warmup_steps: int,
    result_queue: Queue,
    device: str = "cpu",
):
    start_time = None
    end_time = None
    current_step = 0
    try:
        for i in range(max_steps):
            if current_step == warmup_steps:
                start_time = time.time()
            video_path = str(video_path)
            if device == "cuda":
                decoder = CodecDecoder(
                    video_path, seek_mode="approximate", device="cuda"
                )
            else:
                decoder = CodecDecoder(video_path, seek_mode="approximate")
            decoder.get_frames_at(indices=[i])
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


def torchvision_decoder_process(
    process_id: int,
    video_path: Path,
    max_steps: int,
    warmup_steps: int,
    result_queue: Queue,
    backend: str = "pyav",
):
    start_time = None
    end_time = None
    current_step = 0

    torchvision.set_video_backend(backend)
    fps = 30.0
    try:
        for i in range(max_steps):
            if current_step == warmup_steps:
                start_time = time.time()
            target_time_sec = i / fps
            reader = torchvision.io.VideoReader(str(video_path), "video")
            if backend == "pyav":
                reader.seek(target_time_sec, keyframes_only=True)
            else:
                reader.seek(target_time_sec)
            for frame in reader:
                current_pts = frame["pts"]
                current_frame_idx_approx = int(current_pts * fps)
                if current_frame_idx_approx >= i:
                    break
            if backend == "pyav":
                reader.container.close()
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


def videodataset_process(
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
    decoder: str,
):
    result_queue: Queue[dict] = Queue()
    processes = []
    for i in range(num_processes):
        if decoder == "videodataset":
            process = Process(
                target=videodataset_process,
                args=(i, video_path, max_steps, warmup_steps, result_queue),
            )
        elif decoder == "pyav":
            process = Process(
                target=torchvision_decoder_process,
                args=(i, video_path, max_steps, warmup_steps, result_queue, "pyav"),
            )
        elif decoder == "video_reader":
            process = Process(
                target=torchvision_decoder_process,
                args=(
                    i,
                    video_path,
                    max_steps,
                    warmup_steps,
                    result_queue,
                    "video_reader",
                ),
            )
        elif decoder == "torchcodec_cpu":
            process = Process(
                target=torchcodec_decoder_process,
                args=(
                    i,
                    video_path,
                    max_steps,
                    warmup_steps,
                    result_queue,
                    "cpu",
                ),
            )
        elif decoder == "torchcodec_cuda":
            process = Process(
                target=torchcodec_decoder_process,
                args=(
                    i,
                    video_path,
                    max_steps,
                    warmup_steps,
                    result_queue,
                    "cuda",
                ),
            )
        elif decoder == "cv2":
            process = Process(
                target=cv2_decoder_process,
                args=(
                    i,
                    video_path,
                    max_steps,
                    warmup_steps,
                    result_queue,
                ),
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
    parser.add_argument(
        "--decoder", type=str, default="videodataset", help="Decoder to use"
    )

    args = parser.parse_args()
    main(**vars(args))
