import os
from pathlib import Path

from videodataset.dataset import A2dVideoDataset


def test_dataset():
    parent_dir = Path(__file__).parent.parent
    label_file_dir = os.path.join(parent_dir, "testdata", "labels")
    data_root_dir = os.path.join(parent_dir, "testdata", "data")
    dataset = A2dVideoDataset(label_file_dir, data_root_dir)

    assert len(dataset) == 1
    for sample in dataset:
        assert sample["frame"]
