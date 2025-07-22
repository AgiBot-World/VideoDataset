from __future__ import annotations

import numpy as np
import pytest
from lerobot.datasets.lerobot_dataset import LeRobotDataset  # type: ignore

from videodataset.dataset.lerobot_dataset import LeRobotVideoDataset


def test_lerobot(lerobot_svla_so100_stacking_path):
    vt_dataset = LeRobotVideoDataset(
        repo_id=None,
        root=lerobot_svla_so100_stacking_path,
    )
    lr_dataset = LeRobotDataset(
        repo_id=None,
        root=lerobot_svla_so100_stacking_path,
    )
    for i in range(10):
        sample_vt = vt_dataset[i]
        sample_lr = lr_dataset[i]
        for vt_key, vt_value in sample_vt.items():
            lr_value = sample_lr[vt_key]
            if isinstance(vt_value, str):
                assert vt_value == lr_value
            else:
                np.allclose(vt_value.cpu().numpy(), lr_value.cpu().numpy(), atol=1e-3)


@pytest.mark.benchmark(group="lerobot_videodataset_loading")
def test_lerobot_benchmark(benchmark, lerobot_svla_so100_stacking_path):
    vt_dataset = LeRobotVideoDataset(
        repo_id=None,
        root=lerobot_svla_so100_stacking_path,
    )

    def iter():
        for i, sample in enumerate(vt_dataset):
            yield i, sample

    benchmark.pedantic(
        lambda: next(iter()),
        iterations=4,
        rounds=100,
    )
