from abc import ABC, abstractmethod
from enum import Enum


class ListSize(Enum):
    TESTING = 1
    SHORT = 2
    FULL = 3


class ISuperMarket(ABC):
    
    @abstractmethod
    def get_data(self, list_size: ListSize) -> None:
        pass