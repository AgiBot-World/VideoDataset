import os
from pathlib import Path

from videodataset.dataset import A2dVideoDataset


def test_dataset():
    parent_dir = Path(__file__).parent.parent
    label_file_dir = os.path.join(parent_dir, "testdata", "labels")
    data_root_dir = os.path.join(parent_dir, "testdata", "data")
    dataset = A2dVideoDataset(label_file_dir, data_root_dir)

    assert len(dataset.episodes) == 1
    assert len(dataset) == 3275
    for sample in dataset:
        ep_id = sample["episoce_id"]
        ep_info = dataset.episodes[ep_id]
        missing = [field for field in ["state"] if field not in ep_info]
        assert not missing, f"Missing required fields: {missing}"
        assert sample["frame"]
