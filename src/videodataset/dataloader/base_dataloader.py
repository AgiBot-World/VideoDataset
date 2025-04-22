from abc import ABC, abstractmethod
from typing import Any

from torch.utils.data import DataLoader
from torch.utils.data.dataloader import _BaseDataLoaderIter


class BaseDataLoader(DataLoader, ABC):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @abstractmethod
    def __iter__(self) -> _BaseDataLoaderIter:
        pass

    @abstractmethod
    def restore_state_dict(self, state_dict: dict) -> None:
        pass

    @abstractmethod
    def load_state_dict(self) -> dict:
        pass
