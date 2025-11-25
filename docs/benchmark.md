# Benchmark

## 1. Overview

This document provides a comprehensive performance benchmark for `VideoDataset`, a high-efficiency video decoding backend. The `VideoDataset` is designed to be used by creating a custom dataset class that inherits from `BaseVideoDataset`, enabling efficient video data decoding. This document presents a comprehensive performance benchmark analyzing this approach across multiple metrics to quantify its characteristics.

## 2. Prerequisites

### 2.1 Benchmark Environment

To ensure reproducible and fair results, all tests were conducted in the following fixed environment:

| Component | Specification |
| :--- | :--- |
| **Hardware** | - **CPU:** Intel(R) Xeon(R) Platinum 8468 |
| | - **GPU:**  NVIDIA H100 SXM5 80GB |
| | - **GPU Num** 8 |
| **Software** | - **OS:** Ubuntu 24.04.3 LTS |
| | - **Python:** 3.12.3 |
| | - **PyTorch:** 2.7.0a0+79aa17489c.nv25.4 |
| | - **CUDA:** 12.9 |
| | - **Driver Version:** 560.35.03 |

>Note: The Docker image used for running the benchmark will be released later.

### 2.2 Video Transcoding Preparation

Since the H100 GPU cannot decode AV1 videos, all test videos were pre-transcoded to H.265 (HEVC) format using the following command:

```bash
ffmpeg -i input.mp4 -r 30 -c:v libx265  -crf 24 -g 8 -keyint_min 8 -sc_threshold 0 -vf "setpts=N/(30*TB)" -bf 0 -c:a copy output.mp4
```

>Note: The test data required to run the benchmark has been uploaded to Hugging Face: [AgiBotWorldAdmin/videodataset-benchmark](https://huggingface.co/datasets/AgiBotWorldAdmin/videodataset-benchmark/tree/main)

## 3. Benchmark

### 3.1 Metrics

- **Video Decoding Throughput:**<br>

This metric measures the decoding capability of `VideoDecoder`, expressed in frames per second (FPS), representing the maximum theoretical throughput achievable by the hardware when isolated from dataset operations.

- **Single-GPU Random Access Dataset Throughput:**<br>

This metric evaluates the random access throughput​ of the `BaseVideoDataset` under multi-process loading on a single GPU. It tests how efficiently the dataset infrastructure can serve random samples.

- **DataLoader Throughput:**<br>

This measures the efficiency of PyTorch's DataLoader with `BaseVideoDataset` across different `num_workers` configurations on a single GPU. It helps identify the optimal worker count for maximizing data loading performance and reveals bottlenecks in the data loading pipeline.

- **Multi-GPU Data Loading Throughput:**<br>

This metric evaluates how the data loading performance scales across multiple GPUs, . It's essential for understanding multi-GPU training efficiency and identifying potential scaling limitations.

>Note: Since the video encoding uses a GOP size of 8, the decoder's expected actual decoding workload for each output video frame is equivalent to 4 frames. Therefore, when calculating throughput, the count of effectively decoded frames is multiplied by 4.

### 3.2 Execution

### 3.2.1 Video Decoding Throughput

You can ​measure​ the `Video Decoding Throughput` metric by running the `benchmarks/decoder_benchmark.py` file.

```bash

python benchmarks/decoder_benchmark.py --video-path AgiBotWorldAdmin/videodataset-benchmark/videos/observation.images.top_head/chunk-000/file-000.mp4 --num-processes 4

```

#### **Parameters**

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **`--video-path`** | `AgiBotWorldAdmin/videodataset-benchmark/videos/observation.images.top_head/chunk-000/file-000.mp4` | Video file path |
| **`--max-steps`** | `1000` | Maximum iteration steps|
| **`--warmup-steps`** | `10` | Number of warmup steps before timing|
| **`--num-processes`** | `4` | Number of processes|

### 3.2.2 Single-GPU Random Access Dataset Throughput

You can ​measure​ this metric by running the `benchmarks/dataset_benchmark.py` file.

```bash

python benchmarks/dataset_benchmark.py --repo-id AgiBotWorldAdmin/videodataset-benchmark --num-processes 8

```

#### **Parameters**

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **`--repo-id`** | `AgiBotWorldAdmin/videodataset-benchmark` | Repo of the dataset |
| **`--local-dir`** | `./AgiBotWorldAdmin/videodataset-benchmark` | Local dataset path |
| **`--warmup-steps`** | `10` | Number of warmup steps before timing|
| **`--max-steps`** | `1000` | Maximum iteration steps|
| **`--num-processes`** | `4` | Number of processes|

### 3.2.3 DataLoader Throughput

You can ​measure​ this metric by running the `benchmarks/base_video_dataset.py` file.

```bash

python benchmarks/base_video_dataset.py --repo-id AgiBotWorldAdmin/videodataset-benchmark --num-workers 8 16 32

```

#### **Parameters**

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **`--repo-id`** | `AgiBotWorldAdmin/videodataset-benchmark` | Repo of the dataset |
| **`--local-dir`** | `./AgiBotWorldAdmin/videodataset-benchmark` | Local dataset path |
| **`--num-workers`** | `8` | Number of Data Loading Workers |
| **`--batch-size`** | `16` | Batch size for data loading |
| **`--warmup-steps`** | `10` | Number of warmup steps before timing|
| **`--max-steps`** | `1000` | Maximum iteration steps|
| **`--world-size`** | `1` | Total number of processes in distributed training|

### 3.2.4 Multi-GPU Data Loading Throughput

You can ​measure​ this metric by running the `benchmarks/base_video_dataset.py` file.

```bash

python benchmarks/base_video_dataset.py --repo-id AgiBotWorldAdmin/videodataset-benchmark --num-workers 8 --world-size 2

```

#### **Parameters**

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **`--repo-id`** | `AgiBotWorldAdmin/videodataset-benchmark` | Repo of the dataset |
| **`--local-dir`** | `./AgiBotWorldAdmin/videodataset-benchmark` | Local dataset path |
| **`--num-workers`** | `8` | Number of Data Loading Workers |
| **`--batch-size`** | `16` | Batch size for data loading |
| **`--warmup-steps`** | `10` | Number of warmup steps before timing|
| **`--max-steps`** | `1000` | Maximum iteration steps|
| **`--world-size`** | `1` | Total number of processes in distributed training|

### 3.3 Results

> Note: All the following results were obtained with `MPS` enabled. Ensure `MPS` is enabled before executing the benchmark.

#### 3.3.1 Video Decoding Throughput

We ran the benchmark with the following parameters:

```bash

python benchmarks/decoder_benchmark.py \
    --video-path AgiBotWorldAdmin/videodataset-benchmark/videos/observation.images.top_head/chunk-000/file-000.mp4 \
    --num-processes 8 \
    --warmup-steps 10 \
    --max-steps 1000
```

This table show the results:

| num-processes | throughput (FPS)  | GPU Video Decoder Utilization |
| ---------:    | ----------:       | ----------:                   |
| 8             | 8249.6676         | >=30%                         |
| 16            | 15285.96          | >=60%                         |
| 32            | 22070.7748        | >=90%                         |

#### 3.3.2 Single-GPU Random Access Dataset Throughput

We ran the benchmark with the following parameters:

```bash

python benchmarks/dataset_benchmark.py \
    --repo-id AgiBotWorldAdmin/videodataset-benchmark \
    --num-processes 8 \
    --warmup-steps 10 \
    --max-steps 1000
```

This table show the results:

| num-processes | throughput (FPS)  | GPU Video Decoder Utilization |
| ---------:    | ----------:       | ----------:                   |
| 8             | 8286.304          | >=30%                         |
| 16            | 14999.516         | >=60%                         |
| 32            | 22010.9956        | >=85%                         |

#### 3.3.3 DataLoader Throughput

We ran the benchmark with the following parameters:

```bash

python benchmarks/base_video_dataset.py \
    --repo-id AgiBotWorldAdmin/videodataset-benchmark \
    --num-workers 8 \
    --batch-size 16 \
    --warmup-steps 10 \
    --max-steps 1000 \
    --world-size 1
```

This table show the results:

| num_workers   | throughput (FPS)  | GPU Video Decoder Utilization |
| ---------:    | ----------:       | ----------:                   |
| 8             | 8011.246          | >=30%                         |
| 16            | 14798.5004        | >=60%                         |
| 32            | 18447.408         | >=80%                         |

#### 3.3.4 Multi-GPU Data Loading Throughput

We ran the benchmark with the following parameters:

```bash

python benchmarks/base_video_dataset.py \
    --repo-id AgiBotWorldAdmin/videodataset-benchmark \
    --num-workers 8 \
    --batch-size 16 \
    --warmup-steps 10 \
    --max-steps 1000 \
    --world-size 1
```

This table show the results:

| world-size   |  Total throughput (FPS)    | Single-GPU throughput (FPS)   |
| ---------:    | ----------:               | ----------:                   |
| 1             | 8004.196                  | 8004.196                      |
| 2             | 14232.9596                | 7116.4796                     |
| 4             | 25621.792                 | 6405.448                      |
| 8             | 42172.896                 | 5271.612                      |
