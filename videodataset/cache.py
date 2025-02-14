from abc import ABC
from typing import Any


class Cache(ABC):
    def __init__(self, cache_size: int):
        self.cache_size = cache_size

    def get_data(self, file: str) -> Any:
        pass
