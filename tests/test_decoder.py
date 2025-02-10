from __future__ import annotations

import logging
import time

import cv2
import numpy as np
import pytest

from videodataset import VideoDecoder

logger = logging.getLogger(__name__)


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


def test_decode(test_video):
    """Create decoder instance with GPU ID 0 and H.265 codec."""
    VideoDecoder(0, "h265").decode_to_np(str(test_video), 0)


def test_decode_to_np(test_video):
    """Create decoder instance with GPU ID 0 and H.265 codec."""
    VideoDecoder(0, "h265").decode_to_np(str(test_video), 0)


def test_decode_to_tensor(test_video):
    """Create decoder instance with GPU ID 0 and H.265 codec."""
    VideoDecoder(0, "h265").decode_to_tensor(str(test_video), 0)


def test_open_invalid_file():
    """Create decoder instance with GPU ID 0 and H.265 codec."""
    decoder = VideoDecoder(0, "h265")

    # Verify that opening invalid file raises RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        # Attempt to open non-existent/invalid video file
        decoder.decode_to_np("1.mp4", 0)

    # Validate error message contains expected pattern
    assert "Failed to open video file" in str(exc_info.value)


def test_unsupported_codec():
    """Create decoder instance with GPU ID 0 and unsupported codec."""
    with pytest.raises(RuntimeError) as exc_info:
        VideoDecoder(0, "unknown")
    assert "Unsupported codec" in str(exc_info.value)


def test_decode_validation_with_bench(test_video):
    """Test the different decode method for correct frame decoding and benchmarking."""
    cv_frames = []
    frame_indices = [3, 7, 10, 14, 17, 22, 27]
    for i in frame_indices:
        cap = cv2.VideoCapture(str(test_video))
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        _, read_frame = cap.read()
        cap.release()
        read_frame = cv2.cvtColor(read_frame, cv2.COLOR_BGR2RGB)
        cv_frames.append(read_frame)

    logger.info("test_decode_validation_with_bench:")

    decode_to_np_decoder = VideoDecoder(0, "h265")

    start_time = time.perf_counter()
    pre_time = start_time
    for i, index in enumerate(frame_indices):
        cv_frame = cv_frames[i]
        decoded_frame = decode_to_np_decoder.decode_to_np(str(test_video), index)
        rgb_np = decoded_frame
        assert np.allclose(cv_frame, rgb_np, atol=7)
        logger.info(
            f"decode_to_np frame {index} elapsed: {(time.perf_counter() - pre_time) * 1000:.2f}"
        )
        pre_time = time.perf_counter()

    logger.info(
        f"decode_to_np {len(frame_indices)} frames elapsed: {(time.perf_counter() - start_time) * 1000:.2f}"
        f", average: {(time.perf_counter() - start_time) * 1000 / len(frame_indices):.2f}"
    )

    decode_to_tensor_decoder = VideoDecoder(0, "h265")

    start_time = time.perf_counter()
    pre_time = start_time
    for i, index in enumerate(frame_indices):
        cv_frame = cv_frames[i]
        decoded_frame = decode_to_tensor_decoder.decode_to_tensor(
            str(test_video), index
        )
        rgb_np = decoded_frame.cpu().numpy()
        assert np.allclose(cv_frame, rgb_np, atol=7)
        logger.info(
            f"decode_to_tensor frame {index} elapsed: {(time.perf_counter() - pre_time) * 1000:.2f}"
        )
        pre_time = time.perf_counter()

    logger.info(
        f"decode_to_tensor {len(frame_indices)} frames elapsed: {(time.perf_counter() - start_time) * 1000:.2f}"
        f", average: {(time.perf_counter() - start_time) * 1000 / len(frame_indices):.2f}"
    )

    decode_to_nps_decoder = VideoDecoder(0, "h265")

    start_time = time.perf_counter()
    pre_time = start_time
    np_frames = decode_to_nps_decoder.decode_to_nps(str(test_video), frame_indices)
    for i, index in enumerate(frame_indices):
        cv_frame = cv_frames[i]
        decoded_frame = np_frames[i]
        rgb_np = decoded_frame
        assert np.allclose(cv_frame, rgb_np, atol=7)
        logger.info(
            f"decode_to_nps frame {index} elapsed: {(time.perf_counter() - pre_time) * 1000:.2f}"
        )
        pre_time = time.perf_counter()

    logger.info(
        f"decode_to_nps {len(frame_indices)} frames elapsed: {(time.perf_counter() - start_time) * 1000:.2f}"
        f", average: {(time.perf_counter() - start_time) * 1000 / len(frame_indices):.2f}"
    )
