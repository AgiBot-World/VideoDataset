import os
import json
import glob
from typing import Any, List, Dict, Callable

import h5py  # type: ignore[import-untyped]
import torch
import numpy as np
from torch.utils.data import Dataset
from videodataset.video_decoder import VideoDecoder


class A2dVideoDataset(Dataset):
    def __init__(
        self,
        label_file_dir: str,
        data_root_dir: str,
        transforms: Callable | None = None,
        episode_transforms: Callable | None = None,
        action_chunk_size: int = 30,
        action_shift: int = 1,
        joint_dof: int = 7,
        gripper_dof: int = 1,
        gripper_source: str = "action",
        device_id: int = 0,
        codec: str = "h265",
    ):
        super().__init__()
        self.episode_transforms = episode_transforms
        self.transforms = transforms
        self.data_root_dir = data_root_dir
        self.action_chunk_size = action_chunk_size
        self.action_shift = action_shift
        self.joint_dof = joint_dof
        self.gripper_dof = gripper_dof
        self.gripper_source = gripper_source

        self.decoder = VideoDecoder(device_id, codec)
        self.episodes: dict[int, dict[str, Any]] = {}
        self.frames: List[dict] = []

        self.load_episodes(label_file_dir)
        self.load_meta()
        self.load_states()

        if self.episode_transforms:
            self.episodes = {
                ep_id: self.episode_transforms(ep)
                for ep_id, ep in self.episodes.items()
            }

        self.load_frames()

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

    def get_state_path(self, episode_info: Dict) -> str:
        return os.path.join(self.get_episode_path(episode_info), "aligned_joints.h5")

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
                    self.episodes = {ep["episode_id"]: ep for ep in json.load(f)}

            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON parsing failed: {json_file}") from e

    def load_meta(self) -> None:
        for episode in self.episodes.values():
            meta_path = self.get_meta_info_path(episode)
            try:
                with open(meta_path, "r", encoding="utf-8") as fid:
                    episode["meta_info"] = json.load(fid)
            except FileNotFoundError:
                print(f"Warning: Meta file not found at {meta_path}")
                episode["meta_info"] = {}

    def load_states(self) -> None:
        for episode in self.episodes.values():
            state_file = self.get_state_path(episode)
            with h5py.File(state_file, "r") as fid:
                all_abs_joint = np.array(fid["state/joint/position"], dtype=np.float32)
                all_abs_gripper = np.array(
                    fid[f"{self.gripper_source}/effector/position"], dtype=np.float32
                )
                all_abs_head = np.array(fid["state/head/position"], dtype=np.float32)
                all_abs_waist = np.array(fid["state/waist/position"], dtype=np.float32)

            state = {}
            state["left_arm_abs_joint"] = all_abs_joint[:, : self.joint_dof]
            state["right_arm_abs_joint"] = all_abs_joint[:, self.joint_dof :]
            state["left_arm_abs_gripper"] = all_abs_gripper[:, : self.gripper_dof]
            state["right_arm_abs_gripper"] = all_abs_gripper[:, self.gripper_dof :]
            state["head_abs_joint"] = all_abs_head
            try:
                state["waist_abs_joint"] = all_abs_waist[:, 0:1]
                state["waist_abs_lift"] = all_abs_waist[:, 1:2]
            except Exception:
                state["waist_abs_joint"] = np.zeros_like(all_abs_joint)[:, :1]
                state["waist_abs_lift"] = np.zeros_like(all_abs_joint)[:, :1]
            episode["state"] = state

    def load_frames(self) -> None:
        for episode in self.episodes.values():
            action_config = episode["label_info"]["action_config"]
            last_frame_idx = max(step["end_frame"] for step in action_config)
            for act_step in action_config:
                start = act_step["start_frame"]
                end = min(
                    act_step["end_frame"],
                    last_frame_idx - self.action_chunk_size * self.action_shift,
                )
                for current_idx in range(start, end):
                    self.frames.append(
                        {
                            "episode_id": f"{episode['episode_id']}",
                            "frame_idx": f"{current_idx}",
                            "target_idx": f"{current_idx + self.action_chunk_size * self.action_shift}",
                            "video": self.get_video_path(episode),
                        }
                    )

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, idx):
        sample = self.frames[idx]
        decoded_frame = self.decoder.decode(sample["video"], 0)
        frame_tensor = torch.from_dlpack(decoded_frame)
        sample["frame"] = frame_tensor

        if self.transforms:
            sample = self.transforms(sample)
        return sample
