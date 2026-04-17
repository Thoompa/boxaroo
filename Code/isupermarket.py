from abc import ABC, abstractmethod
from enum import Enum


class ListSize(Enum):
    TESTING = 1
    SHORT = 2
    MEDIUM = 3
    LONG = 4
    FULL = 5


class ISuperMarket(ABC):

    @abstractmethod
    def get_data(
        self, list_size: ListSize, refresh_category_lists: bool = False
    ) -> None:
        pass
