from __future__ import annotations

import logging
from pathlib import Path

import torch

from videodataset import VideoDecoder
from videodataset.utils.video_util import nv12_to_rgb

logger = logging.getLogger(__name__)


class BaseVideoDataset:
    """Deooder extension that defines decoder specific funtionalities"""

    def __init__(
        self,
    ) -> None:
        self.decoders: dict[str, VideoDecoder] = {}

        if torch.cuda.is_available():
            self.device_id = torch.cuda.current_device()
        else:
            raise RuntimeError(
                "No cuda device found, accelerated decoding is not available"
            )

    @property
    def device(self):
        return self.device_id

    @property
    def num_decoders(self):
        return len(self.decoders)

    def get_decoder(self, decoder_key: str, codec: str) -> VideoDecoder:
        if decoder_key not in self.decoders:
            self.decoders[decoder_key] = VideoDecoder(self.device_id, codec)
            logger.debug(
                f"Created VideoDecoder {decoder_key} with codec {codec} on device {self.device_id}"
            )
        return self.decoders[decoder_key]

    def decode_video_frame(
        self,
        decoder: VideoDecoder,
        video_path: str | Path,
        frame_idx: int,
        to_cpu: bool = False,
    ):
        decoded_frame = decoder.decode(str(video_path), frame_idx)
        (height, width) = decoded_frame.shape
        src_tensor = torch.from_dlpack(decoded_frame)
        rgb_tensor = nv12_to_rgb(src_tensor, width, int(height / 1.5))

        if to_cpu:
            rgb_tensor = rgb_tensor.cpu()
        return rgb_tensor
