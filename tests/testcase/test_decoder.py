import os
import pytest

from pathlib import Path
from videodataset import video_decoder


@pytest.fixture
def parent_dir(request):
    parent_dir = os.environ.get("TEST_PARENT_DIR")
    if parent_dir:
        return Path(parent_dir)
    return Path(__file__).parent.parent


def test_init():
    """Test CUDA context creation with valid and invalid GPU IDs."""
    # Test with valid GPU ID

    video_decoder.VideoDecoder(0, "h265")


def test_invalid_gpu():
    # Test invalid GPU ID initialization with out-of-range value 999 and H.265 codec
    with pytest.raises(Exception) as exc_info:
        # Attempt to create decoder with invalid GPU ID (should trigger error)
        video_decoder.VideoDecoder(999, "h265")
    # Verify error message contains "Invalid GPU ID" text pattern
    assert "GPU ordinal out of range" in str(exc_info.value)


def test_open_file(parent_dir):
    # Create decoder instance with GPU ID 0 and H.265 codec
    decoder = video_decoder.VideoDecoder(0, "h265")
    decoder.decode(
        os.path.join(
            parent_dir,
            "testdata/data/640/10589/A2D0015AB00172/845949/videos",
            "head_color.mp4",
        ),
        0,
    )


def test_open_invalid_file():
    # Create decoder instance with GPU ID 0 and H.265 codec
    decoder = video_decoder.VideoDecoder(0, "h265")

    # Verify that opening invalid file raises RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        # Attempt to open non-existent/invalid video file
        decoder.decode("1.mp4", 0)

    # Validate error message contains expected pattern
    assert "Failed to open video file" in str(exc_info.value)


def test_unsupported_codec():
    with pytest.raises(RuntimeError) as exc_info:
        video_decoder.VideoDecoder(0, "unknown")
    assert "Unsupported codec" in str(exc_info.value)
