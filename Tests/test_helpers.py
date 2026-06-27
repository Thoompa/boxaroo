# test_helpers.py
"""
Shared dummy/mock classes for Boxaroo unit tests.
"""
from typing import Any, cast

from Code.file_handler import FileHandler
from Code.category_list_service import CategoryListService
from Code.contracts import (
    CategoryData,
    ISuperMarket,
    ListSize,
    ProductsCallback,
    ProductsPageResult,
    ProductParseResult,
    IProductParser,
    IWebDriver,
    ILogger,
    LoggingLevel,
    IFileHandler,
)
from Code.web_driver import WebDriver, NEXT_BUTTON_LOCATORS
from Code.woolworths_category_data_normaliser import WoolworthsCategoryDataNormaliser
from Code.woolworths_category_source import WoolworthsCategorySource


class DummyLogger(ILogger):
    instances: list["DummyLogger"] = []

    def __init__(self, logging_level=None):
        self.logging_level = logging_level or LoggingLevel.INFO
        self.records = []
        DummyLogger.instances.append(self)

    def debug(self, message):
        self.records.append(("DEBUG", message))

    def log(self, message):
        self.records.append(("INFO", message))

    def warning(self, message):
        self.records.append(("WARNING", message))

    def error(self, message):
        self.records.append(("ERROR", message))


class DummyFileHandler(IFileHandler):
    def __init__(self, error_on_init=False):
        if error_on_init:
            raise OSError("permission denied")
        self.saved = []

    def store_data(self, data):
        self.saved.append(data)


class DummyWebDriver(IWebDriver):
    def __init__(self, error_on_init=False):
        if error_on_init:
            raise AssertionError("WebDriver should not be created")
        self.called = []
        self.script_response = ""
        self.category_total_items = None
        self.category_total_items_sequence = []
        self.invoke_products_callback = False
        self.products_response: ProductsPageResult = {
            "products": [],
            "incomplete_items": [],
            "page_stats": [],
        }

    def get_page(self, url: str) -> None:
        self.called.append(("get_page", url))

    def get_products(
        self,
        _callback: ProductsCallback | None = None,
        category_name: str | None = None,
    ) -> ProductsPageResult:
        self.called.append(("get_products", category_name))
        if (
            self.invoke_products_callback
            and _callback is not None
            and isinstance(self.products_response, dict)
        ):
            products = cast(list[str], self.products_response.get("products", []))
            callback_result = _callback(products, page_number=1)
            if isinstance(callback_result, dict):
                return {
                    "products": callback_result.get("products", []),
                    "incomplete_items": callback_result.get("incomplete_items", []),
                    "page_stats": self.products_response.get("page_stats", []),
                }
            if isinstance(callback_result, list):
                return {
                    "products": callback_result,
                    "incomplete_items": [],
                    "page_stats": self.products_response.get("page_stats", []),
                }
        return self.products_response

    def quit(self) -> None:
        self.called.append(("quit",))

    def execute_script(self, script: str, *args) -> Any:
        self.called.append(("execute_script", script))
        if callable(self.script_response):
            return self.script_response(script, *args)
        if isinstance(self.script_response, list):
            return self.script_response.pop(0) if self.script_response else ""
        return self.script_response

    def reload_page(self) -> None:
        self.called.append(("reload_page",))

    def get_category_total_items(self) -> int | None:
        self.called.append(("get_category_total_items",))
        if self.category_total_items_sequence:
            return self.category_total_items_sequence.pop(0)
        return self.category_total_items


class DummyProductParser(IProductParser):
    """Configurable test double for IProductParser."""

    def __init__(self):
        self.calls: list[object] = []
        self._queued: list[ProductParseResult] = []
        self._default_response: ProductParseResult = {
            "name": "",
            "price": "",
            "unit_price": "",
            "promotion": "",
            "missing_fields": ["name", "price", "unit_price"],
        }

    def queue_response(self, response: ProductParseResult) -> None:
        """Enqueue a response; returned FIFO until queue is empty."""
        self._queued.append(response)

    def set_default_response(self, response: ProductParseResult) -> None:
        """Set the response returned when the queue is empty."""
        self._default_response = response

    def parse(self, text: object | None) -> ProductParseResult:
        self.calls.append(text)
        if self._queued:
            return self._queued.pop(0)
        return self._default_response


class DummySupermarket(ISuperMarket):
    def __init__(
        self,
        logger=None,
        file_handler=None,
        web_driver=None,
        product_parser=None,
        logic=None,
        categories: list[str] | None = None,
        category_data: dict[str, CategoryData] | None = None,
        products_to_store=None,
        get_categories_error=None,
        get_category_data_error=None,
    ):
        self.file_handler = file_handler
        self.logger = logger
        self.web_driver = web_driver
        self.product_parser = product_parser

        self.logic = logic
        self.categories = categories or []
        self.category_data = category_data or {}
        self.products_to_store = products_to_store
        self.get_categories_error = get_categories_error
        self.get_category_data_error = get_category_data_error
        self.get_categories_called = False
        self.last_list_size = None
        self.last_refresh_category_lists = None
        self.get_category_data_calls: list[str] = []

    def get_categories(
        self,
        list_size: ListSize = ListSize.FULL,
        refresh_category_lists: bool = False,
        category: str | None = None,
    ) -> list[str]:
        if self.logic:
            self.logic(self.logger, list_size, refresh_category_lists)
        self.last_list_size = list_size
        self.last_refresh_category_lists = refresh_category_lists
        self.get_categories_called = True
        if self.get_categories_error is not None:
            raise self.get_categories_error
        if category is not None:
            return [category]
        if self.categories:
            return self.categories
        if self.products_to_store is not None:
            return ["default-category"]
        return self.categories

    def get_category_data(self, category_name: str) -> CategoryData:
        self.get_category_data_calls.append(category_name)
        if self.get_category_data_error is not None:
            raise self.get_category_data_error
        if category_name in self.category_data:
            return self.category_data[category_name]
        products = self.products_to_store if self.products_to_store is not None else []
        return {
            "category": category_name,
            "total": len(products),
            "products": products,
            "incomplete_items": [],
            "scraped": len(products),
            "incomplete": 0,
        }


class DummyWebDriverHarness(WebDriver):
    def __init__(self, products_response=None):
        self.scripts = []
        self.driver: Any = None
        self.logger = DummyLogger()
        self.hard_driver_reset = False
        self.max_pages_per_session = 12
        self._create_fresh_driver: Any = lambda: DummyWebDriverHarness(
            products_response
        )
        self._category_total_script_response: str | None = None
        self._products_response = products_response or {
            "products": [],
            "incomplete_items": [],
            "page_stats": [],
        }
        self.page_saved = 0

    def execute_script(self, script, *args, **kwargs) -> Any:
        self.scripts.append(script)
        return self._category_total_script_response

    def get_page(self, url):
        pass

    def get_products(
        self,
        _callback: Any | None = None,
        category_name: str | None = None,
    ):
        self.page_saved += 1
        if _callback and "products" in self._products_response:
            _callback(
                cast(list[str], self._products_response["products"]), page_number=1
            )
        return self._products_response

    def quit(self):
        pass

    def reload_page(self):
        pass


class DummyWait:
    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout

    def until(self, condition):
        # Call the condition to evaluate it (e.g. presence_of_element_located)
        try:
            return condition(self.driver)
        except Exception:
            # If condition fails, treat it as timeout (element not found)
            raise TimeoutError("Dummy wait timeout")


def make_woolworths_category_source(
    cache_path: str,
    logger: DummyLogger | None = None,
    web_driver: DummyWebDriver | None = None,
    base_url: str = "https://www.woolworths.com.au",
    browse_url: str = "https://www.woolworths.com.au/shop/browse/",
) -> WoolworthsCategorySource:
    logger = logger or DummyLogger()
    web_driver = web_driver or DummyWebDriver()
    service = CategoryListService(cache_path, logger)
    return WoolworthsCategorySource(
        logger=logger,
        web_driver=web_driver,
        category_list_service=service,
        base_url=base_url,
        browse_url=browse_url,
    )


def make_woolworths_category_data_normaliser(
    logger: DummyLogger | None = None,
    web_driver: DummyWebDriver | None = None,
    product_parser: DummyProductParser | None = None,
    browse_url: str = "https://www.woolworths.com.au/shop/browse/",
) -> WoolworthsCategoryDataNormaliser:
    logger = logger or DummyLogger()
    web_driver = web_driver or DummyWebDriver()
    product_parser = product_parser or DummyProductParser()
    return WoolworthsCategoryDataNormaliser(
        logger=logger,
        web_driver=web_driver,
        product_parser=product_parser,
        browse_url=browse_url,
    )


FILE_HANDLER_HEADER = ["name", "price", "unit_price", "promotion"]


def make_file_handler(tmp_path, header=None, file_name="out.csv"):
    """Construct a FileHandler backed by a real temp directory.

    Returns (handler, logger) so callers can inspect log records.
    """
    logger = DummyLogger()
    handler = FileHandler(
        file_name=file_name,
        file_path=str(tmp_path),
        header=FILE_HANDLER_HEADER if header is None else header,
        logger=logger,
    )
    return handler, logger


class DummyNextButton:
    def __init__(self, href, displayed=True, enabled=True):
        self.href = href
        self._displayed = displayed
        self._enabled = enabled

    def is_displayed(self):
        return self._displayed

    def is_enabled(self):
        return self._enabled

    def get_attribute(self, name):
        if name == "href":
            return self.href
        return None


class DummyProductElement:
    """Configurable test double for a Selenium product element."""

    def __init__(
        self,
        text: str = "",
        raise_on_text: bool = False,
        text_error: Exception | None = None,
    ):
        self._text = text
        self._raise_on_text = raise_on_text
        self._text_error = text_error

    @property
    def text(self):
        if self._text_error is not None:
            raise self._text_error
        if self._raise_on_text:
            raise AttributeError("no text attribute")
        return self._text


class DummySeleniumSession:
    def __init__(
        self,
        script_result=None,
        script_side_effect=None,
        next_button_href="page-2",
        next_button_displayed=True,
        next_button_enabled=True,
        next_button_missing=False,
        click_advances_url_to=None,
        mark_incomplete_a=False,
        pages: list[list[str]] | None = None,
        page_urls: list[str] | None = None,
        start_page_index: int = 0,
        next_button_selectors: set[tuple[str, str]] | None = None,
    ):
        self.pages = pages or [["A", "B"], ["C", "D"]]
        self.page_urls = page_urls or [
            f"page-{index + 1}" for index in range(len(self.pages))
        ]
        self.current_url = self.page_urls[
            min(start_page_index, len(self.page_urls) - 1)
        ]
        self.page_index = start_page_index
        self.called: list[tuple[Any, ...]] = []
        self._script_result = script_result
        self._script_side_effect = script_side_effect
        self._next_button_href = next_button_href
        self._next_button_displayed = next_button_displayed
        self._next_button_enabled = next_button_enabled
        self._next_button_missing = next_button_missing
        self._click_advances_url_to = click_advances_url_to
        self._mark_incomplete_a = mark_incomplete_a
        self._next_button_selectors = (
            set(NEXT_BUTTON_LOCATORS)
            if next_button_selectors is None
            else next_button_selectors
        )

    def get_products_callback(self, elements, *, page_number):
        products = list(elements)
        incomplete_items = []
        if self._mark_incomplete_a and "A" in products:
            incomplete_items.append({"name": "A", "missing": ["unit_price"]})
        return {"products": products, "incomplete_items": incomplete_items}

    def execute_script(self, script, *args):
        if self._script_side_effect is not None:
            raise self._script_side_effect
        if self._click_advances_url_to is not None and "click()" in script:
            self.current_url = self._click_advances_url_to
        return self._script_result

    def find_elements(self, by, value):
        if by == "tag name" and value == "wc-product-tile":
            return self.pages[self.page_index]
        return []

    def find_element(self, by, value):
        if by == "tag name" and value == "wc-product-tile":
            # Return first product tile for the current page
            tiles = (
                self.pages[self.page_index] if self.page_index < len(self.pages) else []
            )
            if tiles:
                return tiles[0]
            raise Exception("no product tiles")
        if (by, value) in self._next_button_selectors:
            if self._next_button_missing:
                raise Exception("no next button")
            if self.page_index < len(self.pages) - 1:
                next_href = self._next_button_href
                if next_href == "page-2" and self.page_index + 1 < len(self.page_urls):
                    next_href = self.page_urls[self.page_index + 1]
                return DummyNextButton(
                    next_href,
                    displayed=self._next_button_displayed,
                    enabled=self._next_button_enabled,
                )
            raise Exception("no next page")
        raise Exception("unsupported selector")

    def get(self, url):
        self.called.append(("get", url))
        self.current_url = url
        if url in self.page_urls:
            self.page_index = self.page_urls.index(url)
            return

        if url.startswith("page-"):
            try:
                self.page_index = max(0, int(url.split("-", 1)[1]) - 1)
            except ValueError:
                pass

    def quit(self):
        self.called.append(("quit",))


class DummyDriverFactory:
    def __init__(
        self,
        *,
        pages: list[list[str]] | None = None,
        page_urls: list[str] | None = None,
        failures_before_success: int = 0,
    ):
        self.pages = pages or [["A", "B"], ["C", "D"]]
        self.page_urls = page_urls or [
            f"page-{index + 1}" for index in range(len(self.pages))
        ]
        self.failures_before_success = failures_before_success
        self.calls = 0
        self.created_drivers: list[DummySeleniumSession] = []

    def __call__(self):
        self.calls += 1
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise RuntimeError("driver creation failed")

        driver = DummySeleniumSession(pages=self.pages, page_urls=self.page_urls)
        driver.quit = lambda: None
        self.created_drivers.append(driver)
        return driver


class DummySupermarketFactory:
    """Test double for supermarket_factory function."""

    def __init__(self, resolved_supermarket=None):
        self.resolved_supermarket = resolved_supermarket or DummySupermarket()
        self.factory_calls = []

    def __call__(
        self,
        supermarket_key,
        file_handler_dep,
        logger_dep,
        web_driver_dep,
        product_parser_dep,
    ):
        self.factory_calls.append(supermarket_key)
        return self.resolved_supermarket
