import json
import pytest

from Code.isupermarket import ListSize
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


# ============================================================
# Product Payload Parsing: extraction, fallback, and skip behavior
# ============================================================


def test_get_products_data_incomplete_tracking(
    file_handler, logger, web_driver, parser
):
    # GIVEN: two product responses with missing fields
    parser.queue_response(
        {
            "name": "Product One each",
            "price": "$2.00",
            "unit_price": "",
            "promotion": "",
            "missing_fields": ["unit_price"],
        }
    )
    parser.queue_response(
        {
            "name": "Product Two each",
            "price": "",
            "unit_price": "$1.00 / 1EA",
            "promotion": "",
            "missing_fields": ["price"],
        }
    )
    w = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )

    # WHEN: products data is retrieved from the inputs
    result = w._get_products_data(["input1", "input2"])

    # THEN: incomplete items are tracked alongside valid products
    assert isinstance(result, dict)
    assert len(result["products"]) == 2
    assert len(result["incomplete_items"]) == 2
    assert result["products"][0][0] == "Product One each"
    assert result["products"][0][1] == "$2.00"
    assert result["products"][1][0] == "Product Two each"
    assert result["products"][1][1] == "$1.00 / 1EA"


def test_get_products_data_uses_injected_product_parser(
    file_handler, logger, web_driver, parser
):
    # GIVEN: a default parser response configured
    parser.set_default_response(
        {
            "name": "Injected Name each",
            "price": "",
            "unit_price": "$2.50 / 1EA",
            "promotion": "",
            "missing_fields": ["price"],
        }
    )
    w = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )

    # WHEN: products data is retrieved with the injected parser
    result = w._get_products_data(["raw text from UI"])

    # THEN: the injected parser is used and results are returned
    assert parser.calls == ["raw text from UI"]
    assert result["products"] == [
        ["Injected Name each", "$2.50 / 1EA", "$2.50 / 1EA", ""]
    ]
    assert result["incomplete_items"] == [
        {"name": "Injected Name each", "missing": ["price"]}
    ]


def test_get_products_data_uses_unit_price_as_price_fallback(
    file_handler, logger, web_driver, parser
):
    # GIVEN: a product with no regular price but with unit price
    parser.set_default_response(
        {
            "name": "Some Product each",
            "price": "",
            "unit_price": "$2.50 / 1KG",
            "promotion": "",
            "missing_fields": ["price"],
        }
    )
    w = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )

    # WHEN: products data is retrieved
    result = w._get_products_data(["any text"])

    # THEN: unit price is used as fallback when price is missing
    assert len(result["products"]) == 1
    product = result["products"][0]
    # _get_products_data promotes unit_price -> price when price is absent
    assert product[1] == "$2.50 / 1KG"
    assert product[2] == "$2.50 / 1KG"


def test_get_products_data_skips_empty_payload_and_continues(
    file_handler, logger, web_driver, parser
):
    # GIVEN: an empty product followed by a valid product
    # First call returns all-empty (simulates whitespace-only input)
    parser.queue_response(
        {
            "name": "",
            "price": "",
            "unit_price": "",
            "promotion": "",
            "missing_fields": ["name", "price", "unit_price"],
        }
    )
    parser.queue_response(
        {
            "name": "Normal Product each",
            "price": "$1.00",
            "unit_price": "$1.00 / 1EA",
            "promotion": "",
            "missing_fields": [],
        }
    )
    w = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )

    # WHEN: products data is retrieved
    result = w._get_products_data(["empty", "normal"])

    # THEN: empty products are skipped and processing continues
    assert len(result["products"]) == 1
    assert result["products"][0][0] == "Normal Product each"


def test_get_products_data_handles_multiple_valid_plain_text_payloads(
    file_handler, logger, web_driver, parser
):
    # GIVEN: multiple valid product responses with various data
    parser.queue_response(
        {
            "name": "Apple each",
            "price": "$2.00",
            "unit_price": "$2.00 / 1EA",
            "promotion": "",
            "missing_fields": [],
        }
    )
    parser.queue_response(
        {
            "name": "Bread each",
            "price": "$3.50",
            "unit_price": "$1.75 / 1EA",
            "promotion": "2 for $3.50",
            "missing_fields": [],
        }
    )
    w = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )

    # WHEN: products data is retrieved from multiple payloads
    result = w._get_products_data(["payload1", "payload2"])

    # THEN: all products are extracted with correct data
    assert len(result["products"]) == 2
    assert result["products"][0][0] == "Apple each"
    assert result["products"][0][1] == "$2.00"
    assert result["products"][1][0] == "Bread each"
    assert result["products"][1][3] == "2 for $3.50"


def test_get_products_data_skips_product_when_all_fields_are_empty(
    file_handler, logger, web_driver, parser
):
    # GIVEN: a product with all empty fields
    # First call returns all-empty -- should be skipped by _get_products_data
    parser.queue_response(
        {
            "name": "",
            "price": "",
            "unit_price": "",
            "promotion": "",
            "missing_fields": ["name", "price", "unit_price"],
        }
    )
    parser.queue_response(
        {
            "name": "Normal Product",
            "price": "$1.00",
            "unit_price": "$1.00 / 1EA",
            "promotion": "",
            "missing_fields": [],
        }
    )
    w = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )

    # WHEN: products data is retrieved
    result = w._get_products_data(["empty", "normal"])

    # THEN: empty product is skipped and debug log is created
    # Assert the empty product was skipped
    assert len(result["products"]) == 1
    assert result["products"][0][0] == "Normal Product"

    # Assert a skip debug message was logged
    debug_records = [msg for level, msg in logger.records if level == "DEBUG"]
    skip_logs = [msg for msg in debug_records if "Skipped empty product" in msg]
    assert len(skip_logs) > 0


# ============================================================
# Category List Refreshing: size classification and zero filtering
# ============================================================


def test_refresh_category_lists_from_site_classifies_by_count(woolworths, web_driver):
    # GIVEN: categories with different product counts
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
        {"name": "liquor", "href": "https://www.woolworths.com.au/shop/browse/liquor"},
    ]
    web_driver.category_total_items_sequence = [220, 1200, 1700, 5000, 12000, 80]

    # WHEN: category lists are refreshed from the site
    out = woolworths._refresh_category_lists_from_site(categories)

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


def test_refresh_category_lists_from_site_skips_zero_count_categories(
    woolworths, web_driver
):
    # GIVEN: categories where one has zero items
    categories = [
        {
            "name": "front-of-store",
            "href": "https://www.woolworths.com.au/shop/browse/front-of-store",
        },
        {
            "name": "fruit-veg",
            "href": "https://www.woolworths.com.au/shop/browse/fruit-veg",
        },
        {"name": "liquor", "href": "https://www.woolworths.com.au/shop/browse/liquor"},
    ]
    web_driver.category_total_items_sequence = [0, 220, 80]

    # WHEN: category lists are refreshed from the site
    out = woolworths._refresh_category_lists_from_site(categories)

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
    woolworths, web_driver
):
    # GIVEN: categories where all have zero items
    categories = [
        {
            "name": "front-of-store",
            "href": "https://www.woolworths.com.au/shop/browse/front-of-store",
        },
    ]
    web_driver.category_total_items_sequence = [0]

    # WHEN: category lists are refreshed from the site
    out = woolworths._refresh_category_lists_from_site(categories)

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


# ============================================================
# Category Selection and Cache Fallback: site/cache reconciliation
# ============================================================


def test_get_all_categories_uses_cache_when_selected_categories_match_site(
    woolworths, web_driver, tmp_path
):
    # GIVEN: a cache with matching categories and the site returns the same categories
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry", "pet"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    woolworths.category_list_service.cache_path = str(cache_file)
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
    web_driver.category_total_items_sequence = [999]

    # WHEN: all categories are retrieved
    out = woolworths._get_all_categories(list_size=ListSize.SHORT)

    # THEN: cached categories are returned without refreshing from site
    assert out == ["fruit-veg", "pantry"]
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 0
    )


def test_get_all_categories_refreshes_when_selected_category_missing(
    woolworths, web_driver, tmp_path
):
    # GIVEN: a cache with a category that is no longer on the site
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    woolworths.category_list_service.cache_path = str(cache_file)
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

    # WHEN: all categories are retrieved
    out = woolworths._get_all_categories(list_size=ListSize.SHORT)

    # THEN: cache is refreshed because a selected category is missing
    assert out == ["baby", "fruit-veg"]
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 2
    )


def test_get_all_categories_refreshes_when_testing_category_has_zero_items(
    woolworths, web_driver, tmp_path
):
    # GIVEN: a cache where the testing category now has zero items
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["front-of-store", "fruit-veg"],
        "testing": ["front-of-store"],
        "short": ["front-of-store", "fruit-veg"],
        "full": ["front-of-store", "fruit-veg"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    woolworths.category_list_service.cache_path = str(cache_file)
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
    # 1) stale TESTING-category validation (front-of-store) -> 0
    # 2) refresh pass front-of-store -> 0
    # 3) refresh pass fruit-veg -> 220
    web_driver.category_total_items_sequence = [0, 0, 220]

    # WHEN: all categories are retrieved for testing size
    out = woolworths._get_all_categories(list_size=ListSize.TESTING)

    # THEN: cache is refreshed because testing category has zero items
    assert out == ["fruit-veg"]
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 3
    )


def test_get_all_categories_falls_back_to_cache_on_exception(woolworths, tmp_path):
    # GIVEN: a valid cache and a method that raises an exception
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
    woolworths.category_list_service.cache_path = str(cache_file)

    def raise_error():
        raise Exception("boom")

    woolworths._get_supermarket_categories = raise_error

    # WHEN: all categories are retrieved but site access fails
    out = woolworths._get_all_categories(ListSize.TESTING)

    # THEN: cache contents are returned as fallback
    assert out == ["fruit-veg"]


def test_get_supermarket_categories_returns_drawer_categories(woolworths, web_driver):
    # GIVEN: web driver that opens the navigation menu and returns categories
    # First execute_script call opens menu (boolean), second returns drawer categories.
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

    # WHEN: supermarket categories are retrieved
    categories = woolworths._get_supermarket_categories()
    names = [c["name"] for c in categories]

    # THEN: drawer categories are returned from the web driver
    assert names == ["fruit-veg", "pantry", "drinks"]


# ============================================================
# Category Selection and Cache Fallback: fallback and path ownership
# ============================================================


def test_get_all_categories_falls_back_to_empty_when_no_cache_and_exception(
    woolworths, tmp_path
):
    # GIVEN: no cache file and a method that raises an exception
    woolworths.category_list_service.cache_path = str(tmp_path / "nope.json")

    def raise_network_error():
        raise Exception("network down")

    woolworths._get_supermarket_categories = raise_network_error

    # WHEN: all categories are retrieved with no cache and site access fails
    out = woolworths._get_all_categories(ListSize.SHORT)

    # THEN: empty list is returned as final fallback
    assert out == []


def test_cache_path_source_of_truth_is_category_list_service(woolworths, tmp_path):
    # GIVEN: a cache path set on the category list service
    cache_file = tmp_path / "woolworths-category-lists.json"
    woolworths.category_list_service.cache_path = str(cache_file)

    # WHEN: the cache path is accessed
    # THEN: the value is retrieved from the category list service
    assert woolworths.category_list_service.cache_path == str(cache_file)
    assert not hasattr(woolworths, "category_lists_cache_path")


# ============================================================
# Product and Category Payload Shapes: boundary contracts
# ============================================================


def test_get_category_data_returns_correct_shape_on_success(woolworths, web_driver):
    # GIVEN: web driver with category total and products data
    web_driver.category_total_items = 5
    web_driver.products_response = {
        "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
        "incomplete_items": [],
        "page_stats": [{"page": 1, "product_tiles": 1, "scraped": 1, "incomplete": 0}],
    }

    # WHEN: category data is retrieved
    result = woolworths._get_category_data("fruit-veg")

    # THEN: category data is returned with correct structure
    assert result["category"] == "fruit-veg"
    assert result["total"] == 5
    assert result["scraped"] == 1
    assert result["incomplete"] == 0
    assert len(result["products"]) == 1
    assert result["incomplete_items"] == []


def test_get_category_data_returns_correct_shape_on_exception(woolworths, web_driver):
    # GIVEN: web driver that raises an exception
    def boom(url):
        raise RuntimeError("Driver exploded")

    web_driver.get_page = boom

    # WHEN: category data is retrieved
    result = woolworths._get_category_data("fruit-veg")

    # THEN: error dict structure is returned with empty data
    assert result["category"] == "fruit-veg"
    assert result["total"] == 0
    assert result["products"] == []
    assert result["incomplete_items"] == []
    assert result["scraped"] == 0
    assert result["incomplete"] == 0


def test_get_category_data_uses_scraped_count_when_total_is_none(
    woolworths, web_driver
):
    # GIVEN: web driver that returns None for total but has product data
    web_driver.category_total_items = None
    web_driver.products_response = {
        "products": [
            ["Apple each", "$1.00", "$1.00 / 1EA", ""],
            ["Bread each", "$2.00", "", ""],
        ],
        "incomplete_items": [],
        "page_stats": [],
    }

    # WHEN: category data is retrieved
    result = woolworths._get_category_data("bakery")

    # THEN: scraped count is used as fallback when total is None
    # When driver returns None for total, fall back to scraped count
    assert result["total"] == 2
    assert result["scraped"] == 2


def test_get_category_data_deduplicates_products_and_incomplete_items(
    woolworths, web_driver
):
    web_driver.category_total_items = 5
    web_driver.products_response = {
        "products": [
            ["Apple each", "$1.00", "$1.00 / 1EA", ""],
            ["Apple each", "$1.00", "$1.00 / 1EA", ""],
            ["Bread each", "$2.00", "$2.00 / 1EA", ""],
        ],
        "incomplete_items": [
            {"name": "Apple each", "missing": ["unit_price"]},
            {"name": "Apple each", "missing": ["unit_price"]},
        ],
        "page_stats": [{"page": 1, "product_tiles": 3, "scraped": 3, "incomplete": 2}],
    }

    result = woolworths._get_category_data("fruit-veg")

    assert result["products"] == [
        ["Apple each", "$1.00", "$1.00 / 1EA", ""],
        ["Bread each", "$2.00", "$2.00 / 1EA", ""],
    ]
    assert result["incomplete_items"] == [
        {"name": "Apple each", "missing": ["unit_price"]}
    ]
    assert result["scraped"] == 2
    assert result["incomplete"] == 1


# ============================================================
# get_data Orchestration: per-category persistence and resilience
# ============================================================


def test_get_data_stores_products_for_each_category_and_accumulates_count(
    file_handler, logger, web_driver, parser
):
    # GIVEN: multiple categories with product data
    woolworths = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )

    # Mock _get_all_categories to return 3 categories
    woolworths._get_all_categories = lambda *args, **kwargs: [
        "fruit-veg",
        "pantry",
        "bakery",
    ]

    # Mock category-level results directly so this test isolates get_data loop behavior.
    category_data = {
        "fruit-veg": {
            "category": "fruit-veg",
            "total": 2,
            "products": [
                ["Apple each", "$1.00", "$1.00 / 1EA", ""],
                ["Orange each", "$0.80", "$0.80 / 1EA", ""],
            ],
            "incomplete_items": [],
            "scraped": 2,
            "incomplete": 0,
        },
        "pantry": {
            "category": "pantry",
            "total": 1,
            "products": [["Rice 1kg", "$2.50", "$2.50 / 1KG", ""]],
            "incomplete_items": [],
            "scraped": 1,
            "incomplete": 0,
        },
        "bakery": {
            "category": "bakery",
            "total": 3,
            "products": [
                ["Bread each", "$3.50", "$3.50 / 1EA", ""],
                ["Croissant each", "$2.00", "$2.00 / 1EA", ""],
                ["Bagel each", "$1.50", "$1.50 / 1EA", ""],
            ],
            "incomplete_items": [],
            "scraped": 3,
            "incomplete": 0,
        },
    }

    woolworths._get_category_data = lambda category: category_data[category]

    # WHEN: data is retrieved for all categories
    woolworths.get_data(list_size=ListSize.TESTING)

    # THEN: products are stored per category and count is accumulated
    # Assert store_data was called 3 times (once per category)
    assert len(file_handler.saved) == 3

    # Assert each saved batch has the correct products
    assert len(file_handler.saved[0]) == 2  # fruit-veg
    assert file_handler.saved[0][0][0] == "Apple each"
    assert file_handler.saved[0][1][0] == "Orange each"

    assert len(file_handler.saved[1]) == 1  # pantry
    assert file_handler.saved[1][0][0] == "Rice 1kg"

    assert len(file_handler.saved[2]) == 3  # bakery
    assert file_handler.saved[2][0][0] == "Bread each"
    assert file_handler.saved[2][2][0] == "Bagel each"

    # Assert final log message shows correct total (2 + 1 + 3 = 6)
    log_records = logger.records
    final_log = [msg for level, msg in log_records if "Successfully scraped" in msg]
    assert len(final_log) > 0
    assert "6 products" in final_log[0]

    start_log = [
        msg
        for level, msg in log_records
        if "Scraping" in msg and "Woolworths categories" in msg
    ]
    assert len(start_log) > 0
    assert "Scraping Woolworths categories" in start_log[0]


def test_get_data_continues_on_category_exception(
    file_handler, logger, web_driver, parser
):
    # GIVEN: multiple categories where one will fail
    woolworths = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )

    woolworths._get_all_categories = lambda *args, **kwargs: [
        "fruit-veg",
        "pantry",
        "bakery",
    ]

    # Mock _get_category_data to return error dict for pantry but succeed on others
    call_count = {"n": 0}

    def failing_get_category_data(category_url: str):
        call_count["n"] += 1
        # Pantry returns empty/error dict (as if exception occurred)
        if "pantry" in category_url:
            return {
                "category": category_url,
                "total": 0,
                "products": [],
                "incomplete_items": [],
                "scraped": 0,
                "incomplete": 0,
            }

        # Return successful data for fruit-veg and bakery
        if "fruit-veg" in category_url:
            return {
                "category": category_url,
                "total": 1,
                "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
                "incomplete_items": [],
                "scraped": 1,
                "incomplete": 0,
            }
        else:  # bakery
            return {
                "category": category_url,
                "total": 1,
                "products": [["Bread each", "$3.50", "$3.50 / 1EA", ""]],
                "incomplete_items": [],
                "scraped": 1,
                "incomplete": 0,
            }

    woolworths._get_category_data = failing_get_category_data

    # WHEN: data is retrieved for all categories
    woolworths.get_data(list_size=ListSize.TESTING)

    # THEN: processing continues and all categories are processed
    # Assert that store_data was called 3 times (once per category)
    # For pantry, it's called with [] due to the error dict
    assert len(file_handler.saved) == 3
    assert call_count["n"] == 3

    # fruit-veg: 1 product
    assert len(file_handler.saved[0]) == 1
    assert file_handler.saved[0][0][0] == "Apple each"

    # pantry: empty (from error)
    assert len(file_handler.saved[1]) == 0

    # bakery: 1 product
    assert len(file_handler.saved[2]) == 1
    assert file_handler.saved[2][0][0] == "Bread each"

    # Final log should show only 2 products (apple + bread, not pantry's 0)
    log_records = logger.records
    final_log = [msg for level, msg in log_records if "Successfully scraped" in msg]
    assert len(final_log) > 0
    assert "2 products" in final_log[0]
