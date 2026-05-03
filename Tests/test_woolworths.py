import json

import pytest

from Code.contracts import ListSize
from Code.woolworths import Woolworths
from Tests.test_helpers import (
    DummyFileHandler,
    DummyLogger,
    DummyProductParser,
    DummyWebDriver,
)


@pytest.fixture
def logger():
    return DummyLogger()


@pytest.fixture
def file_handler():
    return DummyFileHandler()


@pytest.fixture
def parser():
    return DummyProductParser()


@pytest.fixture
def web_driver():
    driver = DummyWebDriver()
    driver.script_response = ""
    return driver


@pytest.fixture
def woolworths(file_handler, logger, web_driver, parser):
    return Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )


def test_cache_path_source_of_truth_is_category_list_service(woolworths, tmp_path):
    # GIVEN: a cache path set on the category list service
    cache_file = tmp_path / "woolworths-category-lists.json"
    woolworths.category_list_service.cache_path = str(cache_file)

    # WHEN: the cache path is accessed
    # THEN: the value is retrieved from the category list service
    assert woolworths.category_list_service.cache_path == str(cache_file)


# ============================================================
# Public adapter contract: wiring from Woolworths to collaborators
# ============================================================


def test_get_categories_returns_selected_list_via_public_api(
    file_handler, logger, web_driver, parser, tmp_path
):
    # GIVEN: a cache with known categories and a site that returns matching names
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
    web_driver.script_response = [
        True,
        [
            {
                "name": "fruit-veg",
                "href": "https://www.woolworths.com.au/shop/browse/fruit-veg",
            },
            {
                "name": "pantry",
                "href": "https://www.woolworths.com.au/shop/browse/pantry",
            },
        ],
    ]
    woolworths = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )
    woolworths.category_list_service.cache_path = str(cache_file)

    # WHEN: categories are retrieved via the public adapter method
    result = woolworths.get_categories(list_size=ListSize.SHORT)

    # THEN: the public API returns the expected selected list
    assert result == ["fruit-veg", "pantry"]


def test_get_categories_refreshes_lists_when_refresh_is_requested_via_public_api(
    file_handler, logger, web_driver, parser, tmp_path
):
    # GIVEN: a valid cache where selected categories match the website
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
    web_driver.script_response = [
        True,
        [
            {
                "name": "fruit-veg",
                "href": "https://www.woolworths.com.au/shop/browse/fruit-veg",
            },
            {
                "name": "pantry",
                "href": "https://www.woolworths.com.au/shop/browse/pantry",
            },
        ],
    ]
    web_driver.category_total_items_sequence = [200, 150]
    woolworths = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )
    woolworths.category_list_service.cache_path = str(cache_file)

    # WHEN: categories are retrieved via the public API with refresh requested
    result = woolworths.get_categories(
        list_size=ListSize.SHORT, refresh_category_lists=True
    )

    # THEN: category lists are refreshed instead of using the cache directly
    assert set(result) == {"fruit-veg", "pantry"}
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 2
    )


def test_get_category_data_returns_expected_shape_via_public_api(
    file_handler, logger, web_driver, parser
):
    # GIVEN: a driver configured with a known total and a single product
    web_driver.category_total_items = 3
    web_driver.products_response = {
        "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
        "incomplete_items": [],
        "page_stats": [],
    }
    woolworths = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )

    # WHEN: category data is retrieved via the public adapter method
    result = woolworths.get_category_data("fruit-veg")

    # THEN: a correctly shaped CategoryData dict is returned from the public API
    assert result["category"] == "fruit-veg"
    assert result["total"] == 3
    assert len(result["products"]) == 1
    assert result["incomplete_items"] == []
