import copy
import random
import numpy as np

from typing import Dict, Tuple
from imgaug import augmenters
from torchvision import transforms
from PIL import Image


class EpisodeProcessorRelableStaticFrames:
    """Remove static frames at the start and end of the episode according to the joint values."""

    def __init__(
        self,
        threshold: Dict[str, float] = {
            "arm": np.pi / 180 / 30,
            "head": 0.01,
            "waist": 0.01,
            "base": 0.01,
        },
    ):
        self.threshold = threshold

    def _get_arm_range(self, episode_info) -> Tuple[int, int]:
        arm_abs_joint: np.ndarray = np.c_[
            episode_info["state"]["left_arm_abs_joint"],
            episode_info["state"]["right_arm_abs_joint"],
        ]
        arm_abs_joint_sum = arm_abs_joint.sum(axis=1)
        arm_abs_joint_diff = np.abs(np.diff(arm_abs_joint_sum))

        start_idx, end_idx = 0, len(arm_abs_joint_diff) - 1

        for i in range(len(arm_abs_joint_diff) - 1):
            if arm_abs_joint_diff[i] >= self.threshold["arm"]:
                start_idx = i
                break

        for j in range(len(arm_abs_joint_diff) - 1, 0, -1):
            if arm_abs_joint_diff[j] >= self.threshold["arm"]:
                end_idx = j
                break

        end_idx += 1
        if start_idx > end_idx:
            raise ValueError(
                f"[EpisodeProcessorRelableStaticFrames] episode {episode_info['spisode_id']} has no dynamic frames!"
            )
        return start_idx, end_idx

    def _get_head_range(self, episode_info):
        head_abs_joint = copy.deepcopy(episode_info["state"]["head_abs_joint"])
        head_abs_joint_sum = head_abs_joint.sum(axis=1)
        head_abs_joint_diff = np.abs(np.diff(head_abs_joint_sum))
        start_idx, end_idx = 0, len(head_abs_joint_diff) - 1

        for i in range(len(head_abs_joint_diff) - 1):
            if head_abs_joint_diff[i] >= self.threshold["head"]:
                start_idx = i
                break
        for j in range(len(head_abs_joint_diff) - 1, 0, -1):
            if head_abs_joint_diff[j] >= self.threshold["head"]:
                end_idx = j
                break

        end_idx += 1
        return start_idx, end_idx

    def _get_waist_range(self, episode_info):
        waist_abs_joint: np.ndarray = np.c_[
            episode_info["state"]["waist_abs_joint"],
            episode_info["state"]["waist_abs_lift"],
        ]
        waist_abs_joint_sum = waist_abs_joint.sum(axis=1)
        waist_abs_joint_diff = np.abs(np.diff(waist_abs_joint_sum))
        start_idx, end_idx = 0, len(waist_abs_joint_diff) - 1
        for i in range(len(waist_abs_joint_diff) - 1):
            if waist_abs_joint_diff[i] >= self.threshold["waist"]:
                start_idx = i
                break
        for j in range(len(waist_abs_joint_diff) - 1, 0, -1):
            if waist_abs_joint_diff[j] >= self.threshold["waist"]:
                end_idx = j
                break

        end_idx += 1
        return start_idx, end_idx

    def _get_base_range(self, episode_info):
        base_val: np.ndarray = np.c_[
            episode_info["state"]["base_linear_vel"],
            episode_info["state"]["base_angular_vel"],
        ]
        base_vel_sum = base_val.sum(axis=1)
        base_vel_sum_diff = np.abs(np.diff(base_vel_sum))
        start_idx, end_idx = 0, len(base_vel_sum_diff) - 1
        for i in range(len(base_vel_sum_diff) - 1):
            if base_vel_sum_diff[i] >= self.threshold["base"]:
                start_idx = i
                break

        for j in range(len(base_vel_sum_diff) - 1, 0, -1):
            if base_vel_sum_diff[j] >= self.threshold["base"]:
                end_idx = j
                break
        end_idx += 1
        return start_idx, end_idx

    def __call__(self, episode_info):
        if "arm" in self.threshold:
            start_idx_arm, end_idx_arm = self._get_arm_range(episode_info)
        else:
            start_idx_arm, end_idx_arm = (
                0,
                len(episode_info["state"]["left_arm_abs_joint"]) - 1,
            )

        if "head" in self.threshold:
            start_idx_head, end_idx_head = self._get_head_range(episode_info)
        else:
            start_idx_head, end_idx_head = (
                0,
                len(episode_info["state"]["head_abs_joint"]) - 1,
            )

        if "waist" in self.threshold:
            start_idx_waist, end_idx_waist = self._get_waist_range(episode_info)
        else:
            start_idx_waist, end_idx_waist = (
                0,
                len(episode_info["state"]["waist_abs_joint"]) - 1,
            )

        if "base" in self.threshold:
            start_idx_base, end_idx_base = self._get_base_range(episode_info)
        else:
            start_idx_base, end_idx_base = (
                0,
                len(episode_info["state"]["base_linear_vel"]) - 1,
            )

        start_idx = min(start_idx_arm, start_idx_head, start_idx_waist, start_idx_base)
        end_idx = max(end_idx_arm, end_idx_head, end_idx_waist, end_idx_base)

        if episode_info["label_info"]["action_config"][0]["start_frame"] < start_idx:
            episode_info["label_info"]["action_config"][0]["start_frame"] = start_idx
        if episode_info["label_info"]["action_config"][-1]["end_frame"] > end_idx:
            episode_info["label_info"]["action_config"][-1]["end_frame"] = end_idx

        return episode_info


class RuntimeImageResize:
    def __init__(self, size=(224, 224)):
        # image shape: [C,H,W]
        self.source_key = "cam_tensor_"
        self.size = size

    def __call__(self, inputs):
        keys = list(inputs.keys())
        for key in keys:
            if self.source_key in key:
                img = inputs[key].resize(self.size)
                inputs[key] = img

        return inputs


class RuntimeImageAugColorJitter:
    def __init__(
        self,
        prob_to_process=0.5,
        brightness=0.3,
        contrast=0.4,
        saturation=0.5,
        hue=0.03,
    ):
        self.prob_to_process = prob_to_process
        self.source_key = "cam_tensor_"
        self.color_jitter = transforms.ColorJitter(
            brightness=brightness, contrast=contrast, saturation=saturation, hue=hue
        )

    def __call__(self, inputs):
        keys = list(inputs.keys())
        for key in keys:
            if self.source_key in key:
                if random.random() < self.prob_to_process:
                    img = self.color_jitter(inputs[key])
                    inputs[key] = img

        return inputs


class RuntimeActionNorm:
    def __init__(self, norm_keys=None, params=None, max_value=1, min_value=-1):
        self.norm_keys = norm_keys
        self.max = max_value
        self.min = min_value
        self.params = np.array(params, dtype=np.float32)

    def __call__(self, sample):
        for key, value in sample["action_target"].items():
            if key in self.norm_keys:
                sample["action_target"][key] = np.clip(
                    value * self.params, self.min, self.max
                )

        return sample


class RuntimeImageAugCorrupt:
    def __init__(self, prob_to_process=0.5):
        self.prob_to_process = prob_to_process
        self.source_key = "cam_tensor_"
        # Define our sequence of augmentation steps that will be applied to every image.
        self.seq = augmenters.Sequential(
            [
                # Execute one of the following noise augmentations
                augmenters.OneOf(
                    [
                        augmenters.AdditiveGaussianNoise(
                            loc=0, scale=(0.0, 0.05 * 255), per_channel=0.5
                        ),
                        augmenters.AdditiveLaplaceNoise(
                            scale=(0.0, 0.05 * 255), per_channel=0.5
                        ),
                        augmenters.AdditivePoissonNoise(
                            lam=(0.0, 0.05 * 255), per_channel=0.5
                        ),
                    ]
                ),
                # Execute one or none of the following blur augmentations
                augmenters.SomeOf(
                    (0, 1),
                    [
                        augmenters.OneOf(
                            [
                                # iaa.GaussianBlur((0, 3.0)),
                                augmenters.AverageBlur(k=(2, 7)),
                                # iaa.MedianBlur(k=(3, 11)),
                            ]
                        ),
                        # iaa.MotionBlur(k=(5, 7)),
                    ],
                ),
            ],
            # do all of the above augmentations in random order
            random_order=True,
        )

    def __call__(self, inputs):
        keys = list(inputs.keys())
        for key in keys:
            if self.source_key in key:
                if random.random() < self.prob_to_process:
                    image_arr = self.seq(images=np.array(inputs[key]))
                    inputs[key] = Image.fromarray(image_arr)

        return inputs


class RuntimeImageAugRandomDropImage:
    def __init__(
        self,
        prob_to_process=[0.1, 0.1, 0.1],
        images=[
            "cam_tensor_head_color",
            "cam_tensor_hand_right_color",
            "cam_tensor_hand_left_color",
        ],
    ):
        self.prob_to_process = prob_to_process
        self.images = images
        IMAGENET_MEAN = (0.485, 0.456, 0.406)
        self.image_mean = IMAGENET_MEAN

    def drop_image(self, img):
        background_color = np.array(
            [int(x * 255) for x in self.image_mean], dtype=np.uint8
        ).reshape(1, 1, 3)
        background_image = (
            np.ones((img.shape[0], img.shape[1], 3), dtype=np.uint8) * background_color
        )
        return background_image

    def __call__(self, inputs):
        for i, input_image in enumerate(self.images):
            if input_image in inputs:
                if random.random() < self.prob_to_process[i]:
                    img = np.array(inputs[input_image])

                    background_image = self.drop_image(img)
                    inputs[input_image] = Image.fromarray(background_image)
        return inputs


episode_transform = transforms.Compose([EpisodeProcessorRelableStaticFrames()])


runtime_transform = transforms.Compose(
    [
        RuntimeImageResize(size=(448, 448)),
        RuntimeImageAugColorJitter(prob_to_process=0.33),
        RuntimeImageAugCorrupt(prob_to_process=0.33),
        RuntimeImageAugRandomDropImage(prob_to_process=[0.1, 0.1, 0.1]),
        RuntimeActionNorm(
            norm_keys=["left_end_effector_6d_pose", "right_end_effector_6d_pose"],
            params=[166 * 2, 106 * 2, 142 * 2, 27 * 2, 38 * 2, 23 * 2],
            max_value=1,
            min_value=-1,
        ),
    ]
)
