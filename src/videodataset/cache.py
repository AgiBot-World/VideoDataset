from abc import ABC, abstractmethod
from typing import Any


class Cache(ABC):
    def __init__(self, cache_size: int) -> None:
        self.cache_size = cache_size

    @abstractmethod
    def get_data(self, file: str) -> Any:
        pass
