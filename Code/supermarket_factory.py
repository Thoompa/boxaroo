from __future__ import annotations

from Code.contracts import (
    CategoryData,
    IncompleteProductItem,
    ISuperMarket,
    ListSize,
    PageStats,
    ProductsData,
    ProductsPageResult,
    Supermarket,
    WebsiteCategory,
)
from Code.file_handler import IFileHandler
from Code.logger import ILogger
from Code.product_parser import IProductParser
from Code.web_driver import IWebDriver
from Code.woolworths import Woolworths

__all__ = [
    "CategoryData",
    "IncompleteProductItem",
    "ISuperMarket",
    "ListSize",
    "PageStats",
    "ProductsData",
    "ProductsPageResult",
    "Supermarket",
    "WebsiteCategory",
    "resolve_supermarket",
    "supermarket_factory",
]


def resolve_supermarket(supermarket: str | Supermarket | None) -> Supermarket:
    if supermarket is None:
        return Supermarket.WOOLWORTHS

    if isinstance(supermarket, Supermarket):
        return supermarket

    normalized = supermarket.strip().lower()
    if not normalized:
        return Supermarket.WOOLWORTHS

    for candidate in Supermarket:
        if normalized in (candidate.value.lower(), candidate.name.lower()):
            return candidate

    raise ValueError(f"Unsupported supermarket '{supermarket}'")


SUPERMARKET_REGISTRY = {
    Supermarket.WOOLWORTHS: Woolworths,
}


def supermarket_factory(
    supermarket: str | Supermarket | None,
    file_handler: IFileHandler,
    logger: ILogger,
    web_driver: IWebDriver,
    product_parser: IProductParser,
) -> ISuperMarket:
    supermarket_key = resolve_supermarket(supermarket)

    try:
        supermarket_adapter = SUPERMARKET_REGISTRY[supermarket_key]
    except KeyError as exc:
        raise ValueError(
            f"No adapter registered for supermarket '{supermarket_key.value}'"
        ) from exc

    return supermarket_adapter(file_handler, logger, web_driver, product_parser)
