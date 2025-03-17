from abc import abstractmethod
from typing import Any, Iterator

from torch.utils.data import IterableDataset

from videodataset.cache import Cache


class BaseDataset(IterableDataset):
    def __init__(self, cache: Cache) -> None:
        super().__init__()
        self.cache = cache

    @abstractmethod
    def __iter__(self) -> Iterator[Any]:
        """Yield next frame."""
        pass
