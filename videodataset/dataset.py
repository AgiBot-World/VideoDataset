
from torch.utils.data import IterableDataset

from videodataset.cache import Cache


class BaseDataset(IterableDataset):

    def __init__(self, cache_size: int):
        super().__init__()
        self.cache = Cache(cache_size=cache_size)

    def __iter__(self):
        """Yield next frame.

        Returns:
        Iterator: An iterator that yields the next frame.
        """
        pass
