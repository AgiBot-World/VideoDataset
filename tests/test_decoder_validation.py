from __future__ import annotations

import cv2
import numpy as np
import pytest
import torch

from videodataset import VideoDecoder
from videodataset.utils.video_util import nv12_to_rgb


@pytest.mark.decoder_validation
def test_decode_validation_with_frames(test_video):
    """Test the decode method for correct frame decoding.

    Read a frame from the test_video at fixed frame positions. Then, decode the video
    and verify that the decoded frame matches the read frames.
    """
    read_frames = []
    for i in range(10):
        cap = cv2.VideoCapture(str(test_video))
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        _, read_frame = cap.read()
        cap.release()
        read_frame = cv2.cvtColor(read_frame, cv2.COLOR_BGR2RGB)
        read_frames.append(read_frame)

    decoder = VideoDecoder(0, "h265")
    for i in range(10):
        decoded_frame = decoder.decode(str(test_video), i)
        frame_tensor = torch.from_dlpack(decoded_frame)
        (height, width) = decoded_frame.shape
        rgb_tensor = nv12_to_rgb(frame_tensor, width, int(height / 1.5))
        frame_rgb_np = rgb_tensor.cpu().numpy()
        assert np.allclose(read_frames[i], frame_rgb_np, atol=3)
