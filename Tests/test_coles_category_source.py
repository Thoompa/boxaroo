import json

from Code.contracts import ListSize
from Tests.test_helpers import (
    DummyLogger,
    DummyWebDriver,
    make_coles_category_source,
)


def test_get_categories_uses_cache_when_selected_categories_match_site(tmp_path):
    # GIVEN: matching selected cache categories and matching website categories
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    cache_file = tmp_path / "coles-category-lists.json"
    cache_data = {
        "supermarket_categories": ["deli", "pantry", "pet"],
        "testing": ["deli"],
        "short": ["deli", "pantry"],
        "full": ["deli", "pantry", "pet"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    source = make_coles_category_source(
        cache_path=str(cache_file), logger=logger, web_driver=web_driver
    )
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
            {
                "name": "pet",
                "href": "https://www.coles.com.au/browse/pet",
            },
        ],
    ]

    # WHEN: category names are retrieved
    result = source.get_categories(list_size=ListSize.SHORT)

    # THEN: cached selected categories are returned without total-count refresh checks
    assert result == ["deli", "pantry"]
