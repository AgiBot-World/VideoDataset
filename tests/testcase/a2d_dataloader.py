import os
import time
import torch
import argparse
import multiprocessing as mp

from torch import nn
from torch.utils.data import DataLoader
from pathlib import Path
from transformers import AutoTokenizer
from videodataset.dataset import A2dVideoDataset
from videodataset.dataset.a2d_video import ActionSpacePadder
from videodataset.dataset.a2d_transform import runtime_transform, episode_transform


# 定义简单模型
class SimpleModel(nn.Module):
    def __init__(self):
        super(SimpleModel, self).__init__()
        self.flatten = nn.Flatten()
        self.linear = nn.Linear(3 * 3 * 448 * 448, 2)
        self.loss_fn = nn.CrossEntropyLoss()

    def forward(self, pixel_values, labels=None):
        x = self.flatten(pixel_values)
        logits = self.linear(x)
        loss = None
        if labels is not None:
            loss = self.loss_fn(logits, labels)
        return loss, logits


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


def collate_fn(batch):
    batch = [
        {"pixel_values": item["pixel_values"]} for item in batch if item is not None
    ]
    if len(batch) == 0:
        raise ValueError("Batch is empty after filtering None values.")
    return torch.utils.data.dataloader.default_collate(batch)


def main(worker_num):
    parent_dir = Path(__file__).parent.parent
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
        shuffle=True,
        actionSpacePadder=ActionSpacePadderArguments(),
    )

    spawn_ctx = mp.get_context("spawn")
    train_loader = DataLoader(
        dataset,
        batch_size=16,
        shuffle=True,
        num_workers=worker_num,
        persistent_workers=True,
        drop_last=True,
        multiprocessing_context=spawn_ctx,
        collate_fn=collate_fn,
    )

    model = SimpleModel()
    model.to("cuda")
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    start = time.time()
    total_epoch = 1
    for epoch in range(total_epoch):  # 训练10个epoch
        total_loss = 0
        for batch_idx, data in enumerate(train_loader):
            # labels = labels.to("cuda").long()
            optimizer.zero_grad()
            loss, logits = model(
                data["pixel_values"].to("cuda"),
                torch.randint(0, 2, (16,), dtype=torch.int32).to("cuda").long(),
            )
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            if batch_idx % 100 == 0:
                print(f"Epoch: {epoch} | Batch: {batch_idx} | Loss: {loss.item():.4f}")
    end = time.time()
    FPS = len(dataset) * total_epoch / (end - start)
    print(f"FPS: {FPS} f/s.", flush=True)
    return FPS


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Test single process video decoder.")
    parser.add_argument("-n", "--worker", default=4, type=int, help="Worker number.")
    args = parser.parse_args()
    main(args.worker)
    time.sleep(3)
