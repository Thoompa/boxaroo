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
    def __init__(
        self,
        logger=None,
        file_handler=None,
        web_driver=None,
        product_parser=None,
        logic=None,
        products_to_store=None,
        get_data_error=None,
        get_data_result=None,
    ):
        self.file_handler = file_handler
        self.logger = logger
        self.web_driver = web_driver
        self.product_parser = product_parser

        self.logic = logic
        self.products_to_store = products_to_store
        self.get_data_error = get_data_error
        self.get_data_result = get_data_result
        self.get_data_called = False
        self.last_list_size = None
        self.last_refresh_category_lists = None

    def get_data(self, list_size=None, refresh_category_lists=False):
        if self.logic:
            self.logic(self.logger, list_size, refresh_category_lists)
        self.get_data_called = True
        self.last_list_size = list_size
        self.last_refresh_category_lists = refresh_category_lists
        if self.products_to_store is not None and self.file_handler is not None:
            self.file_handler.store_data(self.products_to_store)
        if self.get_data_error is not None:
            raise self.get_data_error
        return self.get_data_result


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
