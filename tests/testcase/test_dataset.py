import os
import torch
from pathlib import Path
import pytest

from transformers import AutoTokenizer
from videodataset.dataset import A2dVideoDataset
from videodataset.dataset.a2d_video import ActionSpacePadder
from videodataset.dataset.a2d_transform import runtime_transform, episode_transform


@pytest.fixture
def parent_dir(request):
    parent_dir = os.environ.get("TEST_PARENT_DIR")
    if parent_dir:
        return Path(parent_dir)
    return Path(__file__).parent.parent


class ActionSpacePadderArguments(ActionSpacePadder):
    action_space_used: list = [
        # "LEFT_ARM_JOINT_POSITIONS",
        "LEFT_END_EFFECTOR_6D_POSE",
        "LEFT_GRIPPER_JOINT_POSITIONS",
        "RIGHT_END_EFFECTOR_6D_POSE",
        "RIGHT_GRIPPER_JOINT_POSITIONS",
    ]
    state_space_used: list = [
        # "RIGHT_END_EFFECTOR_6D_POSE",
        # "RIGHT_GRIPPER_JOINT_POSITIONS",
        # "RIGHT_ARM_JOINT_POSITIONS",
        # "RIGHT_END_EFFECTOR_6D_POSE",
        # "RIGHT_GRIPPER_JOINT_POSITIONS",
    ]


ActionSpacePadderArguments.get_space()


def test_dataset(parent_dir):
    label_file_dir = os.path.join(parent_dir, "testdata", "labels")
    data_root_dir = os.path.join(parent_dir, "testdata", "data")
    tokenizer_path = os.path.join(parent_dir, "testdata", "model")

    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_path, add_eos_token=False, trust_remote_code=True, use_fast=False
    )
    dataset = A2dVideoDataset(
        ds_name="Test",
        label_file_dir=label_file_dir,
        data_root_dir=data_root_dir,
        tasks={"640": {"label_file_name": "task_640_train.json"}},
        episode_transforms=episode_transform,
        transforms=runtime_transform,
        text_tokenizer=tokenizer,
        sample_rate=700,
        shuffle=True,
        actionSpacePadder=ActionSpacePadderArguments(),
    )

    assert len(dataset.episodes) == 2
    assert len(dataset) == 11

    num = 0
    for sample in dataset:
        sample = dataset[num]
        missing = [
            field
            for field in [
                "action_gts",
                "state",
                "action_mask",
                "input_ids",
                "position_ids",
                "pixel_values",
                "image_flags",
                "ctrl_freqs",
                "action_mask",
            ]
            if field not in sample
        ]
        assert not missing, f"Missing required fields: {missing}"
        action_gts = sample["action_gts"]
        state = sample["state"]
        input_ids = sample["input_ids"]
        attention_mask = sample["attention_mask"]
        position_ids = sample["position_ids"]
        pixel_values = sample["pixel_values"]
        image_flags = sample["image_flags"]
        ctrl_freqs = sample["ctrl_freqs"]
        action_mask = sample["action_mask"]

        assert action_gts.dtype == torch.float32, (
            f"action_gts dtype error {action_gts.dtype}"
        )
        assert action_gts.shape == (30, 14), (
            f"action_gts shape error {action_gts.shape}"
        )

        assert state.dtype == torch.float32, f"state dtype error {state.dtype}"
        assert state.shape == (1, 14), f"state shape error {state.shape}"

        assert input_ids.dtype == torch.int64, (
            f"input_ids dtype error {input_ids.dtype}"
        )
        assert input_ids.shape == (829,), f"input_ids shape error {input_ids.shape}"

        assert attention_mask.dtype == torch.bool, (
            f"attention_mask dtype error {attention_mask.dtype}"
        )
        assert attention_mask.shape == (829,), (
            f"attention_mask shape error {attention_mask.shape}"
        )

        assert position_ids.dtype == torch.int64, (
            f"position_ids dtype error {position_ids.dtype}"
        )
        assert position_ids.shape == (829,), (
            f"position_ids shape error {position_ids.shape}"
        )
        assert input_ids.shape == attention_mask.shape
        assert input_ids.shape == position_ids.shape

        assert pixel_values.dtype == torch.float32, (
            f"pixel_values dtype error {pixel_values.dtype}"
        )
        assert pixel_values.shape == (3, 3, 448, 448), (
            f"pixel_values shape error {pixel_values.shape}"
        )

        assert image_flags.dtype == torch.int64, (
            f"image_flags dtype error {image_flags.dtype}"
        )
        assert image_flags.shape == (3,), f"image_flags shape error {image_flags.shape}"

        assert ctrl_freqs.dtype == torch.float32, (
            f"ctrl_freqs dtype error {ctrl_freqs.dtype}"
        )
        assert ctrl_freqs.shape == (1,), f"ctrl_freqs shape error {ctrl_freqs.shape}"

        assert action_mask is None, "action_mask is None"

        num += 1
        if num > 10:
            break


if __name__ == "__main__":
    test_dataset(Path(__file__).parent.parent)
