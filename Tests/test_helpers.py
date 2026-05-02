# test_helpers.py
"""
Shared dummy/mock classes for Boxaroo unit tests.
"""
from typing import Any, Callable

from Code.file_handler import IFileHandler
from Code.contracts import (
    CategoryData,
    ISuperMarket,
    ListSize,
    ProductsData,
    ProductsPageResult,
)
from Code.logger import ILogger, LoggingLevel
from Code.product_parser import IProductParser, ProductParseResult
from Code.web_driver import IWebDriver, WebDriver


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

    def error(self, message):
        self.records.append(("ERROR", message))


class DummyFileHandler(IFileHandler):
    def __init__(self):
        self.saved = []

    def store_data(self, data):
        self.saved.append(data)


class DummyWebDriver(IWebDriver):
    def __init__(self):
        self.called = []
        self.script_response = ""
        self.category_total_items = None
        self.category_total_items_sequence = []
        self.products_response: ProductsPageResult = {
            "products": [],
            "incomplete_items": [],
            "page_stats": [],
        }

    def get_page(self, url: str) -> None:
        self.called.append(("get_page", url))

    def get_products(
        self,
        _callback: Callable[[list[str]], ProductsData | list[list[str]]] | None = None,
    ) -> ProductsPageResult:
        self.called.append(("get_products",))
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
        self, list_size: ListSize = ListSize.FULL, refresh_category_lists: bool = False
    ) -> list[str]:
        if self.logic:
            self.logic(self.logger, list_size, refresh_category_lists)
        self.last_list_size = list_size
        self.last_refresh_category_lists = refresh_category_lists
        self.get_categories_called = True
        if self.get_categories_error is not None:
            raise self.get_categories_error
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


class DummyWebDriverShell(WebDriver):
    def __init__(self, products_response=None):
        self.scripts = []
        self.driver: Any = None
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

    def get_products(self, _callback=None):
        self.page_saved += 1
        if _callback and "products" in self._products_response:
            _callback(self._products_response["products"])
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
        return True


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


class DummySeleniumDriver:
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
    ):
        self.current_url = "page-1"
        self.page_index = 0
        self.pages = [["A", "B"], ["C", "D"]]
        self._script_result = script_result
        self._script_side_effect = script_side_effect
        self._next_button_href = next_button_href
        self._next_button_displayed = next_button_displayed
        self._next_button_enabled = next_button_enabled
        self._next_button_missing = next_button_missing
        self._click_advances_url_to = click_advances_url_to
        self._mark_incomplete_a = mark_incomplete_a

    def get_products_callback(self, elements):
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
        if by == "css selector" and value == ".paging-next":
            if self._next_button_missing:
                raise Exception("no next button")
            if self.page_index == 0:
                return DummyNextButton(
                    self._next_button_href,
                    displayed=self._next_button_displayed,
                    enabled=self._next_button_enabled,
                )
            raise Exception("no next page")
        raise Exception("unsupported selector")

    def get(self, url):
        self.current_url = url
        if url == "page-2":
            self.page_index = 1


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
