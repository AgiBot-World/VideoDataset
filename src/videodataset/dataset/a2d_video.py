import os
import copy
import json
import glob
from typing import Any, List, Dict, Callable

import h5py  # type: ignore[import-untyped]
import torch
import numpy as np
from pathlib import Path
from torch.utils.data import Dataset
from videodataset.video_decoder import VideoDecoder
from . import Kinematics


class A2dVideoDataset(Dataset):
    def __init__(
        self,
        label_file_dir: str,
        data_root_dir: str,
        transforms: Callable | None = None,
        episode_transforms: Callable | None = None,
        action_chunk_size: int = 30,
        action_shift: int = 1,
        use_real_state: bool = False,
        joint_dof: int = 7,
        gripper_dof: int = 1,
        gripper_source: str = "action",
        action_use_delta: bool = True,
        delta_type: str = "frame",
        gripper_use_delta: bool = False,
        use_latent_action: bool = False,
        device_id: int = 0,
        codec: str = "h265",
    ):
        super().__init__()
        self.episode_transforms = episode_transforms
        self.transforms = transforms
        self.data_root_dir = data_root_dir
        self.action_chunk_size = action_chunk_size
        self.action_shift = action_shift
        self.use_real_state = use_real_state
        self.joint_dof = joint_dof
        self.gripper_dof = gripper_dof
        self.gripper_source = gripper_source
        self.action_use_delta = action_use_delta
        self.delta_type = delta_type
        self.gripper_use_delta = gripper_use_delta
        self.use_latent_action = use_latent_action
        self.ActionSpacePadder = ActionSpacePadder()

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

            all_left_eef = []
            all_right_eef = []
            conventor = A2dJoint2Eef()
            for f_idx in range(state["left_arm_abs_joint"].shape[0]):
                left_eef, right_eef = conventor.get_eef_pos(
                    waist_pitch=state["waist_abs_joint"][f_idx][0],
                    waist_lift=state["waist_abs_lift"][f_idx][0],
                    left_joints=state["left_arm_abs_joint"][f_idx],
                    right_joints=state["right_arm_abs_joint"][f_idx],
                    head_joints=state["head_abs_joint"][f_idx],
                )
                all_left_eef.append(left_eef)
                all_right_eef.append(right_eef)
            state["left_effector_abs_pose"] = np.stack(all_left_eef)
            state["right_effector_abs_pose"] = np.stack(all_right_eef)
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

    def get_action_and_state(self, sample: dict) -> None:
        episode_id = int(sample["episode_id"])
        episode_info = self.episodes[episode_id]
        state = episode_info["state"]
        current_idx = int(sample["frame_idx"])

        left_arm_joint_chunk = []
        right_arm_joint_chunk = []
        left_effector_pose_chunk = []
        right_effector_pose_chunk = []
        left_arm_gripper_chunk = []
        right_arm_gripper_chunk = []

        def normalize_angles(radius):
            radius_normed = np.mod(radius, 2 * np.pi) - 2 * np.pi * (
                np.mod(radius, 2 * np.pi) > np.pi
            )
            return radius_normed

        def get_target_action(state, current_idx, target_idx, tag_name, use_delta):
            if use_delta:
                target_action = (
                    state[tag_name][target_idx] - state[tag_name][current_idx]
                )
            else:
                target_action = state[tag_name][target_idx]

            if tag_name in ["left_arm_abs_joint", "right_arm_abs_joint"]:  # TODO(hxd)
                target_action = normalize_angles(target_action)
            if tag_name in ["left_effector_abs_pose", "right_effector_abs_pose"]:
                target_action[3:] = normalize_angles(target_action[3:])

            return target_action

        for i in range(self.action_chunk_size):
            shift_idx = current_idx + self.action_shift * (i + 1)
            base_idx = (
                current_idx
                if self.delta_type == "chunk"
                else shift_idx - self.action_shift
            )
            left_arm_joint_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "left_arm_abs_joint",
                    self.action_use_delta,
                )
            )
            right_arm_joint_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "right_arm_abs_joint",
                    self.action_use_delta,
                )
            )
            left_effector_pose_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "left_effector_abs_pose",
                    self.action_use_delta,
                )
            )
            right_effector_pose_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "right_effector_abs_pose",
                    self.action_use_delta,
                )
            )
            left_arm_gripper_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "left_arm_abs_gripper",
                    self.gripper_use_delta,
                )
            )
            right_arm_gripper_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "right_arm_abs_gripper",
                    self.gripper_use_delta,
                )
            )

        action_target = {
            "left_arm_joint_positions": np.array(left_arm_joint_chunk),
            "right_arm_joint_positions": np.array(right_arm_joint_chunk),
            "left_end_effector_6d_pose": np.array(left_effector_pose_chunk),
            "right_end_effector_6d_pose": np.array(right_effector_pose_chunk),
            "left_gripper_joint_positions": np.array(left_arm_gripper_chunk),
            "right_gripper_joint_positions": np.array(right_arm_gripper_chunk),
        }
        agent_state = {
            "left_arm_joint_positions": state["left_arm_abs_joint"][
                current_idx : current_idx + 1
            ],
            "right_arm_joint_positions": state["right_arm_abs_joint"][
                current_idx : current_idx + 1
            ],
            "left_end_effector_6d_pose": state["left_effector_abs_pose"][
                current_idx : current_idx + 1
            ],
            "right_end_effector_6d_pose": state["right_effector_abs_pose"][
                current_idx : current_idx + 1
            ],
            "head_joint_positions": state["head_abs_joint"][
                current_idx : current_idx + 1
            ],
            "waist_joint_positions": state["waist_abs_joint"][
                current_idx : current_idx + 1
            ],
            "waist_lift_positions": state["waist_abs_lift"][
                current_idx : current_idx + 1
            ],
            "left_gripper_joint_positions": state["left_arm_abs_gripper"][
                current_idx : current_idx + 1
            ],
            "right_gripper_joint_positions": state["right_arm_abs_gripper"][
                current_idx : current_idx + 1
            ],
        }
        sample["action_target"] = action_target
        sample["agent_state"] = agent_state

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, idx):
        raw_sample = self.frames[idx]
        sample = copy.deepcopy(raw_sample)

        self.get_action_and_state(sample)

        if self.transforms:
            sample = self.transforms(sample)

        if not self.use_latent_action:
            action, _ = self.ActionSpacePadder.get_action(
                sample["action_target"], chunk_size=self.action_chunk_size
            )
            state, _ = self.ActionSpacePadder.get_action(
                sample["agent_state"], chunk_size=1
            )
        else:
            action, _ = self.ActionSpacePadder.get_action(
                {}, chunk_size=self.action_chunk_size
            )
            state, _ = self.ActionSpacePadder.get_action({}, chunk_size=1)
        agent_state = torch.tensor(state, dtype=torch.float32)
        if not self.use_real_state:
            agent_state = -1 * torch.ones_like(agent_state)

        results = {
            "action_gts": torch.tensor(action, dtype=torch.float32),
            "action_mask": None,  # torch.tensor(action_mask, dtype=torch.float32),
            "state": agent_state,
        }
        decoded_frame = self.decoder.decode(sample["video"], 0)
        frame_tensor = torch.from_dlpack(decoded_frame)
        results["frame"] = frame_tensor
        return results


class A2dJoint2Eef:
    def __init__(self):
        self.kinematics = Kinematics(
            (Path(__file__).parent / "A2D_viz.urdf").as_posix()
        )

    def get_eef_pos(
        self, waist_pitch, waist_lift, left_joints, right_joints, head_joints=None
    ):
        init_arm_joint_angles = np.concatenate([left_joints, right_joints], axis=0)

        left_end_eef, right_end_eef = self.kinematics.compute_arm_fk(
            init_arm_joint_angles,
            waist_pitch,
            waist_lift,
        )
        return left_end_eef, right_end_eef


class UniformAction:
    # Right Arm
    RIGHT_ARM_JOINT_POSITIONS = ("right_arm_joint_positions", 7)  # 0:shoulder  6:hand
    RIGHT_END_EFFECTOR_6D_POSE = ("right_end_effector_6d_pose", 6)
    RIGHT_GRIPPER_JOINT_POSITIONS = ("right_gripper_joint_positions", 1)
    RIGHT_DEXTEROUS_HAND_POSITIONS = ("right_dexterous_hand_positions", 6)  # 灵巧手

    RIGHT_ARM_JOINT_VELOCITIES = ("right_arm_joint_velocities", 7)
    RIGHT_GRIPPER_JOINT_VELOCITIES = ("right_gripper_joint_velocities", 5)
    RIGHT_END_EFFECTOR_POSITIONS = ("right_end_effector_positions", 3)
    RIGHT_END_EFFECTOR_VELOCITIES = ("right_end_effector_velocities", 3)
    RIGHT_END_EFFECTOR_ANGULAR_VELOCITIES = ("right_end_effector_angular_velocities", 3)

    # Left Arm
    LEFT_ARM_JOINT_POSITIONS = ("left_arm_joint_positions", 7)
    LEFT_END_EFFECTOR_6D_POSE = ("left_end_effector_6d_pose", 6)
    LEFT_GRIPPER_JOINT_POSITIONS = ("left_gripper_joint_positions", 1)
    LEFT_DEXTEROUS_HAND_POSITIONS = ("left_dexterous_hand_positions", 6)  # 灵巧手

    LEFT_ARM_JOINT_VELOCITIES = ("left_arm_joint_velocities", 7)
    LEFT_GRIPPER_JOINT_VELOCITIES = ("left_gripper_joint_velocities", 5)
    LEFT_END_EFFECTOR_POSITIONS = ("left_end_effector_positions", 3)
    LEFT_END_EFFECTOR_VELOCITIES = ("left_end_effector_velocities", 3)
    LEFT_END_EFFECTOR_ANGULAR_VELOCITIES = ("left_end_effector_angular_velocities", 3)

    # BODY
    HEAD_JOINT_POSITIONS = ("head_joint_positions", 2)
    WAIST_LIFT_POSITIONS = ("waist_lift_positions", 1)
    WAIST_JOINT_POSITIONS = ("waist_joint_positions", 1)

    BASE_LINEAR_VELOCITIES = ("base_linear_velocities", 2)
    BASE_ANGULAR_VELOCITIES = ("base_angular_velocities", 1)


class ActionSpacePadder:
    action_space: dict = {}
    action_space_len = 0
    space_used_left = [
        "LEFT_END_EFFECTOR_6D_POSE",
        "LEFT_GRIPPER_JOINT_POSITIONS",
    ]
    space_used_right = [
        "RIGHT_END_EFFECTOR_6D_POSE",
        "RIGHT_GRIPPER_JOINT_POSITIONS",
    ]
    space_used_body: list = []

    @classmethod
    def get_space(
        cls,
    ):
        cls.space_used = (
            cls.space_used_left + cls.space_used_right + cls.space_used_body
        )

        for attribute_name in sorted(dir(UniformAction)):
            if not attribute_name.startswith("__") and attribute_name in cls.space_used:
                attribute_value = getattr(UniformAction, attribute_name)
                cls.action_space.update(
                    {
                        attribute_value[0]: (
                            cls.action_space_len,
                            cls.action_space_len + attribute_value[1],
                        )
                    }
                )
                cls.action_space_len += attribute_value[1]

    @classmethod
    def get_action(cls, targets, chunk_size=30):
        action = np.zeros((chunk_size, cls.action_space_len), dtype=np.float32)
        mask = np.zeros((1, cls.action_space_len), dtype=np.float32)
        for key, value in targets.items():
            if key in cls.action_space:
                value = np.array(value)
                start_idx, max_idx = cls.action_space[key]
                if value.shape[-1] <= (max_idx - start_idx):
                    action[:, start_idx : start_idx + value.shape[-1]] = value
                    mask[0, start_idx : start_idx + value.shape[-1]] = np.ones_like(
                        value[0]
                    )
                else:
                    raise ValueError(
                        f"Invalid action items! {key}:{value}, should follow start_idx:{start_idx}, max_idx:{max_idx}"
                    )

        return action, mask


ActionSpacePadder.get_space()
