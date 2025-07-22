from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from typing import Any, List

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

from videodataset import VideoDecoder
from videodataset.utils.video_util import nv12_to_rgb

logger = logging.getLogger(__name__)


class BaseVideoDataset(Dataset, ABC):
    def __init__(
        self,
        ds_name: str,
        label_file_dir: str,
        data_root_dir: str,
    ):
        super().__init__()
        self.ds_name = ds_name
        self.data_root_dir = data_root_dir
        self.device_id = torch.cuda.current_device()
        self.codec = "h265"
        self.decoders: dict = {}
        self.decoder_name_list: list = []

        self.episodes: dict[int, dict[str, Any]] = {}
        self.frames: List[dict] = []

    @abstractmethod
    def load_data(self) -> None:
        """
        Initialize and load all episode information and frame data.

        Performs two main operations:
        1. Episode Initialization:
        - Loads episode information into `self.episodes`
        - Structure: dict[int, dict] where:
            - Key: episode ID (integer)
            - Value: episode data dictionary containing all relevant attributes

        2. Frame Data Loading:
        - Populates frame information for all episodes into `self.frame`
        - Structure: list where each element contains the frame information for an episode
        """
        pass

    def decode_img_frame(self, episode_info, cam_name, frame_idx):
        cam_file_path = self.get_img_path(episode_info, cam_name, frame_idx)
        img = Image.open(cam_file_path).convert("RGB")
        rgb_tenfor = np.array(img)
        return rgb_tenfor

    def create_decoder(self, decoder_name) -> None:
        self.decoders[decoder_name] = VideoDecoder(self.device_id, self.codec)
        self.decoder_name_list.append(decoder_name)

    @abstractmethod
    def get_decoder(self, video_path) -> VideoDecoder:
        pass

    def decode_video_frame(self, episode_info, cam_name, frame_idx):
        video_path = self.get_video_path(episode_info, cam_name)
        decoder = self.get_decoder(video_path)
        decoded_frame = decoder.decode(video_path, frame_idx)
        (height, width) = decoded_frame.shape
        src_tensor = torch.from_dlpack(decoded_frame)
        rgb_tensor = nv12_to_rgb(src_tensor, width, int(height / 1.5))
        rgb_tensor = rgb_tensor.cpu().numpy()
        return rgb_tensor

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, idx):
        get_data_done = False
        while not get_data_done:
            try:
                result = self.getitem(idx)
                get_data_done = True
            except Exception as error:
                logger.error(f"process dataset idx: {idx}, error info: {error}")
                idx = random.randint(0, len(self.frames) - 1)
        return result

    def getitem(self, idx):
        raw_sample = self.frames[idx]
        return raw_sample
