import os
import cv2
import copy
import json
import glob
import random
import logging
from tqdm import tqdm
from typing import Any, List, Dict, Callable

import h5py
import torch
import torch.distributed as dist
import numpy as np
from PIL import Image
from pathlib import Path
from torch.utils.data import Dataset

from videodataset.video_decoder import VideoDecoder
from videodataset.utils.video_util import nv12_to_rgb
from videodataset.utils.image_util import (
    dynamic_preprocess,
    build_transform,
    build_latent_image_transform,
)
from videodataset.utils.converstion_util import preprocess_internlm
from videodataset.dataset.a2d_description import A2dJoint2Eef, A2dJoint2EefIK


logger = logging.getLogger(__name__)


class A2dVideoDataset(Dataset):
    def __init__(
        self,
        ds_name: str,
        label_file_dir: str,
        data_root_dir: str,
        tasks: dict = {},
        use_cam_list: list = ["head", "hand_right", "hand_left"],
        transforms: Callable | None = None,
        episode_transforms: Callable | None = None,
        action_chunk_size: int = 30,
        action_shift: int = 1,
        use_real_state: bool = False,
        joint_dof: int = 7,
        gripper_dof: int = 1,
        wrench_dof: int = 6,
        dexhand_dof: int = 6,
        effector_source: str = "action",
        state_noise_snr: float = 40,
        add_noise_to_state: bool = False,
        conventor_type: str = "ik_solver",
        action_use_delta: bool = True,
        delta_type: str = "frame",
        gripper_use_delta: bool = False,
        remove_intervention: bool = False,
        head_waist_use_delta: bool = True,
        head_waist_norm_margin: list | None = None,
        base_vel_use_norm: bool = False,
        base_vel_norm_margin: list = [
            1.5,
            0.5,
        ],  # [[base linear velocity upper limit, [base angular velocity upper limit]
        base_pos_use_delta: bool = True,
        use_latent_action: bool = False,
        use_action_mask: bool = False,
        actionSpacePadder=None,
        prompt_mode_list: list = [0],
        dynamic_image_size: bool = False,
        is_train: bool = True,
        image_size: int = 448,
        use_depth: bool = False,
        depth_size: tuple = (448, 448),
        pad2square: bool = False,
        use_thumbnail=False,
        min_dynamic_patch=1,
        max_dynamic_patch=12,
        normalize_type: str = "imagenet",
        num_image_token: int = 256,
        text_tokenizer=None,
        device_id: int = -1,
        codec: str = "h265",
        shuffle: bool = False,
        world_size: int | None = None,
        rank_id: int = 0,
        sample_rate: int | None = None,
        need_split_episode_by_rank: bool = False,
        need_split_data_by_rank: bool = True,
    ):
        super().__init__()
        self.ds_name = ds_name
        self.episode_transforms = episode_transforms
        self.transforms = transforms
        self.data_root_dir = data_root_dir
        self.tasks = tasks
        self.use_cam_list = use_cam_list
        self.action_chunk_size = action_chunk_size
        self.action_shift = action_shift
        self.use_real_state = use_real_state
        self.joint_dof = joint_dof
        self.gripper_dof = gripper_dof
        self.wrench_dof = wrench_dof
        self.dexhand_dof = dexhand_dof
        self.effector_source = effector_source
        self.state_noise_snr = state_noise_snr
        self.add_noise_to_state = add_noise_to_state
        self.conventor_type = conventor_type
        self.action_use_delta = action_use_delta
        self.delta_type = delta_type
        self.gripper_use_delta = gripper_use_delta
        self.remove_intervention = remove_intervention
        self.head_waist_use_delta = head_waist_use_delta
        self.head_waist_norm_margin = head_waist_norm_margin
        self.base_vel_use_norm = base_vel_use_norm
        self.base_vel_norm_margin = base_vel_norm_margin
        self.base_pos_use_delta = base_pos_use_delta
        self.use_latent_action = use_latent_action
        self.use_action_mask = use_action_mask
        self.ActionSpacePadder = actionSpacePadder
        self.prompt_mode_list = prompt_mode_list
        self.dynamic_image_size = dynamic_image_size
        self.is_train = is_train
        self.image_size = image_size
        self.use_depth = use_depth
        self.depth_size = depth_size
        self.pad2square = pad2square
        self.use_thumbnail = use_thumbnail
        self.min_dynamic_patch = min_dynamic_patch
        self.max_dynamic_patch = max_dynamic_patch
        self.normalize_type = normalize_type
        self.num_image_token = num_image_token
        self.text_tokenizer = text_tokenizer
        self.shuffle = shuffle
        self.world_size = world_size
        self.rank_id = rank_id
        self.sample_rate = sample_rate
        self.need_split_episode_by_rank = need_split_episode_by_rank
        self.need_split_data_by_rank = need_split_data_by_rank

        self.device_id = device_id if device_id != -1 else torch.cuda.current_device()
        self.codec = codec
        self.decoder = None
        self.head_decoder = None

        self.episodes: dict[int, dict[str, Any]] = {}
        self.frames: List[dict] = []

        self.load_episodes(label_file_dir)
        self.load_meta()

        if self.conventor_type == "kinematics":
            self.conventor = A2dJoint2Eef()
        else:
            self.conventor = A2dJoint2EefIK()
        self.load_states(self.conventor)

        if self.episode_transforms:
            self.process_episode_transform()

        self.load_frames()

        if self.sample_rate is not None:
            self.sample_frame()
        if self.shuffle:
            self.shuffle_sample()

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

    def get_video_path(self, episode_info: Dict, cam_name: str) -> str:
        return os.path.join(
            self.get_episode_path(episode_info), "videos", f"{cam_name}_color.mp4"
        )

    def load_episodes(self, label_file_dir: str) -> None:
        if not os.path.isdir(label_file_dir):
            raise NotADirectoryError(
                f"Label directory does not exist: {label_file_dir}"
            )

        label_files = []
        for task_cfg in self.tasks.values():
            label_files.append(task_cfg["label_file_name"])

        json_files = glob.glob(os.path.join(label_file_dir, "*.json"), recursive=False)

        self.episodes = {}
        for json_file in json_files:
            json_file_name = Path(json_file).name
            if json_file_name not in label_files:
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    self.episodes.update({ep["episode_id"]: ep for ep in json.load(f)})

            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON parsing failed: {json_file}") from e
        for episode in self.episodes.values():
            all_action_desc = [
                act_step["english_action_text"]
                for act_step in episode["label_info"]["action_config"]
            ]
            episode["detailed_job_description"] = ";".join(all_action_desc)
        self.split_episode_by_rank()
        logger.info(f"Dataset {self.ds_name} load episodes {len(self.episodes)}.")

    def load_meta(self) -> None:
        for episode in self.episodes.values():
            meta_path = self.get_meta_info_path(episode)
            try:
                with open(meta_path, "r", encoding="utf-8") as fid:
                    episode["meta_info"] = json.load(fid)
            except FileNotFoundError:
                logger.error(f"Warning: Meta file not found at {meta_path}")
        logger.info(f"Dataset {self.ds_name} load meta {len(self.episodes)} finish.")

    def load_states(self, conventor) -> None:
        pbar = tqdm(total=len(self.episodes), desc="Load states")
        invalid_episodes = []
        for episode in self.episodes.values():
            state = {}
            state_file = self.get_state_path(episode)
            with h5py.File(state_file, "r") as fid:
                all_abs_joint = np.array(fid["state/joint/position"], dtype=np.float32)
                all_abs_effector = np.array(
                    fid[f"{self.effector_source}/effector/position"], dtype=np.float32
                )
                if all_abs_effector.shape[-1] == 2:
                    all_abs_gripper = all_abs_effector
                    state["left_arm_abs_gripper"] = all_abs_gripper[
                        :, : self.gripper_dof
                    ]
                    state["right_arm_abs_gripper"] = all_abs_gripper[
                        :, self.gripper_dof :
                    ]
                elif all_abs_effector.shape[-1] == 12:
                    all_abs_dexhand = all_abs_effector
                    state["left_arm_abs_dexhand"] = all_abs_dexhand[
                        :, : self.dexhand_dof
                    ]
                    state["right_arm_abs_dexhand"] = all_abs_dexhand[
                        :, self.dexhand_dof :
                    ]
                all_abs_head = np.array(fid["state/head/position"], dtype=np.float32)
                all_abs_waist = np.array(fid["state/waist/position"], dtype=np.float32)
                all_abs_base_vel = np.array(
                    fid["action/robot/velocity"], dtype=np.float32
                )
                all_abs_base_pos = np.array(
                    fid["state/robot/position"], dtype=np.float32
                )
                if "state/end/wrench" in fid:
                    use_wrench = True
                    all_abs_wrench = np.array(fid["state/end/wrench"], dtype=np.float32)
                    if len(all_abs_wrench) == 0:
                        use_wrench = False
                    else:
                        use_wrench = True
                else:
                    use_wrench = False

            state["left_arm_abs_joint"] = all_abs_joint[:, : self.joint_dof]
            state["right_arm_abs_joint"] = all_abs_joint[:, self.joint_dof :]
            state["head_abs_joint"] = all_abs_head
            if use_wrench:
                state["left_abs_wrench"] = all_abs_wrench[:, : self.wrench_dof]
                state["right_abs_wrench"] = all_abs_wrench[:, self.wrench_dof :]
            try:
                state["waist_abs_joint"] = all_abs_waist[:, 0:1]
                state["waist_abs_lift"] = all_abs_waist[:, 1:2]
            except Exception:
                state["waist_abs_joint"] = np.zeros_like(all_abs_joint)[:, :1]
                state["waist_abs_lift"] = np.zeros_like(all_abs_joint)[:, :1]

            try:
                state["base_linear_vel"] = all_abs_base_vel[:, 0:1]
                state["base_angular_vel"] = all_abs_base_vel[:, 1:2]
            except Exception:
                state["base_linear_vel"] = np.zeros_like(all_abs_joint)[:, :1]
                state["base_angular_vel"] = np.zeros_like(all_abs_joint)[:, :1]
            try:
                state["base_x_axis_pos"] = all_abs_base_pos[:, 0:1]
                state["base_y_axis_pos"] = all_abs_base_pos[:, 1:2]
            except Exception:
                state["base_x_axis_pos"] = np.zeros_like(all_abs_joint)[:, :1]
                state["base_y_axis_pos"] = np.zeros_like(all_abs_joint)[:, :1]
            if self.add_noise_to_state:
                state_noisy = {}
                for key, value in state.items():
                    std = np.std(value, axis=0)
                    state_noisy[key] = value + np.random.normal(
                        0, std / np.sqrt(10 ** (self.state_noise_snr / 10)), value.shape
                    )
                state = state_noisy

            all_left_eef = []
            all_right_eef = []
            if self.conventor_type == "ik_solver":
                conventor.reset()
            try:
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
            except Exception as e:
                logger.error(
                    f"[ERROR] episode {episode['episode_id']}, {self.get_episode_path(episode)}, error info: {e}"
                )
                invalid_episodes.append(int(episode["episode_id"]))
            pbar.update(1)
        for invalid_episode in invalid_episodes:
            del self.episodes[invalid_episode]
        pbar.close()

    def load_frames(self) -> None:
        for episode in self.episodes.values():
            action_config = episode["label_info"]["action_config"]
            last_frame_idx = max(step["end_frame"] for step in action_config)
            for action_idx, act_step in enumerate(action_config):
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
                            "action_idx": f"{action_idx}",
                        }
                    )
        if self.world_size is not None:
            self.frames = self.split_data_by_rank(self.frames)
            dist.barrier()
            original_length = len(self.frames)
            shard_num = torch.tensor(
                [original_length], dtype=torch.int64, device=torch.cuda.current_device()
            )
            dist.all_reduce(shard_num, op=dist.ReduceOp.MIN, async_op=False)
            shard_num = shard_num.cpu().item()
            self.frames = self.frames[:shard_num]

    def process_episode_transform(self) -> None:
        if not self.episode_transforms:
            return
        invalid_episodes = []
        for ep_id, ep in self.episodes.items():
            try:
                ep = self.episode_transforms(ep)
                self.episodes[ep_id] = ep
            except Exception:
                invalid_episodes.append(ep_id)
        for invalid_episode in invalid_episodes:
            del self.episodes[invalid_episode]

    def split_episode_by_rank(self, shuffle=True):
        episode_ids = [ep for ep in self.episodes.keys()]
        if self.world_size is not None and self.need_split_episode_by_rank:
            if shuffle:
                random.shuffle(episode_ids)
            sub_data_shard = {}
            for idx, episode_id in enumerate(episode_ids):
                if idx % self.world_size == self.rank_id:
                    sub_data_shard[episode_id] = self.episodes[episode_id]
            del episode_ids
            self.episodes = sub_data_shard

    def split_data_by_rank(self, data, shuffle=True):
        if self.world_size is not None and self.need_split_data_by_rank:
            if shuffle:
                random.shuffle(data)
            sub_data_shard = []
            for idx, info in enumerate(data):
                if idx % self.world_size == self.rank_id:
                    sub_data_shard.append(info)

            return sub_data_shard
        else:
            return data

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
        left_arm_hand_chunk = []
        right_arm_hand_chunk = []
        head_joint_chunk = []
        waist_joint_chunk = []
        waist_lift_chunk = []
        base_linear_vel_chunk = []
        base_angular_vel_chunk = []

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
            if (
                tag_name == "head_abs_joint"
                and use_delta
                and self.head_waist_norm_margin is not None
            ):
                target_action = np.clip(
                    target_action,
                    -np.array(self.head_waist_norm_margin[0]),
                    np.array(self.head_waist_norm_margin[0]),
                )
                target_action = (
                    target_action + np.array(self.head_waist_norm_margin[0])
                ) / (2 * np.array(self.head_waist_norm_margin[0]))

            if (
                tag_name in ["waist_abs_joint", "waist_abs_lift"]
                and use_delta
                and self.head_waist_norm_margin is not None
            ):
                head_waist_joint_norm = np.array(self.head_waist_norm_margin)
                if tag_name == "waist_abs_joint":
                    target_action = np.clip(
                        target_action,
                        -head_waist_joint_norm[1][0],
                        head_waist_joint_norm[1][0],
                    )
                    target_action = (target_action + head_waist_joint_norm[1][0]) / (
                        2 * head_waist_joint_norm[1][0]
                    )  # norm to 0 ~ 1
                else:
                    target_action = np.clip(
                        target_action,
                        -head_waist_joint_norm[1][1],
                        head_waist_joint_norm[1][1],
                    )
                    target_action = (target_action + head_waist_joint_norm[1][1]) / (
                        2 * head_waist_joint_norm[1][1]
                    )  # norm to 0 ~ 1

            if (
                tag_name in ["base_linear_vel", "base_angular_vel"]
                and self.base_vel_use_norm
                and self.base_vel_norm_margin is not None
            ):
                base_vel_norm = np.array(self.base_vel_norm_margin)
                idx = 0 if tag_name == "base_linear_vel" else 1
                target_action = np.clip(
                    target_action,
                    -base_vel_norm[idx],
                    base_vel_norm[idx],
                )
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

            if "left_arm_abs_dexhand" in state:
                left_arm_hand_chunk.append(
                    get_target_action(
                        state,
                        base_idx,
                        shift_idx,
                        "left_arm_abs_dexhand",
                        self.gripper_use_delta,
                    )
                )
            if "right_arm_abs_dexhand" in state:
                right_arm_hand_chunk.append(
                    get_target_action(
                        state,
                        base_idx,
                        shift_idx,
                        "right_arm_abs_dexhand",
                        self.gripper_use_delta,
                    )
                )
            head_joint_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "head_abs_joint",
                    self.head_waist_use_delta,
                )
            )
            waist_joint_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "waist_abs_joint",
                    self.head_waist_use_delta,
                )
            )
            waist_lift_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "waist_abs_lift",
                    self.head_waist_use_delta,
                )
            )
            base_linear_vel_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "base_linear_vel",
                    self.gripper_use_delta,
                )
            )
            base_angular_vel_chunk.append(
                get_target_action(
                    state,
                    base_idx,
                    shift_idx,
                    "base_angular_vel",
                    self.gripper_use_delta,
                )
            )
        action_target = {
            "left_arm_joint_positions": np.array(left_arm_joint_chunk),
            "right_arm_joint_positions": np.array(right_arm_joint_chunk),
            "left_end_effector_6d_pose": np.array(left_effector_pose_chunk),
            "right_end_effector_6d_pose": np.array(right_effector_pose_chunk),
            "head_joint_positions": np.array(head_joint_chunk),
            "waist_joint_positions": np.array(waist_joint_chunk),
            "waist_lift_positions": np.array(waist_lift_chunk),
            "base_linear_velocities": np.array(base_linear_vel_chunk),
            "base_angular_velocities": np.array(base_angular_vel_chunk),
        }
        if len(left_arm_gripper_chunk) > 0 and len(right_arm_gripper_chunk) > 0:
            action_target.update(
                {
                    "left_gripper_joint_positions": np.array(left_arm_gripper_chunk),
                    "right_gripper_joint_positions": np.array(right_arm_gripper_chunk),
                }
            )
        if len(left_arm_hand_chunk) > 0 and len(right_arm_hand_chunk) > 0:
            action_target.update(
                {
                    "left_dexterous_hand_positions": np.array(left_arm_hand_chunk),
                    "right_dexterous_hand_positions": np.array(right_arm_hand_chunk),
                }
            )
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
            "base_linear_velocities": state["base_linear_vel"][
                current_idx : current_idx + 1
            ],
            "base_angular_velocities": state["base_angular_vel"][
                current_idx : current_idx + 1
            ],
        }
        if "left_abs_wrench" in state:
            agent_state.update(
                {
                    "left_abs_wrench": state["left_abs_wrench"][
                        current_idx : current_idx + 1
                    ],
                }
            )
        if "right_abs_wrench" in state:
            agent_state.update(
                {
                    "right_abs_wrench": state["right_abs_wrench"][
                        current_idx : current_idx + 1
                    ],
                }
            )

        if "left_arm_abs_gripper" in state and "right_arm_abs_gripper" in state:
            agent_state.update(
                {
                    "left_gripper_joint_positions": state["left_arm_abs_gripper"][
                        current_idx : current_idx + 1
                    ],
                    "right_gripper_joint_positions": state["right_arm_abs_gripper"][
                        current_idx : current_idx + 1
                    ],
                }
            )
        if "left_arm_abs_dexhand" in state and "right_arm_abs_dexhand" in state:
            agent_state.update(
                {
                    "left_dexterous_hand_positions": state["left_arm_abs_dexhand"][
                        current_idx : current_idx + 1
                    ],
                    "right_dexterous_hand_positions": state["right_arm_abs_dexhand"][
                        current_idx : current_idx + 1
                    ],
                }
            )
        sample["action_target"] = action_target
        sample["agent_state"] = agent_state

    def get_prompt(self, sample: dict) -> str:
        episode_id = int(sample["episode_id"])
        episode_info = self.episodes[episode_id]
        detailed_job_description = episode_info["detailed_job_description"]
        job_description = episode_info["english_task_name"]
        action_idx = int(sample["action_idx"])
        action_config = episode_info["label_info"]["action_config"][action_idx]
        sub_job_description = action_config["english_action_text"]

        prompt_mode = random.choice(self.prompt_mode_list)
        if prompt_mode == 0:
            prompt = f"What action should the robot take to {job_description}?"
        elif prompt_mode == 1:
            prompt = f"The robot is performing the step of {sub_job_description}."
        elif prompt_mode == 2:
            prompt = f"What action should the robot take to {job_description}? The robot is performing the step of {sub_job_description}."
        elif prompt_mode == 3:
            prompt = f"The robot is performing the step of {detailed_job_description}?"
        elif prompt_mode == 4:
            prompt = f"What action should the robot take to {job_description}? Place the items in the material box in front of items with the same appearance on the shelves."
        else:
            raise IndexError(f"invalid prompt_mode: {prompt_mode}")
        return prompt

    def get_token(self, sample: dict, num_tiles: list[int], num_patches: int) -> dict:
        final_prompt = self.get_prompt(sample)
        num_image = len(self.use_cam_list)
        num_image_tokens = [self.num_image_token * num_tile for num_tile in num_tiles]
        conversation = [
            {
                "from": "human",
                "value": f"{'<image>' * num_image}{final_prompt}",
            },
            {"from": "gpt", "value": ""},
        ]
        ret = preprocess_internlm(
            "internlm2-chat",
            [conversation],
            self.text_tokenizer,
            num_image_tokens,
            num_image=num_image,
            group_by_length=True,
        )
        position_ids = ret["attention_mask"].long().cumsum(-1) - 1
        position_ids.masked_fill_(ret["attention_mask"] == 0, 1)

        ret = dict(
            input_ids=ret["input_ids"][0],
            attention_mask=ret["attention_mask"][0],
            position_ids=position_ids[0],
            image_flags=torch.tensor([1] * num_patches, dtype=torch.long),
        )
        return ret

    def sample_frame(self):
        frame_sampled = []
        for idx, item in enumerate(self.frames):
            if idx % self.sample_rate == 0:
                frame_sampled.append(item)
        del self.frames
        self.frames = None
        self.frames = frame_sampled

    def shuffle_sample(self):
        random.shuffle(self.frames)

    def decode_video_frame(self, episode_info, cam_name, frame_idx):
        video_path = self.get_video_path(episode_info, cam_name)
        if "head_color" in video_path:
            decoded_frame = self.head_decoder.decode(video_path, frame_idx)
        else:
            decoded_frame = self.decoder.decode(video_path, frame_idx)
        (height, width) = decoded_frame.shape
        # print(f"{video_path}, shape:{height},{width}", flush=True)
        src_tensor = torch.from_dlpack(decoded_frame)
        rgb_tensor = nv12_to_rgb(src_tensor, width, int(height / 1.5))
        rgb_tensor = rgb_tensor.cpu().numpy()
        return rgb_tensor

    def decode_img_frame(self, episode_info, cam_name, frame_idx):
        cam_file_path = os.path.join(
            self.get_episode_path(episode_info),
            "camera",
            str(frame_idx),
            cam_name + "_color.jpg",
        )
        img = Image.open(cam_file_path).convert("RGB")
        rgb_tenfor = np.array(img)
        return rgb_tenfor

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
        sample = copy.deepcopy(raw_sample)
        episode_id = int(sample["episode_id"])
        episode_info = self.episodes[episode_id]

        if not self.decoder:
            self.decoder = VideoDecoder(self.device_id, self.codec)
        if not self.head_decoder:
            self.head_decoder = VideoDecoder(self.device_id, self.codec)

        self.get_action_and_state(sample)

        images = []
        for cam_name in self.use_cam_list:
            rgb_tensor = self.decode_video_frame(
                episode_info, cam_name, int(sample["frame_idx"])
            )
            img = Image.fromarray(rgb_tensor, "RGB")
            images.append(img)
        sample["images"] = images
        if self.use_depth:
            depth_path = os.path.join(
                self.get_episode_path(episode_info),
                "camera",
                sample["frame_idx"],
                "head_depth.png",
            )
            depth_tensor = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED).astype(
                np.float64
            )
            depth_tensor = cv2.resize(depth_tensor, self.depth_size).reshape(
                1, self.depth_size[0], self.depth_size[1]
            )
            depth_tensor = (depth_tensor / 1000.0).clip(0, 3) / 3
            depth_tensor = torch.tensor(
                depth_tensor[None].repeat(3, axis=1), dtype=torch.float32
            )
            sample["depth_tensor_head_depth"] = depth_tensor
        img = self.decode_video_frame(episode_info, "head", int(sample["frame_idx"]))
        img = Image.fromarray(img, "RGB")
        img_k = self.decode_video_frame(episode_info, "head", int(sample["target_idx"]))
        img_k = Image.fromarray(img_k, "RGB")
        initial_pixel_values = build_latent_image_transform()(img)
        target_pixel_values = build_latent_image_transform()(img_k)
        initial_pixel_values = torch.from_numpy(
            np.array(initial_pixel_values).astype(np.float32) / 255.0
        ).permute(2, 0, 1)
        target_pixel_values = torch.from_numpy(
            np.array(target_pixel_values).astype(np.float32) / 255.0
        ).permute(2, 0, 1)
        video = torch.stack(
            [initial_pixel_values, target_pixel_values], dim=0
        ).unsqueeze(0)
        sample["videos"] = video

        if self.transforms:
            sample = self.transforms(sample)

        if not self.use_latent_action:
            if "left_gripper_joint_positions" in sample["agent_state"]:
                sample["agent_state"].pop("left_gripper_joint_positions")
            if "right_gripper_joint_positions" in sample["agent_state"]:
                sample["agent_state"].pop("right_gripper_joint_positions")
            if "base_linear_velocities" in sample["agent_state"]:
                sample["agent_state"].pop("base_linear_velocities")
            if "base_angular_velocities" in sample["agent_state"]:
                sample["agent_state"].pop("base_angular_velocities")
            action, action_mask = self.ActionSpacePadder.get_action(
                sample["action_target"], chunk_size=self.action_chunk_size
            )
            state, state_mask = self.ActionSpacePadder.get_state(
                sample["agent_state"], chunk_size=1
            )
        else:
            action, action_mask = self.ActionSpacePadder.get_action(
                {}, chunk_size=self.action_chunk_size
            )
            state, state_mask = self.ActionSpacePadder.get_state({}, chunk_size=1)
        agent_state = torch.tensor(state, dtype=torch.float32)
        if not self.use_real_state:
            agent_state = -1 * torch.ones_like(agent_state)

        img_transform = build_transform(
            is_train=self.is_train,
            input_size=self.image_size,
            pad2square=self.pad2square,
            normalize_type=self.normalize_type,
        )
        images, num_tiles = [], []
        if self.dynamic_image_size:
            for img in sample["images"]:
                image = dynamic_preprocess(
                    img,
                    min_num=self.min_dynamic_patch,
                    max_num=self.max_dynamic_patch,
                    image_size=self.image_size,
                    use_thumbnail=self.use_thumbnail,
                )
                images += image
                num_tiles.append(len(image))
        else:
            images = sample["images"]
            num_tiles = [1] * len(images)
        pixel_values = [img_transform(image) for image in images]
        pixel_values = torch.stack(pixel_values)
        num_patches = pixel_values.size(0)
        results = self.get_token(sample, num_tiles, num_patches)
        freq = torch.tensor([30.0], dtype=torch.float32)
        results.update(
            {
                "action_gts": torch.tensor(action, dtype=torch.float32),
                "action_mask": torch.tensor(action_mask, dtype=torch.float32)
                if self.use_action_mask
                else None,
                "state": agent_state,
                "state_mask": (
                    torch.tensor(state_mask, dtype=torch.float32)
                    if self.use_action_mask
                    else None
                ),
                "pixel_values": pixel_values,
                "ctrl_freqs": freq,
                "task_ids": torch.tensor(
                    [int(episode_info["task_id"])], dtype=torch.int32
                ),
            }
        )
        if "videos" in sample:
            results["videos"] = sample["videos"]
        if "depth_tensor_head_depth" in sample:
            results["depth_values"] = sample["depth_tensor_head_depth"]
        results.update(
            {"episode_id": episode_id, "frame_idx": int(sample["frame_idx"])}
        )
        return results

    def __del__(self):
        if self.head_decoder:
            del self.head_decoder
        if self.decoder:
            del self.decoder


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
