import json
from unittest.mock import patch

from Code.contracts import ListSize
from Tests.test_helpers import (
    DummyLogger,
    DummyWebDriver,
    make_woolworths_category_source,
)


def test_get_categories_uses_cache_when_selected_categories_match_site(tmp_path):
    # GIVEN: matching selected cache categories and matching website categories
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry", "pet"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    source = make_woolworths_category_source(
        cache_path=str(cache_file), logger=logger, web_driver=web_driver
    )
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
            {
                "name": "baby",
                "href": "https://www.woolworths.com.au/shop/browse/baby",
            },
        ],
    ]

    # WHEN: category names are retrieved
    result = source.get_categories(list_size=ListSize.SHORT)

    # THEN: cached selected categories are returned without total-count refresh checks
    assert result == ["fruit-veg", "pantry"]
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 0
    )


def test_get_categories_refreshes_when_selected_category_missing(tmp_path):
    # GIVEN: selected cache categories where one category no longer exists on the website
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    source = make_woolworths_category_source(
        cache_path=str(cache_file), logger=logger, web_driver=web_driver
    )
    web_driver.script_response = [
        True,
        [
            {
                "name": "fruit-veg",
                "href": "https://www.woolworths.com.au/shop/browse/fruit-veg",
            },
            {
                "name": "baby",
                "href": "https://www.woolworths.com.au/shop/browse/baby",
            },
        ],
    ]
    web_driver.category_total_items_sequence = [220, 80]

    # WHEN: category names are retrieved
    result = source.get_categories(list_size=ListSize.SHORT)

    # THEN: category lists are refreshed and a new selected list is returned
    assert result == ["baby", "fruit-veg"]
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 2
    )


def test_get_categories_falls_back_to_cache_on_discovery_exception(tmp_path):
    # GIVEN: a valid cache and a source where website category discovery fails
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    source = make_woolworths_category_source(
        cache_path=str(cache_file), logger=logger, web_driver=web_driver
    )

    def boom() -> list[dict[str, str]]:
        raise RuntimeError("network down")

    source.get_supermarket_categories = boom

    # WHEN: category names are retrieved after website category discovery has failed
    result = source.get_categories(list_size=ListSize.TESTING)

    # THEN: cached list selection is returned as fallback
    assert result == ["fruit-veg"]


def test_get_categories_preserves_existing_cache_when_discovery_returns_empty(
    tmp_path,
):
    # GIVEN: a valid cache and discovery that exhausts retries (including retry loop) with no categories found
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
    source = make_woolworths_category_source(
        cache_path=str(cache_file), logger=logger, web_driver=web_driver
    )
    # Provide responses for 2 discovery attempts: (open_menu + 6 × extract_menu) × 2
    web_driver.script_response = [
        True,
        [],
        [],
        [],
        [],
        [],
        [],
        True,
        [],
        [],
        [],
        [],
        [],
        [],
    ]

    # WHEN: categories are retrieved while both discovery attempts yield no categories after all retries
    result = source.get_categories(list_size=ListSize.SHORT)

    # THEN: the cached list is returned and the existing cache contents are preserved
    assert result == ["fruit-veg", "pantry"]
    persisted_cache = json.loads(cache_file.read_text(encoding="utf-8"))
    assert persisted_cache["short"] == ["fruit-veg", "pantry"]
    assert persisted_cache["supermarket_categories"] == ["fruit-veg", "pantry"]


def test_get_supermarket_categories_returns_empty_when_script_returns_non_list_after_all_retries(
    tmp_path,
):
    # GIVEN: a driver that returns a non-list for every script execution
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    web_driver.script_response = ""  # non-list; every execute_script call returns this
    source = make_woolworths_category_source(
        cache_path=str(tmp_path / "cache.json"), logger=logger, web_driver=web_driver
    )

    # WHEN: supermarket categories are retrieved while all retries yield a non-list
    with patch("Code.woolworths_category_source.time.sleep"):
        result = source.get_supermarket_categories()

    # THEN: empty list is returned
    assert result == []


def test_get_supermarket_categories_filters_out_malformed_dict_items(tmp_path):
    # GIVEN: a driver that returns a mix of valid and malformed category dict items
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    web_driver.script_response = [
        True,  # open_menu_script response
        [
            {
                "name": "fruit-veg",
                "href": "https://www.woolworths.com.au/shop/browse/fruit-veg",
            },  # valid
            {
                "href": "https://www.woolworths.com.au/shop/browse/pantry"
            },  # missing name
            {"name": "drinks"},  # missing href
            {
                "name": "",
                "href": "https://www.woolworths.com.au/shop/browse/empty",
            },  # empty name
            "not-a-dict",  # non-dict item
        ],
    ]
    source = make_woolworths_category_source(
        cache_path=str(tmp_path / "cache.json"), logger=logger, web_driver=web_driver
    )

    # WHEN: supermarket categories are retrieved
    result = source.get_supermarket_categories()

    # THEN: only the valid item is returned; malformed items are filtered out
    assert result == [
        {
            "name": "fruit-veg",
            "href": "https://www.woolworths.com.au/shop/browse/fruit-veg",
        }
    ]


def test_get_supermarket_categories_expands_relative_hrefs_using_base_url(tmp_path):
    # GIVEN: a driver that returns relative href values and a non-production base URL
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    web_driver.script_response = [
        True,
        [
            {"name": "fruit-veg", "href": "/shop/browse/fruit-veg"},
            {"name": "pantry", "href": "/shop/browse/pantry"},
        ],
    ]
    source = make_woolworths_category_source(
        cache_path=str(tmp_path / "cache.json"),
        logger=logger,
        web_driver=web_driver,
        base_url="https://staging.example.com",
        browse_url="https://staging.example.com/shop/browse/",
    )

    # WHEN: supermarket categories are retrieved
    result = source.get_supermarket_categories()

    # THEN: relative hrefs are expanded using the injected base_url, not a hardcoded host
    assert result == [
        {
            "name": "fruit-veg",
            "href": "https://staging.example.com/shop/browse/fruit-veg",
        },
        {
            "name": "pantry",
            "href": "https://staging.example.com/shop/browse/pantry",
        },
    ]


def test_get_categories_forces_refresh_when_refresh_flag_is_true(tmp_path):
    # GIVEN: a valid cache where selected categories match the website
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
    source = make_woolworths_category_source(
        cache_path=str(cache_file), logger=logger, web_driver=web_driver
    )
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

    # WHEN: categories are retrieved with refresh_category_lists forced to True
    result = source.get_categories(
        list_size=ListSize.SHORT, refresh_category_lists=True
    )

    # THEN: categories are refreshed from the site even though the cache was valid
    assert set(result) == {"fruit-veg", "pantry"}
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 2
    )


def test_get_categories_refreshes_when_testing_size_category_has_zero_products(
    tmp_path,
):
    # GIVEN: a valid cache where the testing-size category has zero items on the site
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["front-of-store", "fruit-veg"],
        "testing": ["front-of-store"],
        "short": ["front-of-store", "fruit-veg"],
        "full": ["front-of-store", "fruit-veg"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
    source = make_woolworths_category_source(
        cache_path=str(cache_file), logger=logger, web_driver=web_driver
    )
    web_driver.script_response = [
        True,
        [
            {
                "name": "front-of-store",
                "href": "https://www.woolworths.com.au/shop/browse/front-of-store",
            },
            {
                "name": "fruit-veg",
                "href": "https://www.woolworths.com.au/shop/browse/fruit-veg",
            },
        ],
    ]
    # 1) testing-size validity check for front-of-store → 0 (triggers refresh)
    # 2) refresh: front-of-store → 0 (excluded)
    # 3) refresh: fruit-veg → 220
    web_driver.category_total_items_sequence = [0, 0, 220]

    # WHEN: categories are retrieved for testing size
    result = source.get_categories(list_size=ListSize.TESTING)

    # THEN: cache is refreshed because the testing category had zero products
    assert result == ["fruit-veg"]
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 3
    )


# ============================================================
# Migrated from test_woolworths.py: refresh_category_lists_from_site
# ============================================================


def test_refresh_category_lists_from_site_classifies_by_count(tmp_path):
    # GIVEN: categories with different product counts
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    source = make_woolworths_category_source(
        cache_path=str(tmp_path / "cache.json"), logger=logger, web_driver=web_driver
    )
    categories = [
        {
            "name": "fruit-veg",
            "href": "https://www.woolworths.com.au/shop/browse/fruit-veg",
        },
        {
            "name": "pantry",
            "href": "https://www.woolworths.com.au/shop/browse/pantry",
        },
        {
            "name": "dairy-eggs-fridge",
            "href": "https://www.woolworths.com.au/shop/browse/dairy-eggs-fridge",
        },
        {
            "name": "home-lifestyle",
            "href": "https://www.woolworths.com.au/shop/browse/home-lifestyle",
        },
        {
            "name": "electronics",
            "href": "https://www.woolworths.com.au/shop/browse/electronics",
        },
        {
            "name": "liquor",
            "href": "https://www.woolworths.com.au/shop/browse/liquor",
        },
    ]
    web_driver.category_total_items_sequence = [220, 1200, 1700, 5000, 12000, 80]

    # WHEN: category lists are refreshed from the site
    out = source.refresh_category_lists_from_site(categories)

    # THEN: categories are classified by size based on product count
    assert out["testing"] == ["liquor"]
    assert out["short"] == ["fruit-veg", "liquor"]
    assert out["medium"] == ["dairy-eggs-fridge", "fruit-veg", "liquor", "pantry"]
    assert out["long"] == [
        "dairy-eggs-fridge",
        "fruit-veg",
        "home-lifestyle",
        "liquor",
        "pantry",
    ]
    assert out["full"] == [
        "dairy-eggs-fridge",
        "electronics",
        "fruit-veg",
        "home-lifestyle",
        "liquor",
        "pantry",
    ]
    assert len(out["short"]) < len(out["medium"]) < len(out["long"]) < len(out["full"])
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 6
    )


def test_refresh_category_lists_from_site_skips_zero_count_categories(tmp_path):
    # GIVEN: categories where one has zero items
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    source = make_woolworths_category_source(
        cache_path=str(tmp_path / "cache.json"), logger=logger, web_driver=web_driver
    )
    categories = [
        {
            "name": "front-of-store",
            "href": "https://www.woolworths.com.au/shop/browse/front-of-store",
        },
        {
            "name": "fruit-veg",
            "href": "https://www.woolworths.com.au/shop/browse/fruit-veg",
        },
        {
            "name": "liquor",
            "href": "https://www.woolworths.com.au/shop/browse/liquor",
        },
    ]
    web_driver.category_total_items_sequence = [0, 220, 80]

    # WHEN: category lists are refreshed from the site
    out = source.refresh_category_lists_from_site(categories)

    # THEN: categories with zero items are excluded from all lists
    assert out["testing"] == ["liquor"]
    assert out["short"] == ["fruit-veg", "liquor"]
    assert out["medium"] == ["fruit-veg", "liquor"]
    assert out["long"] == ["fruit-veg", "liquor"]
    assert out["full"] == ["fruit-veg", "liquor"]
    assert "front-of-store" not in out["testing"]
    assert "front-of-store" not in out["short"]
    assert "front-of-store" not in out["full"]


def test_refresh_category_lists_returns_empty_structure_when_all_categories_are_zero(
    tmp_path,
):
    # GIVEN: categories where all have zero items
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    source = make_woolworths_category_source(
        cache_path=str(tmp_path / "cache.json"), logger=logger, web_driver=web_driver
    )
    categories = [
        {
            "name": "front-of-store",
            "href": "https://www.woolworths.com.au/shop/browse/front-of-store",
        },
    ]
    web_driver.category_total_items_sequence = [0]

    # WHEN: category lists are refreshed from the site
    out = source.refresh_category_lists_from_site(categories)

    # THEN: empty structure is returned with zero counts
    assert out["testing"] == []
    assert out["short"] == []
    assert out["medium"] == []
    assert out["long"] == []
    assert out["full"] == []
    assert out["list_product_totals"] == {
        "testing": 0,
        "short": 0,
        "medium": 0,
        "long": 0,
        "full": 0,
    }
    assert out["category_product_totals"] == {}


def test_get_supermarket_categories_returns_drawer_categories(tmp_path):
    # GIVEN: a driver that opens the navigation menu and returns categories
    logger = DummyLogger()
    web_driver = DummyWebDriver()
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
            {
                "name": "drinks",
                "href": "https://www.woolworths.com.au/shop/browse/drinks",
            },
        ],
    ]
    source = make_woolworths_category_source(
        cache_path=str(tmp_path / "cache.json"), logger=logger, web_driver=web_driver
    )

    # WHEN: supermarket categories are retrieved
    categories = source.get_supermarket_categories()
    names = [c["name"] for c in categories]

    # THEN: drawer categories are returned from the web driver
    assert names == ["fruit-veg", "pantry", "drinks"]


def test_get_categories_falls_back_to_empty_when_no_cache_and_exception(tmp_path):
    # GIVEN: no cache file and a source where website category discovery fails
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    source = make_woolworths_category_source(
        cache_path=str(tmp_path / "nope.json"), logger=logger, web_driver=web_driver
    )

    def raise_network_error():
        raise Exception("network down")

    source.get_supermarket_categories = raise_network_error

    # WHEN: categories are retrieved with no cache and site access fails
    out = source.get_categories(ListSize.SHORT)

    # THEN: empty list is returned as final fallback
    assert out == []
