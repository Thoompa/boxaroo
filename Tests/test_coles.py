import json

from Code.contracts import ListSize
from Code.coles import Coles
from Tests.test_helpers import (
    DummyFileHandler,
    DummyLogger,
    DummyProductParser,
    DummyWebDriver,
)


def test_cache_path_source_of_truth_is_category_list_service():
    # GIVEN: a Coles adapter with a category list service cache path
    coles = Coles(
        file_handler=DummyFileHandler(),
        logger=DummyLogger(),
        web_driver=DummyWebDriver(),
        product_parser=DummyProductParser(),
    )

    # WHEN: the cache path is updated on the category list service
    coles.category_list_service.cache_path = "/tmp/coles-category-lists.json"

    # THEN: the adapter reads the cache path from the category list service
    assert coles.category_list_service.cache_path == "/tmp/coles-category-lists.json"


def test_get_categories_returns_selected_list_via_public_api(tmp_path):
    # GIVEN: a cache with known categories and a site that returns matching names
    cache_file = tmp_path / "coles-category-lists.json"
    cache_data = {
        "supermarket_categories": ["deli", "pantry"],
        "testing": ["deli"],
        "short": ["deli", "pantry"],
        "full": ["deli", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
    web_driver = DummyWebDriver()
    web_driver.script_response = [
        True,
        [
            {
                "name": "deli",
                "href": "https://www.coles.com.au/browse/deli",
            },
            {
                "name": "pantry",
                "href": "https://www.coles.com.au/browse/pantry",
            },
        ],
    ]
    coles = Coles(
        file_handler=DummyFileHandler(),
        logger=DummyLogger(),
        web_driver=web_driver,
        product_parser=DummyProductParser(),
    )
    coles.category_list_service.cache_path = str(cache_file)

    # WHEN: categories are retrieved via the public adapter method
    result = coles.get_categories(list_size=ListSize.SHORT)

    # THEN: the public API returns the expected selected list
    assert result == ["deli", "pantry"]


def test_get_category_data_returns_expected_shape_via_public_api():
    # GIVEN: a driver configured with a known total and a single product
    web_driver = DummyWebDriver()
    web_driver.category_total_items = 3
    web_driver.products_response = {
        "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
        "incomplete_items": [],
        "page_stats": [],
    }
    coles = Coles(
        file_handler=DummyFileHandler(),
        logger=DummyLogger(),
        web_driver=web_driver,
        product_parser=DummyProductParser(),
    )

    # WHEN: category data is retrieved via the public adapter method
    result = coles.get_category_data("deli")

    # THEN: a correctly shaped CategoryData dict is returned from the public API
    assert result["category"] == "deli"
    assert result["total"] == 3
    assert len(result["products"]) == 1
    assert result["incomplete_items"] == []
