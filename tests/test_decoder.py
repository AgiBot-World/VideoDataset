from __future__ import annotations

import cv2
import numpy as np
import pytest
import torch

from videodataset import VideoDecoder
from videodataset.utils.video_util import nv12_to_rgb


def test_init():
    """Test CUDA context creation with valid and invalid GPU IDs."""
    # Test with valid GPU ID
    VideoDecoder(0, "h265")


def test_invalid_gpu():
    """Test invalid GPU ID initialization with out-of-range value 999 and H.265 codec."""
    with pytest.raises(
        ValueError,
        match="GPU ordinal out of range",
    ):
        # Attempt to create decoder with invalid GPU ID (should trigger error)
        VideoDecoder(999, "h265")


def test_decode_sample(test_video):
    """Create decoder instance with GPU ID 0 and H.265 codec."""
    VideoDecoder(0, "h265").decode(str(test_video), 0)


def test_open_invalid_file():
    """Create decoder instance with GPU ID 0 and H.265 codec."""
    decoder = VideoDecoder(0, "h265")

    # Verify that opening invalid file raises RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        # Attempt to open non-existent/invalid video file
        decoder.decode("1.mp4", 0)

    # Validate error message contains expected pattern
    assert "Failed to open video file" in str(exc_info.value)


def test_unsupported_codec():
    """Create decoder instance with GPU ID 0 and unsupported codec."""
    with pytest.raises(RuntimeError) as exc_info:
        VideoDecoder(0, "unknown")
    assert "Unsupported codec" in str(exc_info.value)


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
