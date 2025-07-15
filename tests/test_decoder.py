from __future__ import annotations

import pytest

from videodataset import VideoDecoder


def video_decode(video, frames: list):
    decoder = VideoDecoder(0, "h265")
    for index in frames:
        decoder.decode(str(video), index)


def test_init():
    """Test CUDA context creation with valid and invalid GPU IDs."""
    # Test with valid GPU ID
    VideoDecoder(0, "h265")


def test_invalid_gpu():
    # Test invalid GPU ID initialization with out-of-range value 999 and H.265 codec
    with pytest.raises(Exception) as exc_info:
        # Attempt to create decoder with invalid GPU ID (should trigger error)
        VideoDecoder(999, "h265")
    # Verify error message contains "Invalid GPU ID" text pattern
    assert "GPU ordinal out of range" in str(exc_info.value)


def test_decode_sample(test_video):
    # Create decoder instance with GPU ID 0 and H.265 codec
    VideoDecoder(0, "h265").decode(str(test_video), 0)


def test_open_invalid_file():
    # Create decoder instance with GPU ID 0 and H.265 codec
    decoder = VideoDecoder(0, "h265")

    # Verify that opening invalid file raises RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        # Attempt to open non-existent/invalid video file
        decoder.decode("1.mp4", 0)

    # Validate error message contains expected pattern
    assert "Failed to open video file" in str(exc_info.value)


def test_unsupported_codec():
    with pytest.raises(RuntimeError) as exc_info:
        VideoDecoder(0, "unknown")
    assert "Unsupported codec" in str(exc_info.value)


@pytest.mark.benchmark(group="block_decode")
@pytest.mark.parametrize(
    "block",
    [(0, 3), (3, 6), (6, 9)],
    ids=["block[0:3]", "block[3:6]", "block[6:9]"],
)
def test_decode_range(benchmark, test_video, block):
    benchmark.pedantic(
        video_decode,
        args=(test_video, block),
        iterations=4,
        rounds=10,
    )
