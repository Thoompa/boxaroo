from Tests.test_helpers import (
    DummyLogger,
    DummyProductParser,
    DummyWebDriver,
    make_woolworths_category_data_normaliser,
)
from Code.contracts import ProductParseResult


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
    normaliser = make_woolworths_category_data_normaliser(
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


def test_get_category_data_uses_callback_parser_handoff_for_raw_product_texts():
    # GIVEN: a driver configured to invoke callback with raw product text payloads
    logger = DummyLogger()
    parser = DummyProductParser()
    parser.set_default_response(
        {
            "name": "Injected Name each",
            "price": "$2.50",
            "unit_price": "$2.50 / 1EA",
            "promotion": "",
            "missing_fields": [],
        }
    )
    web_driver = DummyWebDriver()
    web_driver.invoke_products_callback = True
    web_driver.category_total_items = 1
    web_driver.products_response = {
        "products": ["raw text from UI"],
        "incomplete_items": [],
        "page_stats": [],
    }
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: category data is retrieved from the normaliser
    result = normaliser.get_category_data("fruit-veg")

    # THEN: parser-driven product parsing is exercised through the callback handoff path
    assert parser.calls == ["raw text from UI"]
    assert result["products"] == [["Injected Name each", "$2.50", "$2.50 / 1EA", ""]]
    assert result["scraped"] == 1
    assert result["incomplete_items"] == []


def test_get_category_data_uses_callback_list_output_when_callback_returns_list():
    # GIVEN: a driver configured to invoke callback and a callback override that returns a plain product list
    logger = DummyLogger()
    parser = DummyProductParser()
    web_driver = DummyWebDriver()
    web_driver.invoke_products_callback = True
    web_driver.category_total_items = 1
    web_driver.products_response = {
        "products": ["raw text from UI"],
        "incomplete_items": [{"name": "stale", "missing": ["price"]}],
        "page_stats": [{"page": 1, "product_tiles": 1, "scraped": 1, "incomplete": 0}],
    }
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )
    normaliser._get_products_data = lambda _products, *, page_number: [
        [
            "Callback List Product",
            "$3.00",
            "$3.00 / 1EA",
            "",
        ]
    ]

    # WHEN: category data is retrieved from the normaliser
    result = normaliser.get_category_data("fruit-veg")

    # THEN: callback list output is used rather than raw products_response payload
    assert result["products"] == [["Callback List Product", "$3.00", "$3.00 / 1EA", ""]]
    assert result["scraped"] == 1
    assert result["incomplete_items"] == []


def test_get_category_data_logs_page_stats_when_callback_returns_dict():
    # GIVEN: a driver configured to invoke callback and return dict-shaped product data with page stats
    logger = DummyLogger()
    parser = DummyProductParser()
    parser.set_default_response(
        {
            "name": "Injected Name each",
            "price": "$2.50",
            "unit_price": "$2.50 / 1EA",
            "promotion": "",
            "missing_fields": ["promotion"],
        }
    )
    web_driver = DummyWebDriver()
    web_driver.invoke_products_callback = True
    web_driver.category_total_items = 1
    web_driver.products_response = {
        "products": ["raw text from UI"],
        "incomplete_items": [],
        "page_stats": [
            {
                "page": 1,
                "product_tiles": 1,
                "scraped": 1,
                "incomplete": 1,
            }
        ],
    }
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: category data is retrieved from the normaliser
    result = normaliser.get_category_data("fruit-veg")

    # THEN: callback dict output is used and page stats are logged through the category summary path
    assert result["products"] == [["Injected Name each", "$2.50", "$2.50 / 1EA", ""]]
    assert result["incomplete_items"] == [
        {"name": "Injected Name each", "missing": ["promotion"]}
    ]
    assert "Category fruit-veg - page 1 : tiles=1 scraped=1 incomplete=1" in [
        message for level, message in logger.records if level == "INFO"
    ]


def test_get_category_data_uses_scraped_count_when_total_is_none():
    # GIVEN: no total on page and two scraped products
    logger = DummyLogger()
    parser = DummyProductParser()
    web_driver = DummyWebDriver()
    web_driver.category_total_items = None
    web_driver.products_response = {
        "products": [
            ["Apple each", "$1.00", "$1.00 / 1EA", ""],
            ["Bread each", "$2.00", "$2.00 / 1EA", ""],
        ],
        "incomplete_items": [],
        "page_stats": [],
    }
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: category data is retrieved from the normaliser
    result = normaliser.get_category_data("bakery")

    # THEN: scraped count is used as total fallback
    assert result["total"] == 2
    assert result["scraped"] == 2


def test_get_category_data_returns_empty_shape_on_exception():
    # GIVEN: a driver where page loading raises an exception
    logger = DummyLogger()
    parser = DummyProductParser()
    web_driver = DummyWebDriver()

    def boom(url: str) -> None:
        raise RuntimeError("driver exploded")

    web_driver.get_page = boom
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: category data is retrieved while page loading fails
    result = normaliser.get_category_data("fruit-veg")

    # THEN: empty error payload is returned
    assert result["category"] == "fruit-veg"
    assert result["total"] == 0
    assert result["products"] == []
    assert result["incomplete_items"] == []
    assert result["scraped"] == 0
    assert result["incomplete"] == 0


def test_get_products_data_uses_injected_parser_and_unit_price_fallback():
    # GIVEN: parser output with missing price and available unit price
    logger = DummyLogger()
    parser = DummyProductParser()
    parser.set_default_response(
        {
            "name": "Injected Name each",
            "price": "",
            "unit_price": "$2.50 / 1EA",
            "promotion": "",
            "missing_fields": ["price"],
        }
    )
    web_driver = DummyWebDriver()
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: products payload is normalised from raw text items
    result = normaliser._get_products_data(["raw text from UI"])

    # THEN: injected parser values are used and price fallback is applied
    assert parser.calls == ["raw text from UI"]
    assert result["products"] == [
        ["Injected Name each", "$2.50 / 1EA", "$2.50 / 1EA", ""]
    ]
    assert result["incomplete_items"] == [
        {"name": "Injected Name each", "missing": ["price"]}
    ]


def test_get_products_data_continues_when_parser_raises_on_one_item():
    # GIVEN: a parser that raises on the first call and returns valid data on the second
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    parser = DummyProductParser()
    call_count = [0]

    def parse_with_error(text) -> ProductParseResult:
        call_count[0] += 1
        if call_count[0] == 1:
            raise ValueError("parse failed")
        return {
            "name": "Good Product",
            "price": "$1.00",
            "unit_price": "$1.00 / 1EA",
            "promotion": "",
            "missing_fields": [],
        }

    parser.parse = parse_with_error
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: products data is normalised from a list where one item causes a parse error
    result = normaliser._get_products_data(["bad item", "good item"])

    # THEN: the errored item is skipped and the remaining product is returned
    assert len(result["products"]) == 1
    assert result["products"][0][0] == "Good Product"
    error_logs = [msg for level, msg in logger.records if level == "ERROR"]
    assert len(error_logs) == 1


def test_dedupe_incomplete_items_handles_non_list_missing_field():
    # GIVEN: incomplete items where the missing field value is not a list
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    parser = DummyProductParser()
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )
    incomplete_items = [
        {"name": "Apple each", "missing": None},
        {"name": "Bread each", "missing": "price"},
        {"name": "Milk each", "missing": ["price", 1]},
    ]

    # WHEN: incomplete items are deduplicated
    result = normaliser._dedupe_incomplete_items(incomplete_items)

    # THEN: non-list missing fields are normalised to empty lists and list fields are stringified
    assert result == [
        {"name": "Apple each", "missing": []},
        {"name": "Bread each", "missing": []},
        {"name": "Milk each", "missing": ["price", "1"]},
    ]


def test_get_products_data_incomplete_tracking():
    # GIVEN: two product responses with missing fields
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    parser = DummyProductParser()
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
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: products data is retrieved from the inputs
    result = normaliser._get_products_data(["input1", "input2"])

    # THEN: incomplete items are tracked alongside valid products
    assert isinstance(result, dict)
    assert len(result["products"]) == 2
    assert len(result["incomplete_items"]) == 2
    assert result["products"][0][0] == "Product One each"
    assert result["products"][0][1] == "$2.00"
    assert result["products"][1][0] == "Product Two each"
    assert result["products"][1][1] == "$1.00 / 1EA"


def test_get_products_data_skips_empty_payload_and_continues():
    # GIVEN: an empty product followed by a valid product
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    parser = DummyProductParser()
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
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: products data is retrieved
    result = normaliser._get_products_data(["empty", "normal"])

    # THEN: empty products are skipped and processing continues
    assert len(result["products"]) == 1
    assert result["products"][0][0] == "Normal Product each"


def test_get_products_data_handles_multiple_valid_plain_text_payloads():
    # GIVEN: multiple valid product responses with various data
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    parser = DummyProductParser()
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
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: products data is retrieved from multiple payloads
    result = normaliser._get_products_data(["payload1", "payload2"])

    # THEN: all products are extracted with correct data
    assert len(result["products"]) == 2
    assert result["products"][0][0] == "Apple each"
    assert result["products"][0][1] == "$2.00"
    assert result["products"][1][0] == "Bread each"
    assert result["products"][1][3] == "2 for $3.50"


def test_get_products_data_skips_product_when_all_fields_are_empty():
    # GIVEN: a product with all empty fields followed by a valid product
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    parser = DummyProductParser()
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
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: products data is retrieved
    result = normaliser._get_products_data(["empty", "normal"])

    # THEN: empty product is skipped and a debug log is created
    assert len(result["products"]) == 1
    assert result["products"][0][0] == "Normal Product"
    debug_records = [msg for level, msg in logger.records if level == "DEBUG"]
    skip_logs = [msg for msg in debug_records if "Skipped empty product" in msg]
    assert len(skip_logs) > 0


def test_get_products_data_logs_page_number_context():
    # GIVEN: a normaliser and one product payload on page 2
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    parser = DummyProductParser()
    parser.set_default_response(
        {
            "name": "Injected Name each",
            "price": "$2.50",
            "unit_price": "$2.50 / 1EA",
            "promotion": "",
            "missing_fields": [],
        }
    )
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: product data is read with explicit page number context
    normaliser._get_products_data(["raw text from UI"], page_number=2)

    # THEN: the INFO log includes the page number and product count
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any(
        "Reading product data for page 2 with 1 products" in msg
        for msg in info_messages
    )


def test_get_category_data_logs_extraction_failures_in_page_stats():
    # GIVEN: page stats include one extraction failure
    logger = DummyLogger()
    parser = DummyProductParser()
    web_driver = DummyWebDriver()
    web_driver.category_total_items = 1
    web_driver.products_response = {
        "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
        "incomplete_items": [],
        "page_stats": [
            {
                "page": 1,
                "product_tiles": 2,
                "extraction_failures": 1,
                "scraped": 1,
                "incomplete": 0,
            }
        ],
    }
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: category data is retrieved from the normaliser
    normaliser.get_category_data("fruit-veg")

    # THEN: the per-page INFO log surfaces extraction failure count
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any("extraction_failures=1" in msg for msg in info_messages)


def test_get_category_data_logs_category_summary_with_duration():
    # GIVEN: a successful category scrape with known totals
    logger = DummyLogger()
    parser = DummyProductParser()
    web_driver = DummyWebDriver()
    web_driver.category_total_items = 3
    web_driver.products_response = {
        "products": [["A", "$1", "$1", ""], ["B", "$2", "$2", ""]],
        "incomplete_items": [{"name": "A", "missing": ["unit_price"]}],
        "page_stats": [],
    }
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: category data is retrieved
    normaliser.get_category_data("fruit-veg")

    # THEN: category summary includes found, scraped, incomplete, and elapsed time
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any(
        "Category fruit-veg summary" in msg
        and "found=3" in msg
        and "scraped=2" in msg
        and "incomplete=1" in msg
        and "took=" in msg
        for msg in info_messages
    )


def test_get_category_data_warns_when_found_scraped_gap_is_high():
    # GIVEN: page total is much higher than scraped products
    logger = DummyLogger()
    parser = DummyProductParser()
    web_driver = DummyWebDriver()
    web_driver.category_total_items = 100
    web_driver.products_response = {
        "products": [["A", "$1", "$1", ""]],
        "incomplete_items": [],
        "page_stats": [],
    }
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=parser
    )

    # WHEN: category data is retrieved
    normaliser.get_category_data("fruit-veg")

    # THEN: a WARNING log is emitted for high found-vs-scraped gap
    warning_messages = [msg for level, msg in logger.records if level == "WARNING"]
    assert any(
        "Category fruit-veg scrape gap warning" in msg for msg in warning_messages
    )
