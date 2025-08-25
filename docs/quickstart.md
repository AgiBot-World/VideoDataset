# Quickstart

## Prerequisites

- NVIDIA GPU with CUDA support and CUDA Toolkit installed
  - CUDA Toolkit 12.0 or later
- FFmpeg installed

## Installation

### Install from PyPI index

```bash
export PIP_INDEX_URL=https://nexus.infra.agibot.com/repository/pypi-proxy/simple
pip install videodataset
```

### Building from Source

```bash
pip install . git+https://code.agibot.com/ai-platform/videodataset.git@main
```

> Note: If there is no available network to access to github, please add a proxy mirror to the environment variable `GITHUB_PROXY`.

## Quickstart with VideoDataset

VideoDataset provides two main usage patterns:

### Mixin class with torch.utils.data.Dataset

Quick start with a mixin class for `torch.utils.data.Dataset` with the installation of `pip install videodataset` and the following code:

```python
from videodataset.dataset.base_dataset import BaseVideoDataset
import torch
import random

class MyDataset(torch.utils.data.Dataset, BaseVideoDataset):
    def __init__(self, number_of_frames: int, video_path: str, codec: str = "h265"):
        super().__init__()
        self.video_path = video_path
        self.decoder = self.get_decoder(video_path, codec)
        self.frames = []
        self.number_of_frames = number_of_frames

    def __len__(self):
        return self.number_of_frames

    def __getitem__(self, idx):
        got = False
        while not got:
            try:
                frame = self.decode_video_frame(
                    self.decoder,
                    self.video_path,
                    idx,
                )
                self.frames.append(frame)
                result = self.frames[idx]
                got = True
            except Exception:
                idx = random.randint(0, len(self.frames) - 1)
        return result

# Usage example
dataset = MyDataset(10, "/path/to/video.mp4")
dataloader = torch.utils.data.DataLoader(
    dataset,
    batch_size=4,
    shuffle=True,
    num_workers=0,
)
```

### LeRobot Dataset Integration

Use the `LeRobotVideoDataset` class requires the installation of `pip install videodataset[lerobot]`. Here is an example:

```python
from videodataset.dataset.lerobot_dataset import LeRobotVideoDataset
import torch

# Initialize dataset
lerobot_dataset = LeRobotVideoDataset(
    repo_id=None,
    root="/path/to/lerobot_svla_so100_stacking",
)

# Create DataLoader
dataloader = torch.utils.data.DataLoader(
    lerobot_dataset,
    batch_size=4,
    shuffle=True,
    num_workers=0,
)
```

For more examples, see the [tests directory](https://code.agibot.com/ai-platform/videodataset/-/tree/main/tests).
