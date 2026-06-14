from Tests.test_helpers import (
    DummyLogger,
    DummyProductParser,
    DummyWebDriver,
    make_coles_category_data_normaliser,
)


def test_get_category_data_returns_expected_shape_on_success():
    # GIVEN: category total and products payload from web driver
    logger = DummyLogger()
    parser = DummyProductParser()
    web_driver = DummyWebDriver()
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
    normaliser = make_coles_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: category data is retrieved from the normaliser
    result = normaliser.get_category_data("fruit-veg")

    # THEN: normalized payload is returned with deduplicated products and incomplete items
    assert result["category"] == "fruit-veg"
    assert result["total"] == 5
    assert result["products"] == [
        ["Apple each", "$1.00", "$1.00 / 1EA", ""],
        ["Bread each", "$2.00", "$2.00 / 1EA", ""],
    ]
    assert result["incomplete_items"] == [
        {"name": "Apple each", "missing": ["unit_price"]}
    ]
    assert result["scraped"] == 2
    assert result["incomplete"] == 1
