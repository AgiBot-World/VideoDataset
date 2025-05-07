import random
import numpy as np

from imgaug import augmenters
from torchvision import transforms
from PIL import Image


class EpisodeProcessorRelableStaticFrames:
    """Remove static frames at the start and end of the episode according to the joint values."""

    def __init__(self, threshold: float = np.pi / 180 / 30):
        self.threshold = threshold

    def __call__(self, episode_info):
        arm_abs_joint: np.ndarray = np.c_[
            episode_info["state"]["left_arm_abs_joint"],
            episode_info["state"]["right_arm_abs_joint"],
        ]
        arm_abs_joint_sum = arm_abs_joint.sum(axis=1)
        arm_abs_joint_diff = np.abs(np.diff(arm_abs_joint_sum))

        start_idx, end_idx = 0, len(arm_abs_joint_diff) - 1

        for i in range(len(arm_abs_joint_diff) - 1):
            if arm_abs_joint_diff[i] >= self.threshold:
                start_idx = i
                break

        for j in range(len(arm_abs_joint_diff) - 1, 0, -1):
            if arm_abs_joint_diff[j] >= self.threshold:
                end_idx = j
                break

        end_idx += 1
        if start_idx > end_idx:
            raise ValueError(
                f"[EpisodeProcessorRelableStaticFrames] episode {episode_info['spisode_id']} has no dynamic frames!"
            )
        if episode_info["label_info"]["action_config"][0]["start_frame"] < start_idx:
            episode_info["label_info"]["action_config"][0]["start_frame"] = start_idx
        if episode_info["label_info"]["action_config"][-1]["end_frame"] > end_idx:
            episode_info["label_info"]["action_config"][-1]["end_frame"] = end_idx
        return episode_info


class RuntimeImageResize:
    def __init__(self, size=(224, 224)):
        # image shape: [C,H,W]
        self.size = size

    def __call__(self, sample):
        images = sample["images"]
        new_images = []
        for image in images:
            img = image.resize(self.size)
            new_images.append(img)
        sample["images"] = new_images
        return sample


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
        self.color_jitter = transforms.ColorJitter(
            brightness=brightness, contrast=contrast, saturation=saturation, hue=hue
        )

    def __call__(self, sample):
        images = sample["images"]
        new_images = []
        for image in images:
            if random.random() < self.prob_to_process:
                img = self.color_jitter(image)
                new_images.append(img)
            else:
                new_images.append(image)
        sample["images"] = new_images
        return sample


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

    def __call__(self, sample):
        images = sample["images"]
        new_images = []
        for image in images:
            if random.random() < self.prob_to_process:
                image_arr = self.seq(images=np.array(image))
                new_images.append(Image.fromarray(image_arr))
            else:
                new_images.append(image)
        sample["images"] = new_images
        return sample


class RuntimeImageAugRandomDropImage:
    def __init__(
        self,
        prob_to_process=[0.1, 0.1, 0.1],
    ):
        self.prob_to_process = prob_to_process
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

    def __call__(self, sample):
        images = sample["images"]
        new_images = []
        for i, image in enumerate(images):
            if random.random() < self.prob_to_process[i]:
                img = np.array(image)
                background_image = self.drop_image(img)
                new_images.append(Image.fromarray(background_image))
            else:
                new_images.append(image)
        sample["images"] = new_images
        return sample


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
