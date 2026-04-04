# test_helpers.py
"""
Shared dummy/mock classes for Boxaroo unit tests.
"""
from logger import ILogger, LoggingLevel


class DummyLogger(ILogger):
    def __init__(self, logging_level=None):
        self.logging_level = logging_level or LoggingLevel.INFO

    def debug(self, message):
        pass

    def log(self, message):
        pass

    def error(self, message):
        pass


class DummyFileHandler:
    def __init__(self):
        self.saved = []

    def store_data(self, data):
        self.saved.append(data)


class DummyWebDriver:
    def __init__(self):
        self.called = []

    def get_page(self, url):
        self.called.append(("get_page", url))

    def get_products(self, _callback=None):
        return []

    def quit(self):
        self.called.append(("quit",))

    def execute_script(self, script):
        self.called.append(("execute_script", script))
        return ""

    def reload_page(self):
        self.called.append(("reload_page",))


class DummySupermarket:
    def __init__(self, logger, logic=None):
        self.logger = logger
        self.logic = logic
        self.get_data_called = False

    def get_data(self, list_size=None):
        if self.logic:
            self.logic(self.logger, list_size)
        self.get_data_called = True
