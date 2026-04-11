import json
import pytest

from isupermarket import ListSize
from woolworths import Woolworths
from tests.test_helpers import (
    DummyElement,
    DummyFileHandler,
    DummyLogger,
    DummyWebDriver,
)


@pytest.fixture
def logger():
    return DummyLogger()


@pytest.fixture
def file_handler():
    return DummyFileHandler()


@pytest.fixture
def web_driver():
    driver = DummyWebDriver()
    driver.script_response = ""
    return driver


@pytest.fixture
def woolworths(file_handler, logger, web_driver):
    return Woolworths(file_handler=file_handler, logger=logger, web_driver=web_driver)


def test_parse_product_data_full(woolworths):
    text = """$1.20
$1.20 / 1EA
2 FOR $2.00 - $1.00/1EA
Avocado Shepard each
Add to cart
Save to list..."""

    parsed = woolworths._parse_product_data(text)

    assert parsed == [
        "Avocado Shepard each",
        "$1.20",
        "$1.20 / 1EA",
        "2 FOR $2.00 - $1.00/1EA",
    ]


def test_parse_product_data_missing_price_unit(woolworths):
    text = """Avocado Shepard each
Add to cart
"""

    parsed = woolworths._parse_product_data(text)

    assert parsed[0] == "Avocado Shepard each"
    assert parsed[1] == ""
    assert parsed[2] == ""


def test_parse_product_data_non_string(woolworths):
    parsed = woolworths._parse_product_data(None)

    assert parsed == ["", "", "", ""]


def test_get_product_string_from_element_with_shadow_root(woolworths):
    # Simulate a layout where element text is empty, but JavaScript from shadow root returns data
    element = DummyElement("")
    woolworths.driver.script_response = "$0.50\n$0.50 / 1EA\nTest Product each\n"

    out = woolworths._get_product_string_from_element(element)

    assert "Test Product each" in out


def test_get_products_data_incomplete_tracking(woolworths):
    product_inputs = ["$2.00\nProduct One each\n", "Product Two each\n$1.00 / 1EA\n"]

    # Force _get_product_string_from_element to return our test text per element
    def fake_get_product_string(element):
        return element

    woolworths._get_product_string_from_element = fake_get_product_string

    fake_elements = product_inputs
    result = woolworths._get_products_data(fake_elements)

    assert isinstance(result, dict)
    assert len(result["products"]) == 2
    assert len(result["incomplete_items"]) == 2

    assert result["products"][0][0] == "Product One each"
    assert result["products"][0][1] == "$2.00"
    assert result["products"][1][0] == "Product Two each"
    assert result["products"][1][1] == "$1.00 / 1EA" or result["products"][1][1] == ""


def test_refresh_category_lists_from_site_classifies_by_count(woolworths, web_driver):
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

    out = woolworths._refresh_category_lists_from_site(categories)

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

    out = woolworths._refresh_category_lists_from_site(categories)

    assert out["testing"] == ["liquor"]
    assert out["short"] == ["fruit-veg", "liquor"]
    assert out["medium"] == ["fruit-veg", "liquor"]
    assert out["long"] == ["fruit-veg", "liquor"]
    assert out["full"] == ["fruit-veg", "liquor"]
    assert "front-of-store" not in out["testing"]
    assert "front-of-store" not in out["short"]
    assert "front-of-store" not in out["full"]


def test_get_all_categories_uses_cache_when_selected_categories_match_site(
    woolworths, web_driver, tmp_path
):
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry", "pet"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    woolworths.category_lists_cache_path = str(cache_file)
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

    out = woolworths._get_all_categories(list_size=ListSize.SHORT)

    assert out == ["fruit-veg", "pantry"]
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 0
    )


def test_get_all_categories_refreshes_when_selected_category_missing(
    woolworths, web_driver, tmp_path
):
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    woolworths.category_lists_cache_path = str(cache_file)
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

    out = woolworths._get_all_categories(list_size=ListSize.SHORT)

    assert out == ["baby", "fruit-veg"]
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 2
    )


def test_get_all_categories_refreshes_when_testing_category_has_zero_items(
    woolworths, web_driver, tmp_path
):
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["front-of-store", "fruit-veg"],
        "testing": ["front-of-store"],
        "short": ["front-of-store", "fruit-veg"],
        "full": ["front-of-store", "fruit-veg"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    woolworths.category_lists_cache_path = str(cache_file)
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

    out = woolworths._get_all_categories(list_size=ListSize.TESTING)

    assert out == ["fruit-veg"]
    assert (
        len([c for c in web_driver.called if c[0] == "get_category_total_items"]) == 3
    )


def test_get_all_categories_falls_back_to_cache_on_exception(woolworths, tmp_path):
    cache_file = tmp_path / "woolworths-category-lists.json"
    cache_data = {
        "supermarket_categories": ["fruit-veg", "pantry"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
    woolworths.category_lists_cache_path = str(cache_file)

    def raise_error():
        raise Exception("boom")

    woolworths._get_supermarket_categories = raise_error

    out = woolworths._get_all_categories(ListSize.TESTING)

    assert out == ["fruit-veg"]


def test_get_supermarket_categories_returns_drawer_categories(woolworths, web_driver):
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

    categories = woolworths._get_supermarket_categories()
    names = [c["name"] for c in categories]

    assert names == ["fruit-veg", "pantry", "drinks"]
