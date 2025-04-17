import pytest

from videodataset import video_decoder


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
    assert "Invalid GPU ID" in str(exc_info.value)


def test_open_invalid_file():
    # Create decoder instance with GPU ID 0 and H.265 codec
    decoder = video_decoder.VideoDecoder(0, "h265")

    # Verify that opening invalid file raises RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        # Attempt to open non-existent/invalid video file
        decoder.decode("1.mp4", 0)

    # Validate error message contains expected pattern
    assert "Could not open file" in str(exc_info.value)
