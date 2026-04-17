import json

import pytest

from Code.category_list_service import CategoryListService
from Code.isupermarket import ListSize
from tests.test_helpers import DummyLogger


@pytest.fixture
def logger():
    return DummyLogger()


@pytest.fixture
def cache_file(tmp_path):
    return tmp_path / "woolworths-category-lists.json"


@pytest.fixture
def service(cache_file, logger):
    return CategoryListService(str(cache_file), logger)


# ============================================================
# SEAM: load
# ============================================================


def test_load_returns_none_when_file_missing(service):
    assert service.load() is None


def test_load_returns_none_on_invalid_json(service, cache_file):
    cache_file.write_text("not valid json { }", encoding="utf-8")
    assert service.load() is None


def test_load_returns_none_when_required_key_missing(service, cache_file):
    cache_data = {
        "supermarket_categories": ["fruit-veg"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg"],
        # "full" key is missing — should fail validation
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
    assert service.load() is None


def test_load_happy_path_returns_cache(service, cache_file):
    cache_data = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "medium": ["fruit-veg", "pantry"],
        "long": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    result = service.load()

    assert result is not None
    assert result["testing"] == ["fruit-veg"]
    assert result["full"] == ["fruit-veg", "pantry", "pet"]


def test_load_derives_medium_long_from_totals(service, cache_file):
    cache_data = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg"],
        "full": ["electronics", "fruit-veg", "home-lifestyle", "pantry"],
        "category_product_totals": {
            "fruit-veg": 300,
            "pantry": 1500,
            "home-lifestyle": 8000,
            "electronics": 15000,
        },
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    result = service.load()

    # medium threshold < 1800: fruit-veg (300), pantry (1500)
    assert sorted(result["medium"]) == ["fruit-veg", "pantry"]
    # long threshold < 10000: fruit-veg (300), pantry (1500), home-lifestyle (8000)
    assert sorted(result["long"]) == ["fruit-veg", "home-lifestyle", "pantry"]


def test_load_preserves_existing_medium_and_long(service, cache_file):
    cache_data = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg"],
        "medium": ["fruit-veg", "pantry"],
        "long": ["fruit-veg", "pantry", "pet"],
        "full": ["fruit-veg", "pantry", "pet", "baby"],
        "category_product_totals": {"fruit-veg": 300},
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    result = service.load()

    # Must not overwrite already-populated medium/long
    assert result["medium"] == ["fruit-veg", "pantry"]
    assert result["long"] == ["fruit-veg", "pantry", "pet"]


def test_load_falls_back_medium_to_short_when_no_totals(service, cache_file):
    cache_data = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    result = service.load()

    assert result["medium"] == ["fruit-veg", "pantry"]
    assert result["long"] == ["fruit-veg", "pantry", "pet"]


# ============================================================
# SEAM: refresh
# ============================================================


def test_refresh_builds_correct_lists_from_counts(service):
    category_counts = [
        {"name": "fruit-veg", "count": 220},
        {"name": "pantry", "count": 1200},
        {"name": "dairy-eggs-fridge", "count": 1700},
        {"name": "home-lifestyle", "count": 5000},
        {"name": "electronics", "count": 12000},
        {"name": "liquor", "count": 80},
    ]

    out = service.refresh(category_counts)

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
    assert out["category_product_totals"]["liquor"] == 80
    assert out["category_product_totals"]["electronics"] == 12000


def test_refresh_returns_empty_structure_when_all_counts_zero(service):
    out = service.refresh([])

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
# SEAM: save
# ============================================================


def test_save_writes_correct_shape(tmp_path, logger):
    cache_path = tmp_path / "cat" / "woolworths-category-lists.json"
    svc = CategoryListService(str(cache_path), logger)
    category_lists = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "medium": ["fruit-veg", "pantry"],
        "long": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
        "list_product_totals": {"testing": 100, "short": 500},
        "category_product_totals": {"fruit-veg": 300},
    }

    svc.save(category_lists, ["fruit-veg", "pantry", "pet"])

    with open(str(cache_path), "r", encoding="utf-8") as f:
        saved = json.load(f)

    assert saved["supermarket_categories"] == ["fruit-veg", "pantry", "pet"]
    assert saved["testing"] == ["fruit-veg"]
    assert saved["full"] == ["fruit-veg", "pantry", "pet"]
    assert saved["list_product_totals"] == {"testing": 100, "short": 500}
    assert saved["category_product_totals"] == {"fruit-veg": 300}


# ============================================================
# SEAM: select
# ============================================================


@pytest.mark.parametrize(
    "list_size, key",
    [
        (ListSize.TESTING, "testing"),
        (ListSize.SHORT, "short"),
        (ListSize.MEDIUM, "medium"),
        (ListSize.LONG, "long"),
        (ListSize.FULL, "full"),
    ],
)
def test_select_returns_correct_list_for_all_sizes(service, list_size, key):
    category_lists = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "medium": ["fruit-veg", "pantry", "bakery"],
        "long": ["fruit-veg", "pantry", "bakery", "pet"],
        "full": ["fruit-veg", "pantry", "bakery", "pet", "baby"],
    }

    result = service.select(category_lists, list_size)

    assert result == category_lists[key]


def test_select_missing_key_returns_empty(service):
    assert service.select({}, ListSize.FULL) == []


# ============================================================
# SEAM: get_default_lists
# ============================================================


def test_get_default_lists_returns_loaded_cache_when_file_exists(service, cache_file):
    cache_data = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "medium": ["fruit-veg", "pantry"],
        "long": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    result = service.get_default_lists()

    assert result["testing"] == ["fruit-veg"]
    assert result["full"] == ["fruit-veg", "pantry", "pet"]


def test_get_default_lists_logs_error_and_returns_empty_when_file_missing(
    service, logger
):
    result = service.get_default_lists()

    assert result == {}
    assert any(level == "ERROR" for level, _ in logger.records)
