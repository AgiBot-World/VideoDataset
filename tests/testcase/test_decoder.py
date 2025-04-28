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


def test_unsupported_codec():
    with pytest.raises(RuntimeError) as exc_info:
        video_decoder.VideoDecoder(0, "unknown")
    assert "Unsupported codec" in str(exc_info.value)


def test_decode_target_frame_not_found():
    # Create a VideoDecoder instance with GPU ID 0 and H.264 codec
    decoder = video_decoder.VideoDecoder(0, "h264")
    # Verify that trying to decode a non - existent target frame raises a RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        # Attempt to decode a frame number that is extremely large and likely non - existent
        decoder.decode("valid_video.mp4", 99999999999)
    # Validate that the error message contains the expected pattern
    assert "Target frame" in str(exc_info.value)


def test_decoder_core_initialization_failure():
    # Simulate the situation where an exception is thrown during the initialization of DecoderCore
    # The parameters may need to be adjusted to trigger the exception. This is just an example.
    # Try to initialize the VideoDecoder with an invalid GPU ID
    with pytest.raises(RuntimeError) as exc_info:
        video_decoder.VideoDecoder(999, "h264")
    # Validate that the error message contains the expected pattern
    assert "DecoderCore initialization failed" in str(exc_info.value)
