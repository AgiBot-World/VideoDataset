from __future__ import annotations

import random

import torch

from videodataset.dataset.base_dataset import BaseVideoDataset


def test_mixin_with_torch_dataset(test_video):
    """Test the mixin class BaseVideoDataset for torch dataset."""

    class MyDataset(torch.utils.data.Dataset, BaseVideoDataset):
        def __init__(
            self,
            number_of_frames: int,
            video_path: str,
            codec: str = "h265",
        ):
            super().__init__()
            self.video_path = video_path
            self.decoder = self.get_decoder(video_path, codec)
            self.number_of_frames = number_of_frames

        def __len__(self):
            return self.number_of_frames

        def __getitem__(self, idx):
            got = False
            while not got:
                try:
                    result = self.decode_video_frame(
                        self.decoder,
                        self.video_path,
                        idx,
                    )
                    got = True
                except Exception:
                    idx = random.randint(0, len(self.frames) - 1)
            return result

    num_of_frames = 10
    dataset = MyDataset(num_of_frames, str(test_video))
    for batch in torch.utils.data.DataLoader(dataset, batch_size=2):
        assert batch.shape == (2, 720, 1280, 3)
