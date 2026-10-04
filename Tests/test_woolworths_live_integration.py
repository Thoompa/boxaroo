"""Tests against the real Woolworths site; see `live` in pyproject.toml.

Each test covers one layer so a failure points at what broke, and the cheap ones
come first. Together they take a few minutes, dominated by the full refresh test.
"""

import json
import math

import pytest

from Code.contracts import ListSize
from Code.product_parser import ProductParser
from Code.woolworths import Woolworths
from Tests.test_helpers import DummyFileHandler

# Categories that have existed for years; the list itself drifts (promo pages come and go).
STABLE_CATEGORIES = ["fruit-veg", "dairy-eggs-fridge", "pantry", "bakery"]

# Woolworths shows 36 products per page.
PAGE_SIZE = 36

# A mid-sized category: several pages, quick enough to scrape one page of.
SAMPLE_CATEGORY = "deli"


@pytest.fixture
def woolworths(live_driver, live_logger):
    return Woolworths(
        file_handler=DummyFileHandler(),
        logger=live_logger,
        web_driver=live_driver,
        product_parser=ProductParser(logger=live_logger),
    )


@pytest.mark.live
def test_live_menu_discovery_finds_categories(woolworths):
    # WHEN the browse menu is scraped from the live site
    discovered = woolworths.category_source._get_supermarket_categories()

    # THEN the usual categories are found with browse links
    names = [item["name"] for item in discovered]
    assert len(names) >= 15, (
        f"Only {len(names)} categories discovered; the browse menu markup has "
        "probably changed (see Logs/live-test-failures/ and the printed log)"
    )
    missing = [name for name in STABLE_CATEGORIES if name not in names]
    assert not missing, f"Expected categories missing from the menu: {missing}"
    for item in discovered:
        assert item["href"].startswith(woolworths.base_url + "/shop/browse/")


@pytest.mark.live
def test_live_category_total_is_read_from_page(woolworths, live_driver):
    # WHEN a category page is loaded
    live_driver.get_page(woolworths.url + SAMPLE_CATEGORY)

    # THEN the total product count is read from the page
    total = live_driver.get_category_total_items()
    assert isinstance(total, int) and total >= 50, (
        f"Total for {SAMPLE_CATEGORY} was {total!r}; the count text may have moved, "
        "or the page had not finished loading (known issue 3)"
    )


@pytest.mark.live
def test_live_first_page_of_a_category_is_scraped_and_parsed(
    woolworths, live_driver, limit_pages
):
    # GIVEN scraping is limited to the first page
    limit_pages(live_driver, 1)

    # WHEN a category is scraped
    data = woolworths.get_category_data(SAMPLE_CATEGORY)

    # THEN a page of products comes back with names and prices
    assert data["scraped"] > 0, (
        f"Nothing scraped from {SAMPLE_CATEGORY}; get_category_data swallows errors, "
        "so check the printed log for the exception"
    )
    assert data["scraped"] <= 100, "A single page should hold at most ~36-72 tiles"
    assert data["total"] >= data["scraped"]
    priced = [row for row in data["products"] if len(row) > 1 and row[1].startswith("$")]
    assert len(priced) >= 0.9 * data["scraped"], "Most products should have a price"
    print(f"Sample product row: {data['products'][0]}")


def _assert_different_pages(first: set[str], second: set[str]) -> None:
    # Woolworths reshuffles results between loads (reloading page 1 repeats only
    # ~85% of it, and consecutive pages share ~45%), so only reject a page that
    # is essentially the same one again.
    overlap = len(first & second) / len(first)
    assert overlap < 0.9, f"Page 2 repeats {overlap:.0%} of page 1; did it advance?"


def _collect_pages(driver, pages):
    """get_products with a callback that records each page's raw tile text."""

    def record(payloads, page_number):
        pages[page_number] = set(payloads)
        return []

    return driver.get_products(record, category_name=SAMPLE_CATEGORY)


@pytest.mark.live
def test_live_pagination_advances_to_distinct_pages(
    woolworths, live_driver, limit_pages
):
    # GIVEN scraping is limited to three pages
    limit_pages(live_driver, 3)
    live_driver.get_page(woolworths.url + SAMPLE_CATEGORY)
    pages: dict[int, set[str]] = {}

    # WHEN the category is paginated
    result = _collect_pages(live_driver, pages)

    # THEN each of the three pages has products, and they are different pages
    assert [stat["page"] for stat in result["page_stats"]] == [1, 2, 3]
    assert all(stat["product_tiles"] > 0 for stat in result["page_stats"])
    assert "pageNumber=3" in live_driver.driver.current_url
    _assert_different_pages(pages[1], pages[2])


@pytest.mark.live
def test_live_pagination_confirms_the_end_of_a_category(
    woolworths, live_driver, limit_pages, capsys
):
    # GIVEN the final page of a category is loaded directly
    live_driver.get_page(woolworths.url + SAMPLE_CATEGORY)
    total = live_driver.get_category_total_items()
    assert isinstance(total, int) and 50 <= total < 10000, f"Unusable total: {total!r}"
    last_page = math.ceil(total / PAGE_SIZE)
    live_driver.get_page(f"{woolworths.url}{SAMPLE_CATEGORY}?pageNumber={last_page}")
    # (the cap only guards against a wrong total sending us down the whole category)
    limit_pages(live_driver, 3)
    pages: dict[int, set[str]] = {}

    # WHEN the category is paginated from there
    result = _collect_pages(live_driver, pages)

    # THEN pagination ends after that page, without a false end being recovered
    assert len(result["page_stats"]) == 1, (
        f"Expected the end after page {last_page} of {total} products, but "
        f"scraped {len(result['page_stats'])} pages; the total or next-button "
        "detection may be wrong"
    )
    assert "Pagination recovered" not in capsys.readouterr().out


@pytest.mark.live
def test_live_pagination_recovers_from_a_failed_advance(
    woolworths, live_driver, limit_pages, monkeypatch, capsys
):
    # GIVEN the first attempt to advance fails, as it does when the browser hangs
    limit_pages(live_driver, 2)
    original_outcome = live_driver._advance_outcome
    attempts = {"count": 0}

    def fail_once(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return "error"
        return original_outcome(*args, **kwargs)

    monkeypatch.setattr(live_driver, "_advance_outcome", fail_once)
    live_driver.get_page(woolworths.url + SAMPLE_CATEGORY)
    pages: dict[int, set[str]] = {}

    # WHEN the category is paginated
    result = _collect_pages(live_driver, pages)

    # THEN the browser is restarted on page 2 and scraping carries on
    output = capsys.readouterr().out
    assert "Pagination recovery 1/3" in output
    assert "pageNumber=2" in live_driver.driver.current_url
    assert [stat["page"] for stat in result["page_stats"]] == [1, 2]
    assert result["page_stats"][1]["product_tiles"] > 0
    _assert_different_pages(pages[1], pages[2])


@pytest.mark.live
def test_live_category_refresh_classifies_and_caches(tmp_path, woolworths):
    """Slow (counts every category, ~4 minutes): rebuilds the list-size cache."""
    cache_file = tmp_path / "woolworths-category-lists.json"
    woolworths.category_list_service.cache_path = str(cache_file)

    # Force a real refresh path: discover categories, count each category page, classify, and persist cache.
    full_list = woolworths.get_categories(
        list_size=ListSize.FULL, refresh_category_lists=True
    )
    short_list = woolworths.get_categories(
        list_size=ListSize.SHORT, refresh_category_lists=False
    )
    testing_list = woolworths.get_categories(
        list_size=ListSize.TESTING, refresh_category_lists=False
    )

    assert isinstance(full_list, list)
    assert isinstance(short_list, list)
    assert isinstance(testing_list, list)
    assert len(full_list) > 0, (
        "No categories discovered from the live site; the browse menu markup "
        "has probably changed (see Logs/live-test-failures/ and the printed log)"
    )
    assert len(testing_list) == 1

    # Logical list relationship guarantees regardless of live count drift.
    assert set(short_list).issubset(set(full_list))
    assert set(testing_list).issubset(set(short_list))

    assert cache_file.exists()
    cache_data = json.loads(cache_file.read_text(encoding="utf-8"))

    for key in [
        "testing",
        "short",
        "medium",
        "long",
        "full",
        "supermarket_categories",
        "list_product_totals",
        "category_product_totals",
    ]:
        assert key in cache_data
    assert cache_data["full"] == full_list
    assert cache_data["short"] == short_list
    assert cache_data["testing"] == testing_list
    assert len(cache_data["supermarket_categories"]) >= len(full_list)
