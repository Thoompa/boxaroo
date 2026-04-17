import pytest
from Code.web_driver import WebDriver
import Code.web_driver as web_driver_module
from tests.test_helpers import (
    DummyWebDriverShell,
    DummyWait,
    FakeSeleniumDriver,
)


def test_get_category_total_items_from_selector(monkeypatch):
    driver = DummyWebDriverShell()
    driver._category_total_script_response = "Showing 480 products"

    total = driver.get_category_total_items()

    assert total == 480


def test_get_category_total_items_fallback_to_tile_count(monkeypatch):
    driver = DummyWebDriverShell()
    # This is returned because no selector is found and we rely on wc-product-tile fallback
    driver._category_total_script_response = "wc-product-tile:42"

    total = driver.get_category_total_items()

    assert total == 42


def test_get_category_total_items_parses_total_from_range_text(monkeypatch):
    driver = DummyWebDriverShell()
    driver._category_total_script_response = "1 - 36 of 10,000 Products"

    total = driver.get_category_total_items()

    assert total == 10000


def test_get_products_page_stats_aggregation(monkeypatch):
    driver = DummyWebDriverShell(
        products_response={
            "products": ["A", "B"],
            "incomplete_items": [{"name": "A", "missing": ["unit_price"]}],
            "page_stats": [
                {"page": 1, "product_tiles": 2, "scraped": 2, "incomplete": 1}
            ],
        }
    )
    res = driver.get_products(
        lambda x: {
            "products": ["A", "B"],
            "incomplete_items": [{"name": "A", "missing": ["unit_price"]}],
        }
    )

    assert isinstance(res, dict)
    assert res["page_stats"][0]["page"] == 1
    assert res["page_stats"][0]["scraped"] == 2
    assert res["page_stats"][0]["incomplete"] == 1


def test_get_products_advances_using_next_href(monkeypatch):
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)

    driver = DummyWebDriverShell()
    driver.driver = FakeSeleniumDriver()

    result = WebDriver.get_products(
        driver, lambda elements: {"products": list(elements), "incomplete_items": []}
    )

    assert result["products"] == ["A", "B", "C", "D"]
    assert len(result["page_stats"]) == 2
    assert result["page_stats"][1]["page"] == 2


# ============================================================
# SEAM: Driver boundary – get_category_total_items edge cases
# ============================================================


def test_get_category_total_items_returns_none_for_empty_text():
    driver = DummyWebDriverShell()
    driver._category_total_script_response = ""

    total = driver.get_category_total_items()

    assert total is None


def test_get_category_total_items_returns_none_for_non_numeric_text():
    driver = DummyWebDriverShell()
    driver._category_total_script_response = "No products found"

    # "No products found" has no digit patterns that match any extractor
    total = driver.get_category_total_items()

    assert total is None


def test_get_category_total_items_returns_none_when_script_returns_none():
    driver = DummyWebDriverShell()
    driver._category_total_script_response = None

    total = driver.get_category_total_items()

    assert total is None


# ============================================================
# SEAM: Driver boundary – get_products payload contract
# ============================================================


def test_get_products_payload_always_contains_required_keys(monkeypatch):
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)

    # Run the production method, not the helper passthrough.
    driver = DummyWebDriverShell()
    driver.driver = FakeSeleniumDriver()

    result = WebDriver.get_products(
        driver,
        lambda elements: {
            "products": list(elements),
            "incomplete_items": [{"name": "A", "missing": ["unit_price"]}],
        },
    )

    assert "products" in result
    assert "incomplete_items" in result
    assert "page_stats" in result


def test_get_products_page_stats_track_incomplete_count(monkeypatch):
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)

    # Use two pages from FakeSeleniumDriver and assert production page_stats math.
    driver = DummyWebDriverShell()
    driver.driver = FakeSeleniumDriver()

    result = WebDriver.get_products(
        driver,
        lambda elements: {
            "products": list(elements),
            "incomplete_items": [{"name": elements[0], "missing": ["price"]}],
        },
    )

    assert len(result["page_stats"]) == 2
    assert result["page_stats"][0]["incomplete"] == 1
    assert result["page_stats"][1]["incomplete"] == 1


def test_get_products_callback_receives_plain_string_payloads(monkeypatch):
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)

    driver = DummyWebDriverShell()
    driver.driver = FakeSeleniumDriver()

    seen_payloads = []

    def callback(product_texts):
        seen_payloads.extend(product_texts)
        return {"products": list(product_texts), "incomplete_items": []}

    WebDriver.get_products(driver, callback)

    assert seen_payloads == ["A", "B", "C", "D"]
    assert all(isinstance(item, str) for item in seen_payloads)


# ============================================================
# SEAM: Adapter boundary – _extract_text_from_product_element
# ============================================================


def test_extract_text_returns_empty_for_none_element():
    driver = DummyWebDriverShell()
    result = WebDriver._extract_text_from_product_element(driver, None)
    assert result == ""


def test_extract_text_returns_stripped_string_passthrough():
    driver = DummyWebDriverShell()
    result = WebDriver._extract_text_from_product_element(driver, "  Milk 2L  ")
    assert result == "Milk 2L"


def test_extract_text_uses_element_dot_text():
    driver = DummyWebDriverShell()

    class FakeElement:
        text = "Bread 1 loaf\n$3.00\n$3.00 / 1EA"

    result = WebDriver._extract_text_from_product_element(driver, FakeElement())
    assert result == "Bread 1 loaf\n$3.00\n$3.00 / 1EA"


def test_extract_text_shadow_root_fallback_when_text_is_empty():
    driver = DummyWebDriverShell()

    class FakeInnerDriver:
        def execute_script(self, script, *args):
            return "Shadow Product 500g"

    driver.driver = FakeInnerDriver()

    class EmptyTextElement:
        text = ""

    result = WebDriver._extract_text_from_product_element(driver, EmptyTextElement())
    assert result == "Shadow Product 500g"


def test_extract_text_falls_through_to_shadow_when_text_raises():
    driver = DummyWebDriverShell()

    class FakeInnerDriver:
        def execute_script(self, script, *args):
            return "Shadow Product 500g"

    driver.driver = FakeInnerDriver()

    class BrokenTextElement:
        @property
        def text(self):
            raise AttributeError("no text attribute")

    result = WebDriver._extract_text_from_product_element(driver, BrokenTextElement())
    assert result == "Shadow Product 500g"


def test_extract_text_stringifies_non_string_shadow_result():
    driver = DummyWebDriverShell()

    class FakeInnerDriver:
        def execute_script(self, script, *args):
            return 42

    driver.driver = FakeInnerDriver()

    class EmptyTextElement:
        text = ""

    result = WebDriver._extract_text_from_product_element(driver, EmptyTextElement())
    assert isinstance(result, str)


def test_extract_text_propagates_timeout_error_from_shadow_root():
    driver = DummyWebDriverShell()

    class FakeInnerDriver:
        def execute_script(self, script, *args):
            raise TimeoutError("stale element")

    driver.driver = FakeInnerDriver()

    class EmptyTextElement:
        text = ""

    with pytest.raises(TimeoutError):
        WebDriver._extract_text_from_product_element(driver, EmptyTextElement())


def test_get_products_reloads_page_on_per_element_timeout(monkeypatch):
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)

    driver = DummyWebDriverShell()
    driver.driver = FakeSeleniumDriver()

    reload_calls = []
    driver.reload_page = lambda: reload_calls.append(1)

    call_count = {"n": 0}

    def patched_extract(element):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TimeoutError("element stale")
        return str(element)

    driver._extract_text_from_product_element = patched_extract

    result = WebDriver.get_products(
        driver, lambda texts: {"products": list(texts), "incomplete_items": []}
    )

    assert len(reload_calls) == 1
    assert result["products"] == ["B", "C", "D"]
    assert len(result["page_stats"]) == 2
    assert result["page_stats"][0]["product_tiles"] == 2
    assert result["page_stats"][0]["extraction_failures"] == 1
    assert result["page_stats"][0]["scraped"] == 1
    assert result["page_stats"][1]["product_tiles"] == 2
    assert result["page_stats"][1]["extraction_failures"] == 0
    assert result["page_stats"][1]["scraped"] == 2
