"""Application composition and process lifecycle entry point.

Ownership:
- Build and wire concrete dependencies for one scrape run.
- Own process lifecycle concerns such as logger setup and WebDriver teardown.
- Invoke the coordinator as the runtime orchestration boundary.
- Surface a main() function for CLI and other potential entry points to invoke.
"""

import re
from datetime import date

from Code.contracts import ListSize, LoggingLevel, Supermarket
from Code.file_handler import FileHandler
from Code.list_size_help import (
    PERFORMANCE_CONFIG_TEMPLATE_PATH,
    load_performance_profile,
)
from Code.logger import Logger
from Code.product_parser import ProductParser
from Code.scrape_coordinator import ScrapeCoordinator
from Code.supermarket_factory import (
    ISuperMarket,
    resolve_supermarket,
    supermarket_factory,
)
from Code.web_driver import WebDriver


def _build_output_file_name(
    supermarket_name: str,
    list_size: ListSize,
    category: str | None,
) -> str:
    suffix = list_size.name
    if category is not None and category.strip():
        normalized_category = re.sub(r"[^a-z0-9-]+", "-", category.strip().lower())
        normalized_category = re.sub(r"-+", "-", normalized_category).strip("-")
        suffix = normalized_category or list_size.name

    return "{0}-{1}-{2}.csv".format(supermarket_name, date.today(), suffix)


def _build_run_context(
    default_list_size: ListSize | None,
    category: str | None,
    supermarket: str | Supermarket | None,
) -> tuple[ListSize, Supermarket, str, str, str, list[str]]:
    list_size = default_list_size if default_list_size is not None else ListSize.TESTING
    selected_supermarket = resolve_supermarket(supermarket)
    supermarket_name = selected_supermarket.value
    file_path = "Data/{0}".format(date.today())
    file_name = _build_output_file_name(supermarket_name, list_size, category)
    header = ["Product Name", "Price", "Unit Price", "Promotion"]
    return (
        list_size,
        selected_supermarket,
        supermarket_name,
        file_path,
        file_name,
        header,
    )


def _prepare_runtime_dependencies(
    *,
    file_handler,
    logger,
    web_driver,
    headless,
    hard_driver_reset,
    proxy_server,
    file_name: str,
    file_path: str,
    header: list[str],
):
    injected_web_driver = web_driver is not None
    if not injected_web_driver:
        performance_profile = load_performance_profile()
        if performance_profile is None:
            performance_profile = load_performance_profile(
                PERFORMANCE_CONFIG_TEMPLATE_PATH
            )
        max_pages_per_session = (
            performance_profile["max_pages_per_session"]
            if performance_profile is not None
            else 12
        )
        file_handler = file_handler or FileHandler(file_name, file_path, header, logger)
        web_driver = WebDriver(
            logger=logger,
            headless=headless,
            proxy_server=proxy_server,
            hard_driver_reset=hard_driver_reset,
            max_pages_per_session=max_pages_per_session,
        )

    return file_handler, web_driver, injected_web_driver


def _run_scrape(
    *,
    selected_supermarket: Supermarket,
    supermarket_name: str,
    list_size: ListSize,
    category: str | None,
    refresh_category_lists: bool,
    injected_web_driver: bool,
    headless: bool,
    file_handler,
    logger,
    web_driver,
    product_parser,
    file_name: str,
    file_path: str,
    header: list[str],
    mark_lifecycle_started,
) -> None:
    if injected_web_driver:
        file_handler = file_handler or FileHandler(file_name, file_path, header, logger)

    product_parser = product_parser or ProductParser(logger)
    supermarket_adapter: ISuperMarket = supermarket_factory(
        selected_supermarket,
        file_handler,
        logger,
        web_driver,
        product_parser,
    )
    coordinator = ScrapeCoordinator(supermarket_adapter, logger, file_handler)
    target_label = (
        "category - {0}".format(category.strip())
        if isinstance(category, str) and category.strip()
        else "list size - {0}".format(list_size.name)
    )
    logger.log(
        "Running{0} Boxaroo with supermarket - {1} and {2}".format(
            " Headless" if headless else "", supermarket_name, target_label
        )
    )
    logger.log("WebDriver lifecycle start")
    mark_lifecycle_started()
    coordinator.run(
        list_size=list_size,
        category=category,
        refresh_category_lists=refresh_category_lists,
    )


def _teardown_web_driver(
    web_driver, logger, scrape_succeeded: bool, lifecycle_started: bool
) -> None:
    try:
        web_driver.quit()
        if lifecycle_started:
            logger.log("WebDriver lifecycle stop")
    except Exception as exc:
        logger.error(f"WebDriver quit failed: {exc}")
        # Only surface quit failures when scrape work succeeded;
        # otherwise preserve the original scrape exception.
        if scrape_succeeded:
            raise


def main(
    headless=False,
    logging_level=LoggingLevel.INFO,
    default_list_size: ListSize | None = ListSize.TESTING,
    category: str | None = None,
    supermarket: str | Supermarket | None = Supermarket.WOOLWORTHS,
    refresh_category_lists=False,
    hard_driver_reset=False,
    proxy_server=None,
    file_handler=None,
    logger=None,
    web_driver=None,
    product_parser=None,
) -> None:
    """Compose a scrape run and hand control to the scrape coordinator."""
    logger = logger if logger is not None else Logger(logging_level)
    (
        list_size,
        selected_supermarket,
        supermarket_name,
        file_path,
        file_name,
        header,
    ) = _build_run_context(default_list_size, category, supermarket)

    file_handler, web_driver, injected_web_driver = _prepare_runtime_dependencies(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        headless=headless,
        hard_driver_reset=hard_driver_reset,
        proxy_server=proxy_server,
        file_name=file_name,
        file_path=file_path,
        header=header,
    )
    scrape_succeeded = False
    lifecycle_started = False

    def mark_lifecycle_started() -> None:
        nonlocal lifecycle_started
        lifecycle_started = True

    try:
        _run_scrape(
            selected_supermarket=selected_supermarket,
            supermarket_name=supermarket_name,
            list_size=list_size,
            category=category,
            refresh_category_lists=refresh_category_lists,
            injected_web_driver=injected_web_driver,
            headless=headless,
            file_handler=file_handler,
            logger=logger,
            web_driver=web_driver,
            product_parser=product_parser,
            file_name=file_name,
            file_path=file_path,
            header=header,
            mark_lifecycle_started=mark_lifecycle_started,
        )
        scrape_succeeded = True
    except KeyboardInterrupt:
        logger.log("Scrape interrupted by user (Ctrl+C)")
        raise
    finally:
        _teardown_web_driver(
            web_driver,
            logger,
            scrape_succeeded,
            lifecycle_started,
        )
