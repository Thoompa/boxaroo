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
    """Contract for supermarket-specific adapter implementations.

    Ownership:
    - Supermarket adapters own supermarket-specific navigation, payload
      extraction, and translation into Boxaroo category/product structures.
    - Category list services own persistence and list-size selection rules.
    - Product parsers own parsing raw product payloads into normalized fields.

    Boundary direction:
    - Coordinators should depend on category-level methods.
    - get_data() remains as the backward-compatible entry point while
      orchestration still lives inside adapters.
    """

    @abstractmethod
    def get_categories(
        self, list_size: ListSize = ListSize.FULL, refresh_category_lists: bool = False
    ) -> list[str]:
        """Return the category names selected for the current run."""
        pass

    @abstractmethod
    def get_category_data(self, category_name: str) -> CategoryData:
        """Return normalized data for one category scrape attempt."""
        pass

    @abstractmethod
    def get_data(
        self, list_size: ListSize = ListSize.FULL, refresh_category_lists: bool = False
    ) -> None:
        """Legacy compatibility entry point that runs the full scrape."""
        pass
