from __future__ import annotations

import logging
from typing import Any

import torch
from lerobot.datasets.lerobot_dataset import LeRobotDataset # type: ignore

from videodataset.dataset.base_dataset import BaseVideoDataset

logger = logging.getLogger(__name__)


class LeRobotVideoDataset(LeRobotDataset, BaseVideoDataset):
    """
    GPU-accelerated LeRobot dataset using NVDEC decoder.

    This class provides a drop-in replacement for LeRobotDataset with:
    - GPU-accelerated video decoding
    - Improved performance for large-scale training
    - Compatible with all LeRobot dataset formats
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        BaseVideoDataset.__init__(self)
        logger.info(
            "Initialized %s with args=%s, kwargs=%s",
            self.__class__.__name__,
            args,
            kwargs,
        )

    def _query_videos(
        self, query_timestamps: dict[str, list[float]], ep_idx: int
    ) -> dict[str, torch.Tensor]:
        """
        Query and decode video frames for given timestamps.

        This method is invoked by the dataset's __getitem__().
        Uses GPU-accelerated decoding with proper error handling and validation.

        Args:
            query_timestamps: Dictionary mapping video keys to lists of query timestamps
            ep_idx: Episode index

        Returns:
            Dictionary mapping video keys to decoded frame tensors

        Note:
            - support num_workers > 0 with the following prerequisites:
                - Multiprocessing context must be set to 'spawn'
                - Decoder instances must be created outside the dataset constructor

        """
        item = {}

        for vid_key, query_ts in query_timestamps.items():
            try:
                video_path = self.root / self.meta.get_video_file_path(ep_idx, vid_key)
                video_meta = self.meta.info["features"][vid_key]
                resolution, codec = (
                    video_meta["shape"],
                    self._get_codec(video_meta),
                )
                decoder_key = f"{resolution}_{codec}"
                decoder = self.get_decoder(decoder_key, codec)

                frames_list = []
                for ts in query_ts:
                    frame_idx = int(ts * self.fps)
                    decoded_frame = self.decode_video_frame(
                        decoder, video_path, frame_idx
                    )
                    decoded_frame = self._format_frame_tensor(decoded_frame, vid_key)
                    frames_list.append(decoded_frame)

                # Stack frames and ensure proper shape
                frames = torch.stack(frames_list)  # Shape: [T, C, H, W]

                # Decoder [0,255] uint8, convert to [0,1] if needed
                if frames.dtype != torch.float32:
                    frames = frames.float() / 255.0

                item[vid_key] = frames.squeeze(0)
            except Exception as e:
                logger.error(
                    "Error processing video %s at episode %d: %s",
                    vid_key,
                    ep_idx,
                    e,
                )
                msg = f"Failed to process video {vid_key}"
                raise RuntimeError(msg) from e
        return item

    def _format_frame_tensor(
        self, frame_tensor: torch.Tensor, vid_key: str
    ) -> torch.Tensor:
        """
        Format the frame tensor to ensure it has 3 channels and is in (C, H, W) format.

        Args:
            frame_tensor: The decoded frame tensor
            vid_key: Video key for logging

        Returns:
            Formatted frame tensor
        """
        if frame_tensor.dim() == 3 and frame_tensor.shape[0] == 3:
            return frame_tensor
        if frame_tensor.dim() == 3 and frame_tensor.shape[-1] == 3:
            return frame_tensor.permute(2, 0, 1)
        logger.error("Unexpected tensor shape for %s: %s", vid_key, frame_tensor.shape)
        msg = (
            f"Unexpected tensor shape for {vid_key}: {frame_tensor.shape}. "
            "Expected (C, H, W) or (H, W, C) with 3 channels."
        )
        raise ValueError(msg)

    def _get_codec(self, video_meta: dict) -> str:
        """Helper method to return the codec based on the video meta info"""
        possible_keys = ["info", "video_info"]

        for key in possible_keys:
            if key in video_meta:
                return video_meta[key]["video.codec"]

        msg = (
            f"Codec not found. Expected one of {possible_keys} in video_meta, "
            f"check info.json in your dataset for details"
        )
        raise KeyError(msg)
