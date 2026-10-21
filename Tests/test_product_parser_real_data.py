"""ProductParser against real tile text captured from woolworths.com.au.

`Tests/fixtures/tiles/*.json` holds raw tile text exactly as the scraper
receives it; refresh it with `python Scripts/capture_tile_fixtures.py`.

A case the parser gets wrong should be written with the *correct* expected
output and marked `xfail(strict=True)`, so it fails the run once fixed and the
marker is removed.
"""

import json
import re
from pathlib import Path

import pytest

from Code.product_parser import ProductParser
from Tests.test_helpers import DummyLogger

TILE_DIR = Path(__file__).parent / "fixtures" / "tiles"

# Badge and banner text that appears on tiles but is never a product name.
NOT_A_NAME = re.compile(
    r"^(in-store only|supply update|everyday low price|extra \d+% off|designs may vary"
    r"|est\. restock|lowest price|save \$|\[unknown\]|[^a-z0-9]*$|/)",
    re.IGNORECASE,
)
SINGLE_UNIT_PRICE = re.compile(r"^\$\d+(\.\d{2})? / \w+$")


@pytest.fixture(scope="module")
def parser():
    return ProductParser(logger=DummyLogger())


@pytest.fixture(scope="module")
def real_tiles() -> list[tuple[str, str]]:
    tiles = []
    for path in sorted(TILE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        tiles.extend((path.stem, tile) for tile in data["tiles"])
    return tiles


def parsed(parser, tiles):
    return [(category, tile, parser.parse(tile)) for category, tile in tiles]


# ============================================================
# Individual tiles
# ============================================================

CORRECT_CASES = {
    "per-item-price": (
        "$2.50\n$2.50 / 1EA\nHass Avocado each\nAdd to cart\nSave to list",
        {
            "name": "Hass Avocado each",
            "price": "$2.50",
            "unit_price": "$2.50 / 1EA",
            "promotion": "",
        },
    ),
    "per-kg-price": (
        "$4.50\n$18.00 / 1KG\nStrawberries Punnet 250g\nAdd to cart\nSave to list",
        {
            "name": "Strawberries Punnet 250g",
            "price": "$4.50",
            "unit_price": "$18.00 / 1KG",
            "promotion": "",
        },
    ),
    "multibuy-has-no-unit-price": (
        "$20.00\n2 FOR $22.00\nCape Campbell Marlborough Sauvignon Blanc Marlborough"
        " 750ml\nAdd to cart\nSave to list",
        {
            "name": "Cape Campbell Marlborough Sauvignon Blanc Marlborough 750ml",
            "price": "$20.00",
            "unit_price": "",
            "promotion": "2 FOR $22.00",
        },
    ),
    "marketplace-seller-has-no-unit-price": (
        "$389.99\nPokemon TCG 30th Anniversary Celebrations Elite Trainer Box ETB\n"
        "Sold by Serakaia\nAdd to cart\nSave to list",
        {
            "name": "Pokemon TCG 30th Anniversary Celebrations Elite Trainer Box ETB",
            "price": "$389.99",
            "unit_price": "",
            "promotion": "",
        },
    ),
    "special-shows-sale-price-first": (
        "SAVE $2.25\n$3.35\n$5.60\nSharpie Permanent Marker Pens Fine Point Black 2 pack"
        "\nPromoted\nAdd to cart\nSave to list",
        {
            "name": "Sharpie Permanent Marker Pens Fine Point Black 2 pack",
            "price": "$3.35",
            "unit_price": "",
            "promotion": "SAVE $2.25",
        },
    ),
    "out-of-stock-has-no-price": (
        "OUT OF STOCK\nWhite & Black Chair Covers Spandex Folding Banquet Wedding Party"
        " Covers Banquet BLACK / 1X\nAdd to cart\nSave to list",
        {
            "name": "White & Black Chair Covers Spandex Folding Banquet Wedding Party"
            " Covers Banquet BLACK / 1X",
            "price": "",
            "unit_price": "",
            "promotion": "",
        },
    ),
    "in-store-only-badge-before-name": (
        "IN-STORE ONLY\nSellotape Masking Tape 24Mm X 18M each\nView similar\nproducts\n             to Sellotape Masking Tape 24Mm X 18M each\nSave to list",
        {"name": "Sellotape Masking Tape 24Mm X 18M each"},
    ),
    "supply-update-badge-before-name": (
        "$0.88\n$0.88 / 1EA\nSUPPLY UPDATE^\nCavendish Bananas each\nAdd to cart\nSave to list",
        {"name": "Cavendish Bananas each"},
    ),
    "promotion-banner-before-name": (
        "SAVE $8.00\n$12.00\n$20.00\nEXTRA 15% OFF WHEN YOU SPEND $75 ON LIQUOR. T&CS APPLY^^\nMarlborough Sounds Sauvignon Blanc 750ml\nAdd to cart\nSave to list",
        {"name": "Marlborough Sounds Sauvignon Blanc 750ml"},
    ),
    "unit-fragment-line-before-name": (
        "SAVE $0.65\n$2.95\n/ 100G\n$3.60 / 100G $29.50 / 1KG\nPrice per kg charged\nKRC Mild Hungarian Salami Shaved From The Deli per 100g\nAdd to cart\nSave to list",
        {"name": "KRC Mild Hungarian Salami Shaved From The Deli per 100g"},
    ),
    "unit-price-glued-to-the-was-price": (
        "SAVE $6.50\n$6.00\n$12.50 $30.00 / 1KG\nTasmanian Heritage Double Brie Cheese 200g\nAdd to cart\nSave to list",
        {"unit_price": "$30.00 / 1KG"},
    ),
}


@pytest.mark.parametrize(
    ("tile", "expected"), CORRECT_CASES.values(), ids=CORRECT_CASES.keys()
)
def test_real_tile_is_parsed_correctly(parser, tile, expected):
    # GIVEN: raw text of a real product tile

    # WHEN: the tile is parsed
    result = parser.parse(tile)

    # THEN: the fields match what the page shows
    assert {key: result[key] for key in expected} == expected


# ============================================================
# Every captured tile
# ============================================================


def test_real_tiles_are_captured(real_tiles):
    # GIVEN/WHEN: the captured fixtures are loaded
    # THEN: there is a useful spread of them, from several categories
    assert len(real_tiles) >= 400
    assert len({category for category, _ in real_tiles}) >= 6


def test_every_real_tile_parses_without_error(parser, real_tiles):
    # GIVEN: every captured tile

    # WHEN: each is parsed
    results = parsed(parser, real_tiles)

    # THEN: every tile yields a result with all the fields
    for _, _, result in results:
        assert set(result) == {
            "name",
            "price",
            "unit_price",
            "promotion",
            "missing_fields",
        }


def test_nearly_every_real_tile_has_a_price(parser, real_tiles):
    # GIVEN: every captured tile

    # WHEN: each is parsed
    results = parsed(parser, real_tiles)

    # THEN: almost all have a price (out-of-stock and in-store only tiles do not)
    without_price = [tile for _, tile, result in results if not result["price"]]
    assert len(without_price) <= 0.02 * len(results), without_price[:3]


def test_every_real_tile_name_is_a_product_name(parser, real_tiles):
    # GIVEN: every captured tile

    # WHEN: each is parsed
    results = parsed(parser, real_tiles)

    # THEN: no name is badge or banner text, or a stray unit like "/ 100G"
    wrong = [
        result["name"] for _, _, result in results if NOT_A_NAME.match(result["name"])
    ]
    assert (
        not wrong
    ), f"{len(wrong)} of {len(results)} names are not product names: {wrong[:5]}"


def test_every_real_tile_unit_price_is_a_single_price_per_unit(parser, real_tiles):
    # GIVEN: every captured tile

    # WHEN: each is parsed
    results = parsed(parser, real_tiles)

    # THEN: every unit price that exists is exactly one "$x / unit" value
    wrong = [
        result["unit_price"]
        for _, _, result in results
        if result["unit_price"] and not SINGLE_UNIT_PRICE.match(result["unit_price"])
    ]
    assert (
        not wrong
    ), f"{len(wrong)} of {len(results)} unit prices are not a single price per unit: {wrong[:5]}"
