from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any


@dataclass
class VideoFrame:
    data: bytes
    timestamp: float


class BaseDecoder(ABC):
    def __init__(self, videos: Iterable[str]) -> None:
        self.videos = videos

    @abstractmethod
    def __iter__(self) -> Iterator[VideoFrame]:
        pass

    @abstractmethod
    def decode_video(self, video: str) -> Iterable[VideoFrame]:
        pass

    @abstractmethod
    def decode_video_frame(self, video: str, frame_index: int) -> VideoFrame:
        pass

    @abstractmethod
    def get_item(self, index: int) -> Any:
        pass
