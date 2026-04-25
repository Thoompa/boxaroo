import pytest
from Code.web_driver import WebDriver
import Code.web_driver as web_driver_module
from Tests.test_helpers import (
    DummyWebDriverShell,
    DummyWait,
    DummySeleniumDriver,
    DummyProductElement,
)


# ============================================================
# get_category_total_items – parsing product counts from page content
# ============================================================


def test_get_category_total_items_from_selector(monkeypatch):
    # GIVEN: the script response contains a plain product count
    driver = DummyWebDriverShell()
    driver._category_total_script_response = "Showing 480 products"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: the numeric total is parsed correctly
    assert total == 480


def test_get_category_total_items_fallback_to_tile_count(monkeypatch):
    # GIVEN: the product count is only available from tile elements on the page
    driver = DummyWebDriverShell()
    driver._category_total_script_response = "wc-product-tile:42"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: the correct product count is still returned
    assert total == 42


def test_get_category_total_items_parses_total_from_range_text(monkeypatch):
    # GIVEN: the page displays the product count as a pagination range
    driver = DummyWebDriverShell()
    driver._category_total_script_response = "1 - 36 of 10,000 Products"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: the total product count is returned correctly
    assert total == 10000


def test_get_category_total_items_parses_total_from_last_numeric_token():
    # GIVEN: the page shows a count string with no "of N" pattern
    driver = DummyWebDriverShell()
    driver._category_total_script_response = "Items 1,200"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: the last numeric token is parsed and returned
    assert total == 1200


# ============================================================
# get_category_total_items – handling missing or unrecognisable counts
# ============================================================


def test_get_category_total_items_returns_none_for_empty_text():
    # GIVEN: the page provides no product count text
    driver = DummyWebDriverShell()
    driver._category_total_script_response = ""

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: None is returned
    assert total is None


def test_get_category_total_items_returns_none_for_non_numeric_text():
    # GIVEN: the page shows text that contains no recognisable product count
    driver = DummyWebDriverShell()
    driver._category_total_script_response = "No products found"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: None is returned
    assert total is None


def test_get_category_total_items_returns_none_when_script_returns_none():
    # GIVEN: the product count element is absent from the page
    driver = DummyWebDriverShell()
    driver._category_total_script_response = None

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: None is returned
    assert total is None


def test_get_category_total_items_returns_none_for_malformed_tile_count():
    # GIVEN: the wc-product-tile fallback value is not a valid integer
    driver = DummyWebDriverShell()
    driver._category_total_script_response = "wc-product-tile:abc"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: None is returned
    assert total is None


# ============================================================
# get_products – pagination and aggregation
# ============================================================


def test_get_products_page_stats_aggregation(monkeypatch):
    # GIVEN: a two-page category where only the first page reports an incomplete item
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver(mark_incomplete_a=True)

    # WHEN: the products are retrieved
    res = WebDriver.get_products(driver, driver.driver.get_products_callback)

    # THEN: the scrape summary correctly reports the page number, total scraped, and incomplete count
    assert isinstance(res, dict)
    assert res["page_stats"][0]["page"] == 1
    assert res["page_stats"][0]["scraped"] == 2
    assert res["page_stats"][0]["incomplete"] == 1


def test_get_products_advances_using_next_href(monkeypatch):
    # GIVEN: a category with products spread across two pages
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver()

    # WHEN: the products are retrieved across both pages
    result = WebDriver.get_products(
        driver, lambda elements: {"products": list(elements), "incomplete_items": []}
    )

    # THEN: products from both pages are combined and page_stats has two entries
    assert result["products"] == ["A", "B", "C", "D"]
    assert len(result["page_stats"]) == 2
    assert result["page_stats"][1]["page"] == 2


def test_advance_to_next_page_uses_click_when_href_is_empty(monkeypatch):
    # GIVEN: the next pagination button has no href, requiring a JS click
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver(
        next_button_href="", click_advances_url_to="page-2"
    )

    # WHEN: the next page is advanced
    result = WebDriver._advance_to_next_page(driver)

    # THEN: click-based navigation succeeds and True is returned
    assert result is True
    assert driver.driver.current_url == "page-2"


def test_advance_to_next_page_returns_false_when_button_is_hidden(monkeypatch):
    # GIVEN: the next button exists but is not visible on the page
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver(next_button_displayed=False)

    # WHEN: the next page is advanced
    result = WebDriver._advance_to_next_page(driver)

    # THEN: False is returned and no navigation occurs
    assert result is False


def test_advance_to_next_page_returns_false_when_button_is_missing(monkeypatch):
    # GIVEN: there is no next pagination button on the page
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver(next_button_missing=True)

    # WHEN: the next page is advanced
    result = WebDriver._advance_to_next_page(driver)

    # THEN: False is returned and no navigation occurs
    assert result is False


# ============================================================
# get_products – result structure contract
# ============================================================


def test_get_products_payload_always_contains_required_keys(monkeypatch):
    # GIVEN: a standard two-page product listing
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver()

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver,
        lambda elements: {
            "products": list(elements),
            "incomplete_items": [{"name": "A", "missing": ["unit_price"]}],
        },
    )

    # THEN: the result always contains the three required top-level keys
    assert "products" in result
    assert "incomplete_items" in result
    assert "page_stats" in result


def test_get_products_page_stats_track_incomplete_count(monkeypatch):
    # GIVEN: a callback that always reports one incomplete item per page
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver()

    # WHEN: products are retrieved across two pages
    result = WebDriver.get_products(
        driver,
        lambda elements: {
            "products": list(elements),
            "incomplete_items": [{"name": elements[0], "missing": ["price"]}],
        },
    )

    # THEN: each page's stats record one incomplete item
    assert len(result["page_stats"]) == 2
    assert result["page_stats"][0]["incomplete"] == 1
    assert result["page_stats"][1]["incomplete"] == 1


def test_get_products_callback_receives_plain_string_payloads(monkeypatch):
    # GIVEN: a callback that records every payload it receives
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver()
    seen_payloads = []

    def callback(product_texts):
        seen_payloads.extend(product_texts)
        return {"products": list(product_texts), "incomplete_items": []}

    # WHEN: the products are retrieved
    WebDriver.get_products(driver, callback)

    # THEN: the callback received plain strings for all products across both pages
    assert seen_payloads == ["A", "B", "C", "D"]
    assert all(isinstance(item, str) for item in seen_payloads)


def test_get_products_supports_list_return_from_callback(monkeypatch):
    # GIVEN: a callback that returns a plain list instead of a dict
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver()

    # WHEN: the products are retrieved
    result = WebDriver.get_products(driver, lambda elements: list(elements))

    # THEN: all products are still aggregated correctly
    assert result["products"] == ["A", "B", "C", "D"]
    assert result["incomplete_items"] == []
    assert len(result["page_stats"]) == 2


def test_get_products_without_callback_returns_empty_products(monkeypatch):
    # GIVEN: no callback is provided
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver()

    # WHEN: the products are retrieved
    result = WebDriver.get_products(driver)

    # THEN: products and incomplete_items are empty; page_stats still records tile counts
    assert result["products"] == []
    assert result["incomplete_items"] == []
    assert len(result["page_stats"]) == 2
    assert result["page_stats"][0]["product_tiles"] == 2
    assert result["page_stats"][0]["scraped"] == 0


# ============================================================
# get_products – resilience and error handling
# ============================================================


def test_get_products_reloads_page_on_per_element_timeout(monkeypatch):
    # GIVEN: an element on the first page that times out during text extraction
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver()
    reload_calls = []
    driver.reload_page = lambda: reload_calls.append(1)
    call_count = {"n": 0}

    def patched_extract(element):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TimeoutError("element stale")
        return str(element)

    driver._extract_text_from_product_element = patched_extract

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver, lambda texts: {"products": list(texts), "incomplete_items": []}
    )

    # THEN: the page is reloaded once; the failed element is skipped and tracked in stats
    assert len(reload_calls) == 1
    assert result["products"] == ["B", "C", "D"]
    assert len(result["page_stats"]) == 2
    assert result["page_stats"][0]["product_tiles"] == 2
    assert result["page_stats"][0]["extraction_failures"] == 1
    assert result["page_stats"][0]["scraped"] == 1
    assert result["page_stats"][1]["product_tiles"] == 2
    assert result["page_stats"][1]["extraction_failures"] == 0
    assert result["page_stats"][1]["scraped"] == 2


def test_get_products_records_failure_without_reload_on_generic_error(monkeypatch):
    # GIVEN: an element that raises a generic error during text extraction
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver()
    reload_calls = []
    driver.reload_page = lambda: reload_calls.append(1)
    call_count = {"n": 0}

    def patched_extract(element):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise ValueError("parse failed")
        return str(element)

    driver._extract_text_from_product_element = patched_extract

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver, lambda texts: {"products": list(texts), "incomplete_items": []}
    )

    # THEN: the page is not reloaded; the failure is counted and remaining elements are scraped
    assert len(reload_calls) == 0
    assert result["page_stats"][0]["extraction_failures"] == 1
    assert result["page_stats"][0]["scraped"] == 1
    assert result["products"] == ["B", "C", "D"]


# ============================================================
# Reading text from a product element
# ============================================================


def test_extract_text_returns_empty_for_none_element():
    # GIVEN: a None element
    driver = DummyWebDriverShell()

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, None)

    # THEN: an empty string is returned
    assert result == ""


def test_extract_text_returns_stripped_string_passthrough():
    # GIVEN: a plain string element with surrounding whitespace
    driver = DummyWebDriverShell()
    text = "  Milk 2L  "

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, text)

    # THEN: the string is returned stripped
    assert result == "Milk 2L"


def test_extract_text_uses_element_dot_text():
    # GIVEN: a product element with recognisable text
    driver = DummyWebDriverShell()
    element = DummyProductElement(text="Bread 1 loaf\n$3.00\n$3.00 / 1EA")

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, element)

    # THEN: the element's text is returned verbatim
    assert result == "Bread 1 loaf\n$3.00\n$3.00 / 1EA"


def test_extract_text_shadow_root_fallback_when_text_is_empty():
    # GIVEN: a product element with no directly accessible text
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver(script_result="Shadow Product 500g")
    element = DummyProductElement(text="")

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, element)

    # THEN: the product text is successfully retrieved
    assert result == "Shadow Product 500g"


def test_extract_text_falls_through_to_shadow_when_text_raises():
    # GIVEN: a product element that errors on direct text access
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver(script_result="Shadow Product 500g")
    element = DummyProductElement(raise_on_text=True)

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, element)

    # THEN: the product text is successfully retrieved
    assert result == "Shadow Product 500g"


def test_extract_text_stringifies_non_string_shadow_result():
    # GIVEN: a product element whose retrieved text value is not a string
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver(script_result=42)
    element = DummyProductElement(text="")

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, element)

    # THEN: a string is always returned
    assert isinstance(result, str)


def test_extract_text_propagates_timeout_error_from_shadow_root():
    # GIVEN: a product element that times out during text retrieval
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver(
        script_side_effect=TimeoutError("stale element")
    )
    element = DummyProductElement(text="")

    # WHEN: text is retrieved from the element
    # THEN: a TimeoutError is raised
    with pytest.raises(TimeoutError):
        WebDriver._extract_text_from_product_element(driver, element)


def test_extract_text_propagates_timeout_error_from_element_dot_text():
    # GIVEN: a product element whose text property raises a TimeoutError
    driver = DummyWebDriverShell()
    element = DummyProductElement(text_error=TimeoutError("stale element"))

    # WHEN: text is retrieved from the element
    # THEN: a TimeoutError is raised
    with pytest.raises(TimeoutError):
        WebDriver._extract_text_from_product_element(driver, element)


def test_extract_text_returns_empty_when_shadow_root_returns_none():
    # GIVEN: a product element whose shadow root extraction returns None
    driver = DummyWebDriverShell()
    driver.driver = DummySeleniumDriver()  # script_result defaults to None
    element = DummyProductElement(text="")

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, element)

    # THEN: an empty string is returned
    assert result == ""
