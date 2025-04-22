import os
import pytest
from pathlib import Path

from videodataset.dataset import A2dVideoDataset


@pytest.fixture
def sample_batch():
    parent_dir = Path(__file__).parent.parent
    video_path = os.path.join(parent_dir, "sample.mp4")
    """生成包含10个样本的测试数据"""
    return [
        {
            "video": video_path,
        }
        for _ in range(10)
    ]


def test_dataset(sample_batch):
    dataset = A2dVideoDataset(sample_batch, None, 0, "h265")

    for sample in dataset:
        assert sample["frame"]
