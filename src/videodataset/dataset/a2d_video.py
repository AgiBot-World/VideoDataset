import torch

from torch.utils.data import Dataset
from videodataset.video_decoder import VideoDecoder


class A2dVideoDataset(Dataset):
    def __init__(self, samples, transforms, device_id, codec):
        self.samples = samples
        self.transforms = transforms
        self.decoder = VideoDecoder(device_id, codec)

    def __len__(self):
        return len(self.datas)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        decoded_frame = self.decoder.decode(sample["video"], 0)
        frame_tensor = torch.from_dlpack(decoded_frame)
        sample["frame"] = frame_tensor

        if self.transforms:
            sample = self.transforms(sample)
        return sample
