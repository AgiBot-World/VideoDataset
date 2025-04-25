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


# def test_bitstream_filter_application_failure():
#     # Create a VideoDecoder instance with GPU ID 0 and H.264 codec
#     decoder = video_decoder.VideoDecoder(0, "h264")
#     # Assume we can get an AVPacket here and simulate the failure of apply_bitstream_filter
#     # Since the code does not provide a method to obtain an AVPacket, this is just an example and may need adjustment according to the actual situation
#     mock_pkt = None
#     # Verify that applying the bitstream filter with a mock packet raises a RuntimeError
#     with pytest.raises(RuntimeError) as exc_info:
#         decoder.apply_bitstream_filter(mock_pkt)
#     # Validate that the error message contains the expected pattern
#     assert "Failed to" in str(exc_info.value)


def test_decoder_core_initialization_failure():
    # Simulate the situation where an exception is thrown during the initialization of DecoderCore
    # The parameters may need to be adjusted to trigger the exception. This is just an example.
    # Try to initialize the VideoDecoder with an invalid GPU ID
    with pytest.raises(RuntimeError) as exc_info:
        video_decoder.VideoDecoder(999, "h264")
    # Validate that the error message contains the expected pattern
    assert "DecoderCore initialization failed" in str(exc_info.value)


def test_nv_decoder_video_decode_unsupported_format():
    # Assume the parameter here can initialize an NvDecoder instance
    decoder = video_decoder.NvDecoder(None)
    # Simulate encoded data
    encoded_data = b""
    # Set the size of the encoded data
    data_size = 0
    # Verify that decoding with an empty encoded data raises a RuntimeError due to an unsupported format
    with pytest.raises(RuntimeError) as exc_info:
        decoder.VideoDecode(encoded_data, data_size, 0)
    # Validate that the error message contains the expected pattern
    assert "Unsupported video format" in str(exc_info.value)
