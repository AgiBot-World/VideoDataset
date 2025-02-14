from abc import ABC
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class VideoFrame:
    data: bytes
    timestamp: float


class BaseDecoder(ABC):
    def __init__(self, videos: Iterable[str]):
        self.videos = videos

    def __iter__(self):
        pass

    def decode_video(self, video: str) -> Iterable[VideoFrame]:
        pass

    def decode_video_frame(self, video: str, frame_index: int) -> VideoFrame:
        pass

    def get_item(self, index: int) -> Any:
        pass
