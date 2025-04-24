import os
import torch
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
        missing = [
            field
            for field in ["action_gts", "state", "action_mask"]
            if field not in sample
        ]
        assert not missing, f"Missing required fields: {missing}"
        action_gts = sample["action_gts"] = torch.rand(30, 14, dtype=torch.float32)
        state = sample["state"] = torch.rand(1, 14, dtype=torch.float32)
        assert action_gts.dtype == torch.float32, (
            f"action_gts dtype error {action_gts.dtype}"
        )
        assert action_gts.shape == (30, 14), (
            f"action_gts shape error {action_gts.shape}"
        )
        assert state.dtype == torch.float32, f"state dtype error {state.dtype}"
        assert state.shape == (1, 14), f"state shape error {state.shape}"
