from __future__ import annotations
import typing

__all__ = ["CAIMemoryView", "DecodedFrame", "ExternalBuffer", "VideoDecoder"]

class CAIMemoryView:
    def __init__(
        self,
        arg0: list[int],
        arg1: list[int],
        arg2: str,
        arg3: int,
        arg4: int,
        arg5: bool,
    ) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def __cuda_array_interface__(self) -> dict: ...
    @property
    def data(self) -> int: ...
    @property
    def dataptr(self) -> int: ...
    @property
    def shape(self) -> list[int]: ...
    @property
    def stride(self) -> list[int]: ...

class DecodedFrame:
    def __dlpack__(self, stream: typing.Any = 0) -> capsule:
        """
        Export the buffer as a DLPack tensor
        """
    def __dlpack_device__(self) -> tuple:
        """
        Get the device associated with the buffer
        """
    def __repr__(self) -> str: ...
    @property
    def format(self) -> Pixel_Format: ...
    @property
    def shape(self) -> tuple:
        """
        Get the shape of the buffer as an array
        """
    @property
    def timestamp(self) -> int: ...

class ExternalBuffer:
    def __dlpack__(self, stream: typing.Any = 1) -> capsule:
        """
        Export the buffer as a DLPack tensor
        """
    def __dlpack_device__(self) -> tuple:
        """
        Get the device associated with the buffer
        """
    @property
    def dtype(self) -> str:
        """
        Get the data type of the buffer
        """
    @property
    def shape(self) -> tuple:
        """
        Get the shape of the buffer as an array
        """
    @property
    def strides(self) -> tuple:
        """
        Get the strides of the buffer
        """

class VideoDecoder:
    """
    Video decoder with NvCodec acceleration.
    """
    def __init__(self, gpuid: int, codec: str) -> None:
        """
        Create a video decoder instance.

        Args:
            gpuid (int): GPU device ID to use for decoding.
            codec (str): Name of the video codec (e.g., "h264", "hevc").
        """
    def decode(self, path: str, target_frame: int) -> DecodedFrame:
        """
        The main decoding function for VideoDecoder.

        Performs the complete decoding process for a given video file.
        It opens the file, finds the video stream, calculates the target PTS, seeks to the target frame,
        initializes the bitstream filter if needed, and then decodes the frames until the target frame is found.

        Args:
            path (str): The path to the video file to be decoded.
            target_frame (int): The frame number that is the target for decoding.

        Returns:
            A DecodedFrame object representing the target frame that was successfully decoded.

        Raises:
            RuntimeError: if there are issues such as file opening failure, decoding failure, or target frame not found.
        """
    @property
    def codec(self) -> str:
        """
        Video codec format being decoded
        """
    @codec.setter
    def codec(self, arg0: str) -> None: ...
    @property
    def gpuId(self) -> int:
        """
        ID of the GPU being used for decoding
        """
    @gpuId.setter
    def gpuId(self, arg0: int) -> None: ...
