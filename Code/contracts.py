from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Iterable, Sequence, TypedDict


class Supermarket(Enum):
    WOOLWORTHS = "woolworths"


class ListSize(Enum):
    TESTING = 1
    SHORT = 2
    MEDIUM = 3
    LONG = 4
    FULL = 5


class LoggingLevel(Enum):
    DEBUG = 1
    INFO = 2
    ERROR = 3


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


class ProductParseResult(TypedDict):
    name: str
    price: str
    unit_price: str
    promotion: str
    missing_fields: list[str]


class CategoryCount(TypedDict):
    name: str
    count: int


class ListProductTotals(TypedDict):
    testing: int
    short: int
    medium: int
    long: int
    full: int


class CategoryListCache(TypedDict, total=False):
    testing: list[str]
    short: list[str]
    medium: list[str]
    long: list[str]
    full: list[str]
    supermarket_categories: list[str]
    list_product_totals: ListProductTotals
    category_product_totals: dict[str, int]


class ILogger(ABC):
    @abstractmethod
    def __init__(self, logging_level: LoggingLevel):
        pass

    @abstractmethod
    def debug(self, message: str) -> None:
        pass

    @abstractmethod
    def log(self, message: str) -> None:
        pass

    @abstractmethod
    def error(self, e: str) -> None:
        pass


class IFileHandler(ABC):
    @abstractmethod
    def __init__(
        self, file_name: str, file_path: str, header: Sequence[str], logger: ILogger
    ):
        pass

    @abstractmethod
    def store_data(self, data: Iterable[Iterable[Any]]) -> None:
        pass


class IProductParser(ABC):
    @abstractmethod
    def parse(self, text: object | None) -> ProductParseResult:
        pass


class IWebDriver(ABC):
    @abstractmethod
    def get_page(self, url: str) -> None:
        pass

    @abstractmethod
    def get_products(
        self,
        _callback: Callable[[list[str]], ProductsData | list[list[str]]] | None = None,
    ) -> ProductsPageResult:
        pass

    @abstractmethod
    def quit(self) -> None:
        pass

    @abstractmethod
    def execute_script(self, script: str, *args) -> Any:
        pass

    @abstractmethod
    def reload_page(self) -> None:
        pass

    @abstractmethod
    def get_category_total_items(self) -> int | None:
        pass


class ISuperMarket(ABC):
    """Contract for supermarket-specific adapter implementations.

    Ownership:
    - Supermarket adapters own supermarket-specific navigation, payload
      extraction, and translation into Boxaroo category/product structures.
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
