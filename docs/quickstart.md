# Quickstart

## Prerequisites

- NVIDIA GPU with CUDA support and CUDA Toolkit 12.0+ installed
- FFmpeg installed
- Python 3.10 or later

## Installation

### Install from PyPI

```bash
pip install agibot-videodataset
```

### Building from Source

```bash
pip install git+https://github.com/AgiBot-World/VideoDataset.git
```

> Note: If there is no available network to access to github, please add a proxy mirror to the environment variable `GITHUB_PROXY`.

## Data Preparation

There are no specific requirements for the data organization format and it can follow the LeRobotDataset format or any other custom structure.

### Video Transcoding

To achieve high-performance decoding and precise frame-seeking, the videos must be transcoded. Here is an example of video transcoding using FFmpeg:

```bash
ffmpeg -i input.mp4 -r 30 -c:v libx265  -crf 24 -g 8 -keyint_min 8 -sc_threshold 0 -vf "setpts=N/(30*TB)" -bf 0 -c:a copy output.mp4
```

#### Key parameter explanation

- `-g 8​:` Sets the keyframe (I-frame) interval to 8 frames
- `-sc_threshold 0​​:` Disables automatic keyframe insertion at scene changes
- `-vf "setpts=N/(30*TB)"​:`  Synchronize the video to a 30 fps timeline
- `-bf 0​:` Sets the number of bidirectional frames (B-frames) to 0
- `-c:v libx265​:` Selects the H.265/HEVC video encoder (libx265) for compression

> Note: Since `BaseVideoDataset` uses the Nvidia Codec SDK for decoding, it is essential to ensure that the selected video codec is supported by the GPU on the machine. For specific details, please refer to the official NVIDIA documentation: [Video Encode and Decode Support Matrix](https://developer.nvidia.com/video-encode-decode-support-matrix)

## Quickstart with VideoDataset

### Creating Custom Dataset with BaseVideoDataset

To get started quickly, first install the package. Then, you can utilize the `BaseVideoDataset` mixin class for `torch.utils.data.Dataset` to handle your custom data, as long as the __getitem__ method can correctly determine which videos and which frames to parse.

The following example demonstrates this using the LeRobotDataset format:

```python
import argparse
import json
import logging

from huggingface_hub import snapshot_download
from pathlib import Path
from torch.utils.data import DataLoader, Dataset

from videodataset.dataset import BaseVideoDataset

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MyDataset(Dataset, BaseVideoDataset):

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

            # Key Point 1: Initialize the decoder, specifying an efficient video codec (e.g., HEVC)
            decoder = self.get_decoder(decoder_key=video_key, codec="hevc")
            video_path = self.root / "videos" / video_key / "chunk-000" / "file-000.mp4"

            # Key Point 2: Decode the specified frame
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

def main(repo_id: str, local_dir: Path, batch_size: int, num_workers: int):

    if repo_id:
        download_dataset(repo_id, local_dir)

    dataset = MyDataset(root=local_dir)

    # Key Point 3: Using 'multiprocessing_context="spawn"' when num_workers > 0
    dataloader = DataLoader(dataset, batch_size=batch_size, num_workers=num_workers, multiprocessing_context="spawn", )

    for epoch in range(2):
        for batch_idx, batch_data in enumerate(dataloader):
            logger.info(f"Epoch {epoch} Batch {batch_idx}: {batch_data}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="BaseVideoDataset Example")
    parser.add_argument("--repo-id", type=str, default="AgiBotWorldAdmin/videodataset-benchmark", help="repo of the dataset")
    parser.add_argument("--local-dir", type=str, default="./AgiBotWorldAdmin/videodataset-benchmark", help="path to the dataset")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size for data loading")
    parser.add_argument("--num-workers", type=int, default=4, help="Number of Data Loading Workers",)

    args = parser.parse_args()
    main(**vars(args))
```

For more examples, see the [tests directory](https://github.com/AgiBot-World/VideoDataset/-/tree/main/tests).
