import os
import json
import glob
from typing import List, Dict, Optional, Callable

import torch
from torch.utils.data import Dataset
from videodataset.video_decoder import VideoDecoder


class A2dVideoDataset(Dataset):
    def __init__(
        self,
        label_file_dir: str,
        data_root_dir: str,
        transforms: Optional[Callable] = None,
        episode_transforms: Optional[Callable] = None,
        device_id: int = 0,
        codec: str = "h265",
    ):
        super().__init__()
        self.episode_transforms = episode_transforms
        self.transforms = transforms
        self.data_root_dir = data_root_dir

        self.decoder = VideoDecoder(device_id, codec)
        self.episodes: List[Dict] = []

        self.load_episodes(label_file_dir)
        self.load_meta()

        if self.episode_transforms:
            self.episodes = [self.episode_transforms(ep) for ep in self.episodes]

    def get_episode_path(self, episode_info: Dict) -> str:
        return os.path.join(
            self.data_root_dir,
            str(episode_info["task_id"]),
            str(episode_info["job_id"]),
            str(episode_info["sn_code"]),
            str(episode_info["episode_id"]),
        )

    def get_meta_info_path(self, episode_info: Dict) -> str:
        return os.path.join(self.get_episode_path(episode_info), "meta_info.json")

    def get_video_path(self, episode_info: Dict) -> str:
        return os.path.join(self.get_episode_path(episode_info), "sample.mp4")

    def load_episodes(self, label_file_dir: str) -> None:
        if not os.path.isdir(label_file_dir):
            raise NotADirectoryError(
                f"Label directory does not exist: {label_file_dir}"
            )

        json_files = glob.glob(os.path.join(label_file_dir, "*.json"), recursive=False)

        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    episodes = json.load(f)
                    self.episodes.extend(episodes)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON parsing failed: {json_file}") from e

    def load_meta(self) -> None:
        for episode in self.episodes:
            episode_path = self.get_episode_path(episode)
            episode["episode_path"] = episode_path
            episode["video"] = self.get_video_path(episode)

            meta_path = self.get_meta_info_path(episode)
            try:
                with open(meta_path, "r", encoding="utf-8") as fid:
                    episode["meta_info"] = json.load(fid)
            except FileNotFoundError:
                print(f"Warning: Meta file not found at {meta_path}")
                episode["meta_info"] = {}

    def __len__(self):
        return len(self.episodes)

    def __getitem__(self, idx):
        sample = self.episodes[idx]
        decoded_frame = self.decoder.decode(sample["video"], 0)
        frame_tensor = torch.from_dlpack(decoded_frame)
        sample["frame"] = frame_tensor

        if self.transforms:
            sample = self.transforms(sample)
        return sample
