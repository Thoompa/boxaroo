# test_helpers.py
"""
Shared dummy/mock classes for Boxaroo unit tests.
"""
from typing import Any

from Code.file_handler import IFileHandler
from Code.logger import ILogger, LoggingLevel
from Code.product_parser import IProductParser, ProductParseResult
from Code.web_driver import WebDriver


class DummyLogger(ILogger):
    def __init__(self, logging_level=None):
        self.logging_level = logging_level or LoggingLevel.INFO
        self.records = []

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


class DummyWebDriver:
    def __init__(self):
        self.called = []
        self.script_response = ""
        self.category_total_items = None
        self.category_total_items_sequence = []
        self.products_response = []

    def get_page(self, url):
        self.called.append(("get_page", url))

    def get_products(self, _callback=None):
        self.called.append(("get_products",))
        return self.products_response

    def quit(self):
        self.called.append(("quit",))

    def execute_script(self, script, *args):
        self.called.append(("execute_script", script))
        if callable(self.script_response):
            return self.script_response(script, *args)
        if isinstance(self.script_response, list):
            return self.script_response.pop(0) if self.script_response else ""
        return self.script_response

    def reload_page(self):
        self.called.append(("reload_page",))

    def get_category_total_items(self):
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


class DummySupermarket:
    def __init__(self, logger, logic=None):
        self.logger = logger
        self.logic = logic
        self.get_data_called = False
        self.last_list_size = None
        self.last_refresh_category_lists = None

    def get_data(self, list_size=None, refresh_category_lists=False):
        if self.logic:
            self.logic(self.logger, list_size, refresh_category_lists)
        self.get_data_called = True
        self.last_list_size = list_size
        self.last_refresh_category_lists = refresh_category_lists


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


class FakeNextButton:
    def __init__(self, href):
        self.href = href

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def get_attribute(self, name):
        if name == "href":
            return self.href
        return None


class FakeSeleniumDriver:
    def __init__(self):
        self.current_url = "https://www.woolworths.com.au/shop/browse/electronics"
        self.page_index = 0
        self.pages = [["A", "B"], ["C", "D"]]

    def execute_script(self, script, *args):
        return None

    def find_elements(self, by, value):
        if by == "tag name" and value == "wc-product-tile":
            return self.pages[self.page_index]
        return []

    def find_element(self, by, value):
        if by == "css selector" and value == ".paging-next":
            if self.page_index == 0:
                return FakeNextButton(
                    "https://www.woolworths.com.au/shop/browse/electronics?pageNumber=2"
                )
            raise Exception("no next page")
        raise Exception("unsupported selector")

    def get(self, url):
        self.current_url = url
        if "pageNumber=2" in url:
            self.page_index = 1
