# test_helpers.py
"""
Shared dummy/mock classes for Boxaroo unit tests.
"""


class DummyLogger:
    def __init__(self):
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
