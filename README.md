# VideoDataset

<!-- SPHINX-START -->

A GPU-accelerated library that enables random frame access and efficient video decoding for data loading.

[![Documentation](https://img.shields.io/badge/Documentation-sphinx-blue)](https://AgiBot-World.github.io/VideoDataset)
[![License](https://img.shields.io/github/license/AgiBot-World/videodataset)](https://github.com/AgiBot-World/videodataset/blob/master/LICENSE)
[![SS Badge](https://img.shields.io/badge/Serious%20Scaffold-pybind11-blue)](https://github.com/serious-scaffold/ss-pybind11)

[![CI](https://github.com/AgiBot-World/videodataset/actions/workflows/ci.yml/badge.svg)](https://github.com/AgiBot-World/videodataset/actions/workflows/ci.yml)
[![CD](https://github.com/AgiBot-World/videodataset/actions/workflows/cd.yml/badge.svg)](https://github.com/AgiBot-World/videodataset/actions/workflows/cd.yml)
[![CommitLint](https://github.com/AgiBot-World/videodataset/actions/workflows/commitlint.yml/badge.svg)](https://github.com/AgiBot-World/videodataset/actions/workflows/commitlint.yml)
[![Renovate](https://github.com/AgiBot-World/videodataset/actions/workflows/renovate.yml/badge.svg)](https://github.com/AgiBot-World/videodataset/actions/workflows/renovate.yml)
[![Semantic Release](https://github.com/AgiBot-World/videodataset/actions/workflows/semantic-release.yml/badge.svg)](https://github.com/AgiBot-World/videodataset/actions/workflows/semantic-release.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://AgiBot-World.github.io/VideoDataset/_static/badges/coverage.json)](https://AgiBot-World.github.io/VideoDataset/reports/coverage)

[![Release](https://img.shields.io/github/v/release/AgiBot-World/videodataset)](https://github.com/AgiBot-World/videodataset/releases)
[![PyPI](https://img.shields.io/pypi/v/agibot-videodataset)](https://pypi.org/project/agibot-videodataset/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/agibot-videodataset)](https://pypi.org/project/agibot-videodataset/)
[![GitHub](https://img.shields.io/github/license/AgiBot-World/videodataset)](https://github.com/AgiBot-World/videodataset/blob/main/LICENSE)

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-orange.json)](https://github.com/copier-org/copier)
[![Serious Scaffold Python](https://img.shields.io/endpoint?url=https://serious-scaffold.github.io/ss-python/_static/badges/logo.json)](https://serious-scaffold.github.io/ss-python)

> [!WARNING]
> _VideoDataset_ is in the **Alpha** phase.
> Frequent changes and instability should be anticipated.
> Any feedback, comments, suggestions and contributions are welcome!

## Overview

VideoDataset is a high-performance video decoding multi-framework supporting library. It aims to provide framework-integrated solutions for working with video decoding tasks.

Key Features:

- GPU-accelerated video decoding using NvCodec library
- Support for common video formats (H.264, H.265, etc.)
- Easy integration with multi-frameworks and multi-formats.

## Installation

### Prerequisites

- NVIDIA GPU with CUDA support and CUDA Toolkit installed
  - CUDA Toolkit 12.0 or later
- FFmpeg installed
- Python 3.10 or later

### Install from PyPI index

```bash
pip install agibot-videodataset
```

### Building from Source

```bash
pip install . git+https://github.com/AgiBot-World/videodataset.git

```

## Quick Start

Here is a simple example. The complete example can be found in the [quickstart documentation](https://github.com/AgiBot-World/VideoDataset/blob/main/docs/quickstart.md).

```python

from pathlib import Path
from torch.utils.data import DataLoader, Dataset

from videodataset.dataset import BaseVideoDataset


class MyDataset(Dataset, BaseVideoDataset):

    def __init__(
        self,
        video_path: Path,
        total_frames: int,
    ):
        Dataset.__init__(self)
        BaseVideoDataset.__init__(self)
        self.video = Path(video_path)
        self.total_frames = total_frames

    def __len__(self):
        return self.total_frames

    def __getitem__(self, idx) -> dict:

        # Key Point 1: Initialize the decoder, specifying an efficient video codec (e.g., HEVC)
        decoder = self.get_decoder(decoder_key=self.video, codec="hevc")

        # Key Point 2: Decode the specified frame
        frame = self.decode_video_frame(
            decoder=decoder, video_path=self.video, frame_idx=idx
        )
        return frame

dataset = MyDataset(video_path="/path/to/video", total_frames=1000)

# Key Point 3: Using 'multiprocessing_context="spawn"' when num_workers > 0
dataloader = DataLoader(dataset, batch_size=batch_size, num_workers=num_workers, multiprocessing_context="spawn", )

for epoch in range(2):
    for batch_idx, batch_data in enumerate(dataloader):
        logger.info(f"Epoch {epoch} Batch {batch_idx}: {batch_data}")

```

## Documentation

Full documentation is available at: [Documentation](https://AgiBot-World.github.io/VideoDataset).

Also, a sphinx-based documentation can be generated by running the following command:

```bash
make dev-doc doc-coverage
```

It will generate the documentation in the `docs/_build/html` directory and serve it on <http://localhost:8000>.

## Performance

VideoDataset is optimized for high-throughput video processing. Benchmark results show:

- **GPU Decoding:** A decoding throughput of 20,000 FPS is achieved in a multiprocessing environment.
- **Random Access:** Minimal overhead for non-sequential frame access.
- **GPU Decoder Utilization:** Over 90% GPU decoder utilization is achieved in a multiprocessing environment.

See the [benchmark documentation](https://github.com/AgiBot-World/VideoDataset/blob/main/docs/benchmark.md) for detailed performance analysis.

## Development Status

- [&check;] GPU acceleration via NvCodec
- [&check;] Random frame access
- [&check;] PyTorch integration
- [ ] Multi-stage pipeline optimization
- [ ] Compatibility with LeRobot
- [ ] Distributed storage loading​
- [ ] Additional video format support

## License

MIT License, for more details, see the [LICENSE](https://github.com/AgiBot-World/videodataset/blob/master/LICENSE) file.
