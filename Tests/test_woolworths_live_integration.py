"""Tests against the real Woolworths site; see `live` in pyproject.toml.

Each test covers one layer so a failure points at what broke, and the cheap ones
come first. Together they take a few minutes, dominated by the full refresh test.
"""

import json

import pytest

from Code.contracts import ListSize
from Code.product_parser import ProductParser
from Code.woolworths import Woolworths
from Tests.test_helpers import DummyFileHandler

# Categories that have existed for years; the list itself drifts (promo pages come and go).
STABLE_CATEGORIES = ["fruit-veg", "dairy-eggs-fridge", "pantry", "bakery"]

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
