import json
import os

from isupermarket import ListSize
from woolworths import Woolworths
from file_handler import FileHandler
from datetime import date
from logger import Logger, LoggingLevel
from web_driver import WebDriver


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
    default_list_size=ListSize.TESTING,
    refresh_category_lists=False,
    proxy_server=None,
    file_handler=None,
    logger=None,
    web_driver=None,
) -> None:
    # Allow dependency injection for unit testing
    logger = logger or Logger(logging_level)
    list_size = default_list_size if default_list_size is not None else ListSize.TESTING
    file_path = "Data/{0}".format(date.today())
    file_name = "woolworths-{0}-{1}.csv".format(date.today(), list_size.name)
    header = ["Product Name", "Price", "Unit Price", "Promotion"]

    file_handler = file_handler or FileHandler(file_name, file_path, header, logger)
    web_driver = web_driver or WebDriver(headless, proxy_server)

    woollies = Woolworths(file_handler, logger, web_driver)
    logger.log("Running Boxaroo with list size - {0}".format(list_size))
    logger.log("WebDriver lifecycle start")
    scrape_error: Exception | None = None

    try:
        woollies.get_data(
            list_size=list_size, refresh_category_lists=refresh_category_lists
        )
    except Exception as exc:
        scrape_error = exc
        raise
    finally:
        logger.log("WebDriver lifecycle stop")
        try:
            web_driver.quit()
        except Exception as exc:
            logger.error(f"WebDriver quit failed: {exc}")
            if scrape_error is None:
                raise
