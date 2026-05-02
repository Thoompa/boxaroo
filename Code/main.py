"""Application composition and process lifecycle entry point.

Ownership:
- Build and wire concrete dependencies for one scrape run.
- Own process lifecycle concerns such as logger setup and WebDriver teardown.
- Invoke the coordinator as the runtime orchestration boundary.

Non-ownership:
- Does not own category-level orchestration.
- Does not own supermarket-specific scraping rules.
- Does not own parser or category-list persistence logic.
"""

import json
import os

from Code.contracts import ListSize, LoggingLevel, Supermarket
from Code.supermarket_factory import (
    ISuperMarket,
    resolve_supermarket,
    supermarket_factory,
)
from Code.product_parser import ProductParser
from Code.file_handler import FileHandler
from datetime import date
from Code.logger import Logger
from Code.scrape_coordinator import ScrapeCoordinator
from Code.web_driver import WebDriver


def _load_list_product_totals() -> dict[str, int]:
    cache_path = os.path.join(
        "Data", "category_lists", "woolworths-category-lists.json"
    )
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        totals = cached.get("list_product_totals", {})
        if not isinstance(totals, dict):
            return {}
        return {
            str(k).lower(): int(v)
            for k, v in totals.items()
            if isinstance(v, int) and v >= 0
        }
    except Exception:
        return {}


def _format_eta(total_products: int | None) -> str:
    if total_products is None:
        return "n/a"

    seconds = round(total_products / 4)
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if remaining_seconds > 0 or not parts:
        parts.append(f"{remaining_seconds}s")

    return "~" + " ".join(parts)


def build_list_size_help() -> str:
    totals = _load_list_product_totals()

    return (
        "Size of category list to scrape. "
        "Estimated runtime by list (4 products/sec): "
        f"TESTING {_format_eta(totals.get('testing'))}, "
        f"SHORT {_format_eta(totals.get('short'))}, "
        f"MEDIUM {_format_eta(totals.get('medium'))}, "
        f"LONG {_format_eta(totals.get('long'))}, "
        f"FULL {_format_eta(totals.get('full'))}."
    )


def main(
    headless=False,
    logging_level=LoggingLevel.INFO,
    default_list_size: ListSize | None = ListSize.TESTING,
    supermarket: str | Supermarket | None = Supermarket.WOOLWORTHS,
    refresh_category_lists=False,
    proxy_server=None,
    file_handler=None,
    logger=None,
    web_driver=None,
    product_parser=None,
) -> None:
    """Compose a scrape run and hand control to the scrape coordinator."""
    logger = logger or Logger(logging_level)
    list_size = default_list_size if default_list_size is not None else ListSize.TESTING
    selected_supermarket = resolve_supermarket(supermarket)
    supermarket_name = selected_supermarket.value
    file_path = "Data/{0}".format(date.today())
    file_name = "{0}-{1}-{2}.csv".format(supermarket_name, date.today(), list_size.name)
    header = ["Product Name", "Price", "Unit Price", "Promotion"]

    file_handler = file_handler or FileHandler(file_name, file_path, header, logger)
    web_driver = web_driver or WebDriver(headless, proxy_server)
    product_parser = product_parser or ProductParser(logger=logger)

    supermarket_adapter: ISuperMarket = supermarket_factory(
        selected_supermarket,
        file_handler,
        logger,
        web_driver,
        product_parser,
    )
    coordinator = ScrapeCoordinator(supermarket_adapter, logger, file_handler)
    logger.log(
        "Running Boxaroo with supermarket - {0} and list size - {1}".format(
            supermarket_name, list_size.name
        )
    )
    logger.log("WebDriver lifecycle start")
    scrape_succeeded = False

    try:
        coordinator.run(
            list_size=list_size, refresh_category_lists=refresh_category_lists
        )
        scrape_succeeded = True
    finally:
        try:
            web_driver.quit()
            logger.log("WebDriver lifecycle stop")
        except Exception as exc:
            logger.error(f"WebDriver quit failed: {exc}")
            if scrape_succeeded:
                raise
