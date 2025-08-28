from __future__ import annotations

import random

import numpy as np
import pytest

try:
    from lerobot.datasets.lerobot_dataset import LeRobotDataset  # type: ignore
except ImportError:
    pytestmark = pytest.mark.skip("lerobot not installed, skipping test")


@pytest.mark.parametrize(
    ("video_dataset", "lerobot_dataset"),
    [("ucsd_kitchen_video_dataset", "ucsd_kitchen_dataset")],
)
def test_lerobot(video_dataset, lerobot_dataset, request):
    video_dataset = request.getfixturevalue(video_dataset)
    lerobot_dataset = request.getfixturevalue(lerobot_dataset)

    assert len(video_dataset) == len(lerobot_dataset)

    test_indices = random.sample(range(len(video_dataset)), 10)
    for i in test_indices:
        sample_vt = video_dataset[i]
        sample_lr = lerobot_dataset[i]
        for vt_key, vt_value in sample_vt.items():
            lr_value = sample_lr[vt_key]
            if isinstance(vt_value, str):
                assert vt_value == lr_value
            else:
                vt_tensor, lr_tensor = vt_value.cpu().numpy(), lr_value.cpu().numpy()

                assert np.allclose(
                    vt_tensor.mean(),
                    lr_tensor.mean(),
                    atol=5e-2,
                )

                assert np.allclose(
                    vt_tensor.std(),
                    lr_tensor.std(),
                    atol=5e-2,
                )
