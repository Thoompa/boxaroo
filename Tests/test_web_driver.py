import pytest
from Code.web_driver import WebDriver
import Code.web_driver as web_driver_module
from Tests.test_helpers import (
    DummyWebDriverHarness,
    DummyWait,
    DummySeleniumSession,
    DummyProductElement,
    DummyLogger,
    DummyDriverFactory,
)


# ============================================================
# WebDriver setup – browser/driver discovery
# ============================================================


def test_resolve_driver_binaries_prefers_env_paths(monkeypatch):
    # GIVEN: both executable environment variables point to valid binaries
    env_map = {
        "CHROME_BINARY": "/opt/browser/chrome",
        "CHROMEDRIVER": "/opt/driver/chromedriver",
    }
    monkeypatch.setattr(web_driver_module.os, "getenv", lambda key: env_map.get(key))
    monkeypatch.setattr(web_driver_module.os.path, "isfile", lambda path: True)
    monkeypatch.setattr(web_driver_module.os, "access", lambda path, mode: True)
    monkeypatch.setattr(web_driver_module.shutil, "which", lambda name: None)

    # WHEN: driver binaries are resolved
    browser_binary, chromedriver_binary = WebDriver._resolve_driver_binaries()

    # THEN: environment values are used for both binaries
    assert browser_binary == "/opt/browser/chrome"
    assert chromedriver_binary == "/opt/driver/chromedriver"


def test_resolve_driver_binaries_falls_back_to_path_search(monkeypatch):
    # GIVEN: environment overrides are absent but PATH contains Chrome and chromedriver
    monkeypatch.setattr(web_driver_module.os, "getenv", lambda key: None)
    monkeypatch.setattr(web_driver_module.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(web_driver_module.os, "access", lambda path, mode: False)

    def resolve_from_path(name):
        mapping = {
            "chromium": None,
            "chromium-browser": None,
            "google-chrome": "/usr/bin/google-chrome",
            "google-chrome-stable": None,
            "chromedriver": "/usr/bin/chromedriver",
        }
        return mapping.get(name)

    monkeypatch.setattr(web_driver_module.shutil, "which", resolve_from_path)

    # WHEN: driver binaries are resolved
    browser_binary, chromedriver_binary = WebDriver._resolve_driver_binaries()

    # THEN: resolved PATH binaries are returned
    assert browser_binary == "/usr/bin/google-chrome"
    assert chromedriver_binary == "/usr/bin/chromedriver"


def test_resolve_driver_binaries_raises_with_linux_setup_guidance(monkeypatch):
    # GIVEN: neither browser nor chromedriver can be discovered
    monkeypatch.setattr(web_driver_module.os, "getenv", lambda key: None)
    monkeypatch.setattr(web_driver_module.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(web_driver_module.os, "access", lambda path, mode: False)
    monkeypatch.setattr(web_driver_module.shutil, "which", lambda name: None)

    # WHEN: driver binary resolution is attempted
    # THEN: a setup error is raised with install guidance and override hints
    with pytest.raises(RuntimeError) as exc_info:
        WebDriver._resolve_driver_binaries()

    message = str(exc_info.value)
    assert "sudo apt install chromium chromium-driver" in message
    assert "sudo pacman -S chromium chromedriver" in message
    assert "CHROME_BINARY" in message
    assert "CHROMEDRIVER" in message


# ============================================================
# get_category_total_items – parsing product counts from page content
# ============================================================


def test_get_category_total_items_from_selector():
    # GIVEN: the script response contains a plain product count
    driver = DummyWebDriverHarness()
    driver._category_total_script_response = "Showing 480 products"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: the numeric total is parsed correctly
    assert total == 480


def test_get_category_total_items_fallback_to_tile_count():
    # GIVEN: the product count is only available from tile elements on the page
    driver = DummyWebDriverHarness()
    driver._category_total_script_response = "wc-product-tile:42"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: the correct product count is still returned
    assert total == 42


def test_get_category_total_items_parses_total_from_range_text():
    # GIVEN: the page displays the product count as a pagination range
    driver = DummyWebDriverHarness()
    driver._category_total_script_response = "1 - 36 of 10,000 Products"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: the total product count is returned correctly
    assert total == 10000


def test_get_category_total_items_parses_total_from_updated_pagination_component():
    # GIVEN: the page displays the new pagination component text format
    driver = DummyWebDriverHarness()
    driver._category_total_script_response = "1 –to 36 of 557 Products"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: the total product count is returned correctly
    assert total == 557


def test_get_category_total_items_parses_total_from_last_numeric_token():
    # GIVEN: the page shows a count string with no "of N" pattern
    driver = DummyWebDriverHarness()
    driver._category_total_script_response = "Items 1,200"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: the last numeric token is parsed and returned
    assert total == 1200


def test_get_category_total_items_script_includes_pagination_info_selector():
    # GIVEN: the page exposes the total count via the new pagination component class
    driver = DummyWebDriverHarness()
    driver._category_total_script_response = "Showing 1 Products"

    # WHEN: the category total is retrieved
    driver.get_category_total_items()

    # THEN: the extraction script targets the new pagination component class
    assert any(
        "pagination-info_component_pagination-info" in script
        for script in driver.scripts
    )


# ============================================================
# get_category_total_items – handling missing or unrecognisable counts
# ============================================================


def test_get_category_total_items_returns_none_for_empty_text():
    # GIVEN: the page provides no product count text
    driver = DummyWebDriverHarness()
    driver._category_total_script_response = ""

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: None is returned
    assert total is None


def test_get_category_total_items_returns_none_for_non_numeric_text():
    # GIVEN: the page shows text that contains no recognisable product count
    driver = DummyWebDriverHarness()
    driver._category_total_script_response = "No products found"

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: None is returned
    assert total is None


def test_get_category_total_items_returns_none_when_script_returns_none():
    # GIVEN: the product count element is absent from the page
    driver = DummyWebDriverHarness()
    driver._category_total_script_response = None

    # WHEN: the category total is retrieved
    total = driver.get_category_total_items()

    # THEN: None is returned
    assert total is None


def test_get_category_total_items_returns_none_for_malformed_tile_count():
    # GIVEN: the wc-product-tile fallback value is not a valid integer
    driver = DummyWebDriverHarness()
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
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(mark_incomplete_a=True)

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
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession()

    # WHEN: the products are retrieved across both pages
    result = WebDriver.get_products(
        driver,
        lambda elements, *, page_number: {
            "products": list(elements),
            "incomplete_items": [],
        },
    )

    # THEN: products from both pages are combined and page_stats has two entries
    assert result["products"] == ["A", "B", "C", "D"]
    assert len(result["page_stats"]) == 2
    assert result["page_stats"][1]["page"] == 2


def test_advance_to_next_page_uses_click_when_href_is_empty(monkeypatch):
    # GIVEN: the next pagination button has no href, requiring a JS click
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(
        next_button_href="", click_advances_url_to="page-2"
    )

    # WHEN: the next page is advanced
    result = WebDriver._advance_to_next_page(driver)

    # THEN: click-based navigation succeeds and True is returned
    assert result is True
    assert driver.driver.current_url == "page-2"


def test_advance_to_next_page_prefers_rel_next_selector(monkeypatch):
    # GIVEN: the current site exposes the next button via a semantic rel attribute
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(
        next_button_selectors={("css selector", "a[rel='next']")}
    )

    # WHEN: the next page is advanced
    result = WebDriver._advance_to_next_page(driver)

    # THEN: href-based navigation succeeds without the legacy class selector
    assert result is True
    assert driver.driver.current_url == "page-2"


def test_get_next_page_url_uses_legacy_selector_as_fallback():
    # GIVEN: only the legacy pagination selector is available on the page
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(
        next_button_selectors={("css selector", ".paging-next")}
    )

    # WHEN: the next page URL is retrieved
    result = WebDriver._get_next_page_url(driver)

    # THEN: the legacy selector still resolves the next page href
    assert result == "page-2"


def test_advance_to_next_page_returns_false_when_button_is_hidden(monkeypatch):
    # GIVEN: the next button exists but is not visible on the page
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(next_button_displayed=False)

    # WHEN: the next page is advanced
    result = WebDriver._advance_to_next_page(driver)

    # THEN: False is returned and no navigation occurs
    assert result is False


def test_advance_to_next_page_returns_false_when_button_is_missing(monkeypatch):
    # GIVEN: there is no next pagination button on the page
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(next_button_missing=True)

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
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession()

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver,
        lambda elements, *, page_number: {
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
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession()

    # WHEN: products are retrieved across two pages
    result = WebDriver.get_products(
        driver,
        lambda elements, *, page_number: {
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
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession()
    seen_payloads = []

    def callback(product_texts, *, page_number):
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
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession()

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver, lambda elements, *, page_number: list(elements)
    )

    # THEN: all products are still aggregated correctly
    assert result["products"] == ["A", "B", "C", "D"]
    assert result["incomplete_items"] == []
    assert len(result["page_stats"]) == 2


def test_get_products_without_callback_returns_empty_products(monkeypatch):
    # GIVEN: no callback is provided
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession()

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
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession()
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
        driver,
        lambda texts, *, page_number: {
            "products": list(texts),
            "incomplete_items": [],
        },
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
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession()
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
        driver,
        lambda texts, *, page_number: {
            "products": list(texts),
            "incomplete_items": [],
        },
    )

    # THEN: the page is not reloaded; the failure is counted and remaining elements are scraped
    assert len(reload_calls) == 0
    assert result["page_stats"][0]["extraction_failures"] == 1
    assert result["page_stats"][0]["scraped"] == 1
    assert result["products"] == ["B", "C", "D"]


def test_get_products_does_not_mask_callback_typeerror(monkeypatch):
    # GIVEN: a callback that accepts page_number and raises an internal TypeError
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession()

    def callback_with_page_context(elements, *, page_number):
        raise TypeError("internal callback type error")

    # WHEN: products are retrieved with the callback
    # THEN: the internal callback TypeError is propagated as-is
    with pytest.raises(TypeError, match="internal callback type error"):
        WebDriver.get_products(driver, callback_with_page_context)


# ============================================================
# get_products – hard driver reset behavior
# ============================================================


def test_get_products_triggers_driver_reset_after_threshold(monkeypatch):
    # GIVEN: a three-page category and a one-page reset threshold
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    logger = DummyLogger()
    driver = DummyWebDriverHarness()
    original_driver = DummySeleniumSession(
        pages=[["A", "B"], ["C", "D"], ["E", "F"]],
        page_urls=["page-1", "page-2", "page-3"],
    )
    driver.driver = original_driver
    driver.logger = logger
    driver.hard_driver_reset = True
    driver.max_pages_per_session = 1
    factory = DummyDriverFactory(
        pages=[["A", "B"], ["C", "D"], ["E", "F"]],
        page_urls=["page-1", "page-2", "page-3"],
    )
    driver._create_fresh_driver = factory

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver,
        lambda elements, *, page_number: {
            "products": list(elements),
            "incomplete_items": [],
        },
        category_name="beauty",
    )

    # THEN: scraping resumes across driver resets without losing data
    assert result["products"] == ["A", "B", "C", "D", "E", "F"]
    assert len(result["page_stats"]) == 3
    assert original_driver.called.count(("quit",)) == 1
    assert factory.calls == 2
    assert factory.created_drivers[0].called == [("get", "page-2")]
    assert factory.created_drivers[1].called == [("get", "page-3")]
    assert any(
        level == "INFO" and "Driver reset triggered: pages_processed=1" in message
        for level, message in logger.records
    )
    assert any(
        level == "INFO" and "WebDriver reset completed:" in message
        for level, message in logger.records
    )


def test_get_products_does_not_reset_when_category_finishes_before_threshold(
    monkeypatch,
):
    # GIVEN: a single-page category and a higher reset threshold
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    logger = DummyLogger()
    driver = DummyWebDriverHarness()
    original_driver = DummySeleniumSession(pages=[["A", "B"]], page_urls=["page-1"])
    driver.driver = original_driver
    driver.logger = logger
    driver.hard_driver_reset = True
    driver.max_pages_per_session = 12
    factory = DummyDriverFactory(pages=[["A", "B"]], page_urls=["page-1"])
    driver._create_fresh_driver = factory

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver,
        lambda elements, *, page_number: {
            "products": list(elements),
            "incomplete_items": [],
        },
        category_name="bakery",
    )

    # THEN: the category completes without an unnecessary reset
    assert result["products"] == ["A", "B"]
    assert original_driver.called.count(("quit",)) == 0
    assert factory.calls == 0
    assert not any("Driver reset triggered" in message for _, message in logger.records)


def test_get_products_retries_driver_creation_before_succeeding(monkeypatch):
    # GIVEN: driver recreation fails before eventually succeeding
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    logger = DummyLogger()
    driver = DummyWebDriverHarness()
    original_driver = DummySeleniumSession(
        pages=[["A", "B"], ["C", "D"]],
        page_urls=["page-1", "page-2"],
    )
    driver.driver = original_driver
    driver.logger = logger
    driver.hard_driver_reset = True
    driver.max_pages_per_session = 1
    factory = DummyDriverFactory(
        pages=[["A", "B"], ["C", "D"]],
        page_urls=["page-1", "page-2"],
        failures_before_success=2,
    )
    driver._create_fresh_driver = factory

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver,
        lambda elements, *, page_number: {
            "products": list(elements),
            "incomplete_items": [],
        },
        category_name="beauty",
    )

    # THEN: the driver is recreated with retries and the scrape still completes
    assert result["products"] == ["A", "B", "C", "D"]
    assert factory.calls == 3
    assert any(
        level == "INFO" and "WebDriver reset completed:" in message
        for level, message in logger.records
    )


def test_get_products_preserves_page_stats_across_resets(monkeypatch):
    # GIVEN: a multi-page category with a reset occurring mid-scrape
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(
        pages=[["A", "B"], ["C", "D"], ["E", "F"]],
        page_urls=["page-1", "page-2", "page-3"],
    )
    driver.hard_driver_reset = True
    driver.max_pages_per_session = 1
    driver._create_fresh_driver = DummyDriverFactory(
        pages=[["A", "B"], ["C", "D"], ["E", "F"]],
        page_urls=["page-1", "page-2", "page-3"],
    )

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver,
        lambda elements, *, page_number: {
            "products": list(elements),
            "incomplete_items": [{"name": elements[0], "missing": ["price"]}],
        },
        category_name="fruit-veg",
    )

    # THEN: products and incomplete items are preserved across the reset boundary
    assert result["products"] == ["A", "B", "C", "D", "E", "F"]
    assert len(result["incomplete_items"]) == 3
    assert len(result["page_stats"]) == 3


def test_get_products_logs_category_summary_after_reset_run(monkeypatch):
    # GIVEN: a reset-enabled scrape with multiple pages in one category
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    logger = DummyLogger()
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(
        pages=[["A", "B"], ["C", "D"]],
        page_urls=["page-1", "page-2"],
    )
    driver.logger = logger
    driver.hard_driver_reset = True
    driver.max_pages_per_session = 1
    driver._create_fresh_driver = DummyDriverFactory(
        pages=[["A", "B"], ["C", "D"]],
        page_urls=["page-1", "page-2"],
    )

    # WHEN: the products are retrieved
    WebDriver.get_products(
        driver,
        lambda elements, *, page_number: {
            "products": list(elements),
            "incomplete_items": [],
        },
        category_name="beauty",
    )

    # THEN: the category completion summary is logged after reset processing
    assert any(
        level == "INFO" and "Category beauty: reset_count=" in message
        for level, message in logger.records
    )


def test_get_products_does_not_reset_when_hard_reset_is_disabled(monkeypatch):
    # GIVEN: a multi-page category where threshold is reached but hard reset is disabled
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    logger = DummyLogger()
    driver = DummyWebDriverHarness()
    original_driver = DummySeleniumSession(
        pages=[["A", "B"], ["C", "D"]],
        page_urls=["page-1", "page-2"],
    )
    driver.driver = original_driver
    driver.logger = logger
    driver.hard_driver_reset = False
    driver.max_pages_per_session = 1
    factory = DummyDriverFactory(
        pages=[["A", "B"], ["C", "D"]],
        page_urls=["page-1", "page-2"],
    )
    driver._create_fresh_driver = factory

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver,
        lambda elements, *, page_number: {
            "products": list(elements),
            "incomplete_items": [],
        },
        category_name="beauty",
    )

    # THEN: pagination continues without any reset attempt
    assert result["products"] == ["A", "B", "C", "D"]
    assert factory.calls == 0
    assert original_driver.called.count(("quit",)) == 0
    assert not any("Driver reset triggered" in message for _, message in logger.records)


def test_reset_driver_for_next_page_raises_after_max_attempts(monkeypatch):
    # GIVEN: a reset sequence where every fresh driver creation attempt fails
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    logger = DummyLogger()
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(
        pages=[["A", "B"]],
        page_urls=["page-1"],
    )
    driver.logger = logger
    factory = DummyDriverFactory(failures_before_success=3)
    driver._create_fresh_driver = factory

    # WHEN: the driver is reset for the next page
    # THEN: the final failure is raised after max attempts
    with pytest.raises(RuntimeError, match="driver creation failed"):
        WebDriver._reset_driver_for_next_page(driver, "page-2")

    assert factory.calls == 3
    assert any(
        level == "INFO" and "WebDriver reset retry 1/2" in message
        for level, message in logger.records
    )
    assert any(
        level == "INFO" and "WebDriver reset retry 2/2" in message
        for level, message in logger.records
    )


def test_reset_driver_for_next_page_logs_quit_failure_and_continues(monkeypatch):
    # GIVEN: quitting the old driver fails but a fresh driver can still be created
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    logger = DummyLogger()
    driver = DummyWebDriverHarness()
    old_driver = DummySeleniumSession(
        pages=[["A", "B"], ["C", "D"]],
        page_urls=["page-1", "page-2"],
    )

    def _raise_on_quit():
        raise RuntimeError("quit failed")

    old_driver.quit = _raise_on_quit
    driver.driver = old_driver
    driver.logger = logger
    factory = DummyDriverFactory(
        pages=[["A", "B"], ["C", "D"]],
        page_urls=["page-1", "page-2"],
    )
    driver._create_fresh_driver = factory

    # WHEN: the driver is reset for the next page
    WebDriver._reset_driver_for_next_page(driver, "page-2")

    # THEN: quit failure is logged and reset still completes
    assert factory.calls == 1
    assert driver.driver.current_url == "page-2"
    assert any(
        level == "WARNING"
        and "Failed to quit previous WebDriver before reset" in message
        for level, message in logger.records
    )
    assert any(
        level == "INFO" and "WebDriver reset completed:" in message
        for level, message in logger.records
    )


def test_get_products_skips_reset_when_no_next_page_button(monkeypatch):
    # GIVEN: no next-page button is available while hard reset is enabled and threshold is reached
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    logger = DummyLogger()
    driver = DummyWebDriverHarness()
    original_driver = DummySeleniumSession(
        pages=[["A", "B"], ["C", "D"]],
        page_urls=["page-1", "page-2"],
        next_button_missing=True,
    )
    driver.driver = original_driver
    driver.logger = logger
    driver.hard_driver_reset = True
    driver.max_pages_per_session = 1
    factory = DummyDriverFactory(
        pages=[["A", "B"], ["C", "D"]],
        page_urls=["page-1", "page-2"],
    )
    driver._create_fresh_driver = factory

    # WHEN: the products are retrieved
    result = WebDriver.get_products(
        driver,
        lambda elements, *, page_number: {
            "products": list(elements),
            "incomplete_items": [],
        },
        category_name="beauty",
    )

    # THEN: no next URL is returned and the reset is skipped
    assert result["products"] == ["A", "B"]
    assert factory.calls == 0
    assert original_driver.called.count(("quit",)) == 0


# ============================================================
# Reading text from a product element
# ============================================================


def test_extract_text_returns_empty_for_none_element():
    # GIVEN: a None element
    driver = DummyWebDriverHarness()

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, None)

    # THEN: an empty string is returned
    assert result == ""


def test_extract_text_returns_stripped_string_passthrough():
    # GIVEN: a plain string element with surrounding whitespace
    driver = DummyWebDriverHarness()
    text = "  Milk 2L  "

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, text)

    # THEN: the string is returned stripped
    assert result == "Milk 2L"


def test_extract_text_uses_element_dot_text():
    # GIVEN: a product element with recognisable text
    driver = DummyWebDriverHarness()
    element = DummyProductElement(text="Bread 1 loaf\n$3.00\n$3.00 / 1EA")

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, element)

    # THEN: the element's text is returned verbatim
    assert result == "Bread 1 loaf\n$3.00\n$3.00 / 1EA"


def test_extract_text_shadow_root_fallback_when_text_is_empty():
    # GIVEN: a product element with no directly accessible text
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(script_result="Shadow Product 500g")
    element = DummyProductElement(text="")

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, element)

    # THEN: the product text is successfully retrieved
    assert result == "Shadow Product 500g"


def test_extract_text_falls_through_to_shadow_when_text_raises():
    # GIVEN: a product element that errors on direct text access
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(script_result="Shadow Product 500g")
    element = DummyProductElement(raise_on_text=True)

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, element)

    # THEN: the product text is successfully retrieved
    assert result == "Shadow Product 500g"


def test_extract_text_stringifies_non_string_shadow_result():
    # GIVEN: a product element whose retrieved text value is not a string
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(script_result=42)
    element = DummyProductElement(text="")

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, element)

    # THEN: a string is always returned
    assert isinstance(result, str)


def test_extract_text_propagates_timeout_error_from_shadow_root():
    # GIVEN: a product element that times out during text retrieval
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(
        script_side_effect=TimeoutError("stale element")
    )
    element = DummyProductElement(text="")

    # WHEN: text is retrieved from the element
    # THEN: a TimeoutError is raised
    with pytest.raises(TimeoutError):
        WebDriver._extract_text_from_product_element(driver, element)


def test_extract_text_propagates_timeout_error_from_element_dot_text():
    # GIVEN: a product element whose text property raises a TimeoutError
    driver = DummyWebDriverHarness()
    element = DummyProductElement(text_error=TimeoutError("stale element"))

    # WHEN: text is retrieved from the element
    # THEN: a TimeoutError is raised
    with pytest.raises(TimeoutError):
        WebDriver._extract_text_from_product_element(driver, element)


def test_extract_text_returns_empty_when_shadow_root_returns_none():
    # GIVEN: a product element whose shadow root extraction returns None
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession()  # script_result defaults to None
    element = DummyProductElement(text="")

    # WHEN: text is retrieved from the element
    result = WebDriver._extract_text_from_product_element(driver, element)

    # THEN: an empty string is returned
    assert result == ""
