from typing import Iterator, Any

from torch.utils.data import DataLoader


class BaseDataLoader(DataLoader):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __iter__(self) -> Iterator[Any]:
        pass

    def restore_state_dict(self):
        pass

    def load_state_dict(self):
        pass
