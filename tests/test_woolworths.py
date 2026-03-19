import pytest

from woolworths import Woolworths


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


class DummyElement:
    def __init__(self, text):
        self._text = text

    @property
    def text(self):
        return self._text


class DummyWebDriver:
    def __init__(self, script_response=None):
        self.script_response = script_response
        self.scripts_executed = []

    def execute_script(self, script, element=None):
        self.scripts_executed.append(script)
        return self.script_response


@pytest.fixture
def logger():
    return DummyLogger()


@pytest.fixture
def file_handler():
    return DummyFileHandler()


@pytest.fixture
def web_driver():
    return DummyWebDriver()


@pytest.fixture
def woollies(file_handler, logger, web_driver):
    return Woolworths(file_handler=file_handler, logger=logger, web_driver=web_driver)


def test_parse_product_data_full(woollies):
    text = """$1.20
$1.20 / 1EA
2 FOR $2.00 - $1.00/1EA
Avocado Shepard each
Add to cart
Save to list..."""

    parsed = woollies._parse_product_data(text)

    assert parsed == ["Avocado Shepard each", "$1.20", "$1.20 / 1EA", "2 FOR $2.00 - $1.00/1EA"]


def test_parse_product_data_missing_price_unit(woollies):
    text = """Avocado Shepard each
Add to cart
"""

    parsed = woollies._parse_product_data(text)

    assert parsed[0] == "Avocado Shepard each"
    assert parsed[1] == ""
    assert parsed[2] == ""


def test_parse_product_data_non_string(woollies):
    parsed = woollies._parse_product_data(None)

    assert parsed == ["", "", "", ""]


def test_get_product_string_from_element_with_shadow_root(woollies):
    # Simulate a layout where element text is empty, but JavaScript from shadow root returns data
    element = DummyElement("")
    woollies.driver.script_response = "$0.50\n$0.50 / 1EA\nTest Product each\n"

    out = woollies._get_product_string_from_element(element)

    assert "Test Product each" in out


def test_get_products_data_incomplete_tracking(woollies):
    product_inputs = ["$2.00\nProduct One each\n", "Product Two each\n$1.00 / 1EA\n"]

    # Force _get_product_string_from_element to return our test text per element
    def fake_get_product_string(element):
        return element

    woollies._get_product_string_from_element = fake_get_product_string

    fake_elements = product_inputs
    result = woollies._get_products_data(fake_elements)

    assert isinstance(result, dict)
    assert len(result["products"]) == 2
    assert len(result["incomplete_items"]) == 2

    assert result["products"][0][0] == "Product One each"
    assert result["products"][0][1] == "$2.00"
    assert result["products"][1][0] == "Product Two each"
    assert result["products"][1][1] == "$1.00 / 1EA" or result["products"][1][1] == ""
