from abc import ABC, abstractmethod
from enum import Enum
from typing import TypedDict


class ListSize(Enum):
    TESTING = 1
    SHORT = 2
    MEDIUM = 3
    LONG = 4
    FULL = 5


class WebsiteCategory(TypedDict):
    name: str
    href: str


class IncompleteProductItem(TypedDict):
    name: str
    missing: list[str]


class ProductsData(TypedDict):
    products: list[list[str]]
    incomplete_items: list[IncompleteProductItem]


class PageStats(TypedDict):
    page: int
    product_tiles: int
    extraction_failures: int
    scraped: int
    incomplete: int


class ProductsPageResult(TypedDict):
    products: list[list[str]]
    incomplete_items: list[IncompleteProductItem]
    page_stats: list[PageStats]


class CategoryData(TypedDict):
    category: str
    total: int
    products: list[list[str]]
    incomplete_items: list[IncompleteProductItem]
    scraped: int
    incomplete: int


class ISuperMarket(ABC):

    @abstractmethod
    def get_data(
        self, list_size: ListSize, refresh_category_lists: bool = False
    ) -> None:
        pass
