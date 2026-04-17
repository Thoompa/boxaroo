import pytest

from Code.product_parser import ProductParser


@pytest.fixture
def product_parser():
    return ProductParser()


def test_parse_full_product_text(product_parser):
    text = """$1.20
$1.20 / 1EA
2 FOR $2.00 - $1.00/1EA
Avocado Shepard each
Add to cart
Save to list..."""

    parsed = product_parser.parse(text)

    assert parsed["name"] == "Avocado Shepard each"
    assert parsed["price"] == "$1.20"
    assert parsed["unit_price"] == "$1.20 / 1EA"
    assert parsed["promotion"] == "2 FOR $2.00 - $1.00/1EA"
    assert parsed["missing_fields"] == []


def test_parse_missing_fields(product_parser):
    text = "Avocado Shepard each\nAdd to cart\n"

    parsed = product_parser.parse(text)

    assert parsed["name"] == "Avocado Shepard each"
    assert parsed["price"] == ""
    assert parsed["unit_price"] == ""
    assert parsed["promotion"] == ""
    assert sorted(parsed["missing_fields"]) == ["price", "unit_price"]


def test_parse_non_string_input_returns_empty_fields(product_parser):
    parsed = product_parser.parse(None)

    assert parsed == {
        "name": "",
        "price": "",
        "unit_price": "",
        "promotion": "",
        "missing_fields": ["name", "price", "unit_price"],
    }


def test_parse_blacklisted_lines_yields_no_name(product_parser):
    text = "Promoted\nAdd to cart\nSave to list"

    parsed = product_parser.parse(text)

    assert parsed["name"] == ""
    assert "name" in parsed["missing_fields"]


def test_parse_promotion_multi_for(product_parser):
    text = "$1.50\n$3.00 / 2EA\n3 for $4.00\nPasta Sauce 500g\n"

    parsed = product_parser.parse(text)

    assert parsed["name"] == "Pasta Sauce 500g"
    assert parsed["price"] == "$1.50"
    assert parsed["unit_price"] == "$3.00 / 2EA"
    assert parsed["promotion"] == "3 for $4.00"
    assert parsed["missing_fields"] == []


def test_parse_empty_string(product_parser):
    parsed = product_parser.parse("")
    assert parsed["name"] == ""
    assert parsed["price"] == ""
    assert parsed["unit_price"] == ""
    assert parsed["promotion"] == ""


def test_parse_dollar_prefix_line_not_used_as_name(product_parser):
    text = "$5.00\n$5.00 / 1KG\nTest Product each\n"
    parsed = product_parser.parse(text)
    assert parsed["name"] == "Test Product each"
    assert parsed["price"] == "$5.00"


def test_parse_was_dollar_line_filtered_from_name(product_parser):
    text = "$3.00\n$3.00 / 1EA\nWas $5.00\nFresh Bread each\n"
    parsed = product_parser.parse(text)
    assert parsed["name"] == "Fresh Bread each"


def test_parse_save_with_dollar_filtered_from_name(product_parser):
    text = "$2.50\nSave $1.50\nYoghurt Berry 500g\n"
    parsed = product_parser.parse(text)
    assert parsed["name"] == "Yoghurt Berry 500g"


def test_parse_short_name_is_filtered(product_parser):
    # "Abc" is < 6 chars and must not be chosen as product name
    text = "$1.00\nAbc\nGood Product each\n"
    parsed = product_parser.parse(text)
    assert parsed["name"] == "Good Product each"


def test_parse_integer_input_returns_empty_fields(product_parser):
    parsed = product_parser.parse(42)
    assert isinstance(parsed, dict)
    assert parsed["name"] == ""
    assert parsed["price"] == ""
    assert parsed["unit_price"] == ""
    assert parsed["promotion"] == ""


def test_parse_out_of_stock_label_filtered_from_name(product_parser):
    text = "$4.00\nOut of stock\nButter Unsalted 250g\n"
    parsed = product_parser.parse(text)
    assert parsed["name"] == "Butter Unsalted 250g"
