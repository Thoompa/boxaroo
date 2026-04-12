from web_driver import WebDriver
import web_driver as web_driver_module
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


def test_get_products_payload_always_contains_required_keys():
    driver = DummyWebDriverShell(
        products_response={
            "products": [],
            "incomplete_items": [],
            "page_stats": [],
        }
    )

    result = driver.get_products(lambda x: {"products": [], "incomplete_items": []})

    assert "products" in result
    assert "incomplete_items" in result
    assert "page_stats" in result


def test_get_products_page_stats_track_incomplete_count():
    driver = DummyWebDriverShell(
        products_response={
            "products": ["A", "B"],
            "incomplete_items": [
                {"name": "A", "missing": ["price"]},
                {"name": "B", "missing": ["unit_price"]},
            ],
            "page_stats": [
                {"page": 1, "product_tiles": 2, "scraped": 2, "incomplete": 2}
            ],
        }
    )

    result = driver.get_products(
        lambda x: {
            "products": ["A", "B"],
            "incomplete_items": [{"name": "A", "missing": ["price"]}],
        }
    )

    assert result["page_stats"][0]["incomplete"] == 2
