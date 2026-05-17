"""Application composition and process lifecycle entry point.

Ownership:
- Build and wire concrete dependencies for one scrape run.
- Own process lifecycle concerns such as logger setup and WebDriver teardown.
- Invoke the coordinator as the runtime orchestration boundary.
- Surface a main() function for CLI and other potential entry points to invoke.
"""

from datetime import date

from Code.contracts import ListSize, LoggingLevel, Supermarket
from Code.file_handler import FileHandler
from Code.logger import Logger
from Code.product_parser import ProductParser
from Code.scrape_coordinator import ScrapeCoordinator
from Code.supermarket_factory import (
    ISuperMarket,
    resolve_supermarket,
    supermarket_factory,
)
from Code.web_driver import WebDriver


def _build_run_context(
    default_list_size: ListSize | None,
    supermarket: str | Supermarket | None,
) -> tuple[ListSize, Supermarket, str, str, str, list[str]]:
    list_size = default_list_size if default_list_size is not None else ListSize.TESTING
    selected_supermarket = resolve_supermarket(supermarket)
    supermarket_name = selected_supermarket.value
    file_path = "Data/{0}".format(date.today())
    file_name = "{0}-{1}-{2}.csv".format(supermarket_name, date.today(), list_size.name)
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
    proxy_server,
    file_name: str,
    file_path: str,
    header: list[str],
):
    injected_web_driver = web_driver is not None
    if not injected_web_driver:
        file_handler = file_handler or FileHandler(file_name, file_path, header, logger)
        web_driver = WebDriver(headless, proxy_server)

    return file_handler, web_driver, injected_web_driver


def _run_scrape(
    *,
    selected_supermarket: Supermarket,
    supermarket_name: str,
    list_size: ListSize,
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
    probe: bool = False,
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

    if probe:
        from Code.scrape_coordinator import ProbeCoordinator

        coordinator = ProbeCoordinator(supermarket_adapter, logger, web_driver)
    else:
        coordinator = ScrapeCoordinator(supermarket_adapter, logger, file_handler)

    logger.log(
        "Running{0} Boxaroo with supermarket - {1} and list size - {2}".format(
            " Headless" if headless else "", supermarket_name, list_size.name
        )
    )
    logger.log("WebDriver lifecycle start")
    mark_lifecycle_started()
    coordinator.run(list_size=list_size, refresh_category_lists=refresh_category_lists)


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
    supermarket: str | Supermarket | None = Supermarket.WOOLWORTHS,
    refresh_category_lists=False,
    proxy_server=None,
    file_handler=None,
    logger=None,
    web_driver=None,
    product_parser=None,
    probe=False,
) -> None:
    """Compose a scrape run and hand control to the scrape coordinator."""
    logger = logger or Logger(logging_level)
    (
        list_size,
        selected_supermarket,
        supermarket_name,
        file_path,
        file_name,
        header,
    ) = _build_run_context(default_list_size, supermarket)

    file_handler, web_driver, injected_web_driver = _prepare_runtime_dependencies(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        headless=headless,
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
            probe=probe,
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
