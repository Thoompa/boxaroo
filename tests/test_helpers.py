# test_helpers.py
"""
Shared dummy/mock classes for Boxaroo unit tests.
"""
from logger import ILogger, LoggingLevel


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


class DummyFileHandler:
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


class DummyElement:
    def __init__(self, text):
        self._text = text

    @property
    def text(self):
        return self._text


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
