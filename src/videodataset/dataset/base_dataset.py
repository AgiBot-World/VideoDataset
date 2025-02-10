from __future__ import annotations

import logging
from pathlib import Path

import torch

from videodataset import VideoDecoder

logger = logging.getLogger(__name__)


class BaseVideoDataset:
    """Decoder extension that defines decoder specific functionalities"""

    def __init__(self) -> None:
        """Initialize the BaseVideoDataset with a dictionary to hold decoders
        and set the device_id to the current CUDA device if available.
        Raises a RuntimeError if no CUDA device is found.
        """
        self.decoders: dict[str, VideoDecoder] = {}

        if torch.cuda.is_available():
            self.device_id = torch.cuda.current_device()
        else:
            err_msg = "No cuda device found, accelerated decoding is not available"
            raise RuntimeError(err_msg)

    @property
    def device(self) -> int:
        """Return the device ID where decoders are running."""
        return self.device_id

    @property
    def num_decoders(self) -> int:
        """Return the number of decoders currently managed by the dataset."""
        return len(self.decoders)

    def get_decoder(self, decoder_key: str, codec: str) -> VideoDecoder:
        """Retrieve a VideoDecoder for a specific key and codec. If the decoder
        does not exist, it creates a new one and logs the creation.
        """
        if decoder_key not in self.decoders:
            self.decoders[decoder_key] = VideoDecoder(self.device_id, codec)
            logger.debug(
                "Created VideoDecoder %s with codec %s on device %s",
                decoder_key,
                codec,
                self.device_id,
            )
        return self.decoders[decoder_key]

    def decode_video_frames(
        self,
        decoder: VideoDecoder,
        video_path: str | Path,
        frame_indices: list[int],
        to_cpu: bool = False,
    ) -> list[torch.Tensor]:
        """Decode specific frames from a video file using the provided decoder.
        Converts the decoded frames from NV12 format to RGB and optionally moves
        the tensors to the CPU.
        """
        decoded_frames = decoder.decode_to_nps(str(video_path), frame_indices)

        rgb_tensors = []
        for np_frame in decoded_frames:
            rgb_tensor = torch.from_numpy(np_frame)
            rgb_tensors.append(
                rgb_tensor.cuda(decoder.gpu_id()) if not to_cpu else rgb_tensor
            )

        return rgb_tensors

    def decode_video_frame(
        self,
        decoder: VideoDecoder,
        video_path: str | Path,
        frame_idx: int,
        to_cpu: bool = False,
    ) -> torch.Tensor:
        """Decode a specific frame from a video file using the provided decoder.
        Converts the decoded frame from NV12 format to RGB and optionally moves
        the tensor to the CPU.
        """
        decoded_frame = decoder.decode_to_tensor(str(video_path), frame_idx)
        return decoded_frame.cpu() if to_cpu else decoded_frame
