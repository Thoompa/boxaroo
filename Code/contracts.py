from enum import Enum
from typing import TypedDict


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
