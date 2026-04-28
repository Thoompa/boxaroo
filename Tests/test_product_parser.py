import pytest

from Code.product_parser import ProductParser
from Tests.test_helpers import DummyLogger


@pytest.fixture
def product_parser():
    return ProductParser(logger=DummyLogger())


# ============================================================
# Happy Path Extraction
# ============================================================


def test_parse_full_product_text(product_parser):
    # GIVEN: full product text containing price, unit price, promotion, and name
    text = """$1.20
$1.20 / 1EA
2 FOR $2.00 - $1.00/1EA
Avocado Shepard each
Add to cart
Save to list..."""

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: all fields are extracted and no required fields are missing
    assert parsed["name"] == "Avocado Shepard each"
    assert parsed["price"] == "$1.20"
    assert parsed["unit_price"] == "$1.20 / 1EA"
    assert parsed["promotion"] == "2 FOR $2.00 - $1.00/1EA"
    assert parsed["missing_fields"] == []


def test_parse_promotion_multi_for(product_parser):
    # GIVEN: product text with a multi-buy promotion
    text = "$1.50\n$3.00 / 2EA\n3 for $4.00\nPasta Sauce 500g\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the promotion and all required fields are extracted
    assert parsed["name"] == "Pasta Sauce 500g"
    assert parsed["price"] == "$1.50"
    assert parsed["unit_price"] == "$3.00 / 2EA"
    assert parsed["promotion"] == "3 for $4.00"
    assert parsed["missing_fields"] == []


# ============================================================
# Missing and Non-String Inputs
# ============================================================


def test_parse_missing_fields(product_parser):
    # GIVEN: product text with a name but no price or unit price
    text = "Avocado Shepard each\nAdd to cart\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: missing price fields are reported and promotion remains empty
    assert parsed["name"] == "Avocado Shepard each"
    assert parsed["price"] == ""
    assert parsed["unit_price"] == ""
    assert parsed["promotion"] == ""
    assert sorted(parsed["missing_fields"]) == ["price", "unit_price"]


def test_parse_non_string_input_returns_empty_fields(product_parser):
    # GIVEN: a None input value
    # WHEN: the value is parsed
    parsed = product_parser.parse(None)

    # THEN: all parsed fields are empty and all required fields are missing
    assert parsed == {
        "name": "",
        "price": "",
        "unit_price": "",
        "promotion": "",
        "missing_fields": ["name", "price", "unit_price"],
    }


def test_parse_empty_string(product_parser):
    # GIVEN: an empty text input
    # WHEN: the text is parsed
    parsed = product_parser.parse("")

    # THEN: all parsed fields are empty and all required fields are missing
    assert parsed["name"] == ""
    assert parsed["price"] == ""
    assert parsed["unit_price"] == ""
    assert parsed["promotion"] == ""
    assert sorted(parsed["missing_fields"]) == ["name", "price", "unit_price"]


def test_parse_integer_input_returns_empty_fields(product_parser):
    # GIVEN: a non-string scalar input value
    # WHEN: the value is parsed
    parsed = product_parser.parse(42)

    # THEN: parsing succeeds and returns empty parsed fields with all required fields missing
    assert isinstance(parsed, dict)
    assert parsed["name"] == ""
    assert parsed["price"] == ""
    assert parsed["unit_price"] == ""
    assert parsed["promotion"] == ""
    assert sorted(parsed["missing_fields"]) == ["name", "price", "unit_price"]


# ============================================================
# Product Name Candidate Filtering
# ============================================================


def test_parse_blacklisted_lines_yields_no_name(product_parser):
    # GIVEN: text containing only blacklisted UI labels
    text = "Promoted\nAdd to cart\nSave to list"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: no product name is selected
    assert parsed["name"] == ""
    assert "name" in parsed["missing_fields"]


def test_parse_dollar_prefix_line_not_used_as_name(product_parser):
    # GIVEN: text where price-prefixed lines appear before the product name
    text = "$5.00\n$5.00 / 1KG\nTest Product each\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the dollar-prefixed line is not used as the product name
    assert parsed["name"] == "Test Product each"
    assert parsed["price"] == "$5.00"


def test_parse_was_dollar_line_filtered_from_name(product_parser):
    # GIVEN: text containing a historical "Was $" line
    text = "$3.00\n$3.00 / 1EA\nWas $5.00\nFresh Bread each\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the "Was $" line is excluded from name selection
    assert parsed["name"] == "Fresh Bread each"


def test_parse_save_with_dollar_filtered_from_name(product_parser):
    # GIVEN: text containing a "Save $" line
    text = "$2.50\nSave $1.50\nYoghurt Berry 500g\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the "Save $" line is excluded from name selection
    assert parsed["name"] == "Yoghurt Berry 500g"


def test_parse_short_name_is_filtered(product_parser):
    # GIVEN: a short name candidate followed by a valid product name
    # "Abc" is < 6 chars and must not be chosen as product name
    text = "$1.00\nAbc\nGood Product each\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the short name candidate is ignored
    assert parsed["name"] == "Good Product each"


def test_parse_out_of_stock_label_filtered_from_name(product_parser):
    # GIVEN: text containing an out-of-stock label and a valid product name
    text = "$4.00\nOut of stock\nButter Unsalted 250g\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the out-of-stock label is excluded from name selection
    assert parsed["name"] == "Butter Unsalted 250g"


def test_parse_non_alphabetic_line_not_used_as_name(product_parser):
    # GIVEN: text where one line contains only digits
    text = "$2.00\n12345\nOrange Juice 1L\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the digits-only line is rejected and the real name is chosen
    assert parsed["name"] == "Orange Juice 1L"


def test_parse_price_label_filtered_from_name(product_parser):
    # GIVEN: text containing a short price-label line ("price" in ≤4 words)
    text = "$2.00\n$2.00 / 1EA\nClub Price\nOlive Oil 500ml\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the short price label is excluded from name selection
    assert parsed["name"] == "Olive Oil 500ml"


def test_parse_custom_blacklist_term_filtered_from_name():
    # GIVEN: a parser configured with an extra blacklist term
    parser = ProductParser(logger=DummyLogger(), blacklist=["special offer"])
    text = "$3.00\nSpecial Offer\nWhole Milk 1L\n"

    # WHEN: the text is parsed
    parsed = parser.parse(text)

    # THEN: the custom blacklist term is excluded from name selection
    assert parsed["name"] == "Whole Milk 1L"


def test_parse_fallback_name_selected_when_strict_candidates_fail(product_parser):
    # GIVEN: text where the only name candidate is too short for strict selection (< 6 chars)
    text = "$3.00\n$3.00 / 1EA\nBread\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the fallback path selects the short name rather than returning empty
    assert parsed["name"] == "Bread"


def test_parse_fallback_prefers_last_line_over_first(product_parser):
    # GIVEN: text where multiple lines pass only the fallback (both < 6 chars)
    text = "$2.00\nMilk\nBeer\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the last qualifying line in document order is chosen
    assert parsed["name"] == "Beer"


# ============================================================
# Price, Unit Price, and Promotion Extraction
# ============================================================


def test_parse_price_with_single_decimal_digit_not_extracted(product_parser):
    # GIVEN: text with a price written with only one decimal place
    text = "$1.2\nOrange Juice 1L\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the malformed price is not extracted and price is reported missing
    assert parsed["price"] == ""
    assert "price" in parsed["missing_fields"]


def test_parse_price_with_three_decimal_digits_not_extracted(product_parser):
    # GIVEN: text with a price written with three decimal places
    text = "$1.000\nOrange Juice 1L\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the malformed price is not extracted and price is reported missing
    assert parsed["price"] == ""
    assert "price" in parsed["missing_fields"]


def test_parse_price_with_trailing_text_captured_as_price(product_parser):
    # GIVEN: text with a per-item price value that includes unit text
    text = "$5 each\nOrange Juice 1L\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the per-item price is captured and unit price is normalized to the dollar amount
    assert parsed["price"] == "$5 each"
    assert parsed["unit_price"] == "$5"
    assert "price" not in parsed["missing_fields"]
    assert "unit_price" not in parsed["missing_fields"]


def test_parse_promotion_matches_any_line_containing_for_dollar(product_parser):
    # GIVEN: text with a line containing "for $" that is not a multi-buy promotion
    text = "$3.00\n$3.00 / 1EA\nBest value for $5\nCheddar Cheese 500g\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the "for $" line is matched as a promotion (no context check is applied)
    assert parsed["promotion"] == "Best value for $5"
    assert parsed["name"] == "Cheddar Cheese 500g"


def test_parse_was_dollar_line_captured_as_promotion(product_parser):
    # GIVEN: text containing a "Was $" original-price line
    text = "$3.00\n$3.00 / 1EA\nWas $5.00\nFresh Bread each\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the "Was $" line is captured as a promotion
    assert parsed["promotion"] == "Was $5.00"


def test_parse_save_dollar_line_captured_as_promotion(product_parser):
    # GIVEN: text containing a "Save $" savings line
    text = "$2.50\n$2.50 / 1EA\nSave $1.50\nYoghurt Berry 500g\n"

    # WHEN: the text is parsed
    parsed = product_parser.parse(text)

    # THEN: the "Save $" line is captured as a promotion
    assert parsed["promotion"] == "Save $1.50"


def test_parse_price_with_single_decimal_logs_rejection():
    # GIVEN: a parser with a logger and a price written with only one decimal place
    logger = DummyLogger()
    parser = ProductParser(logger=logger)
    text = "$1.2\nMilk 2L\n"

    # WHEN: the text is parsed
    parser.parse(text)

    # THEN: the malformed price is logged
    assert any("$1.2" in msg for _, msg in logger.records)


def test_parse_price_with_three_decimal_digits_logs_rejection():
    # GIVEN: a parser with a logger and a price written with three decimal places
    logger = DummyLogger()
    parser = ProductParser(logger=logger)
    text = "$1.000\nMilk 2L\n"

    # WHEN: the text is parsed
    parser.parse(text)

    # THEN: the malformed price is logged
    assert any("$1.000" in msg for _, msg in logger.records)
