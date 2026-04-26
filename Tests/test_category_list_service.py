import json

import pytest

from Code.category_list_service import CategoryListCache, CategoryListService
from Code.isupermarket import ListSize
from Tests.test_helpers import DummyLogger


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
# Cache Loading: validation and usable payload handling
# ============================================================


def test_load_returns_none_when_file_missing(service):
    # GIVEN: the cache file does not exist
    # WHEN: the cache is loaded
    # THEN: no cache is returned
    assert service.load() is None


def test_load_returns_none_on_invalid_json(service, cache_file):
    # GIVEN: the cache file contains invalid JSON
    cache_file.write_text("not valid json { }", encoding="utf-8")

    # WHEN: the cache is loaded
    # THEN: no cache is returned
    assert service.load() is None


def test_load_returns_none_when_cache_root_is_not_dict(service, cache_file):
    # GIVEN: the cache file contains a non-dictionary root payload
    cache_file.write_text(json.dumps(["fruit-veg", "pantry"]), encoding="utf-8")

    # WHEN: the cache is loaded
    # THEN: no cache is returned
    assert service.load() is None


def test_load_returns_none_when_required_key_missing(service, cache_file):
    # GIVEN: the cache file is missing a required key
    cache_data = {
        "supermarket_categories": ["fruit-veg"],
        "testing": ["fruit-veg"],
        "short": ["fruit-veg"],
        # "full" key is missing — should fail validation
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    # WHEN: the cache is loaded
    # THEN: no cache is returned
    assert service.load() is None


def test_load_returns_none_when_required_key_is_not_list(service, cache_file):
    # GIVEN: a required key has an invalid non-list value
    cache_data = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg"],
        "full": "fruit-veg",
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    # WHEN: the cache is loaded
    # THEN: no cache is returned
    assert service.load() is None


# ------------------------------------------------------------
# Cache Loading: reconstruction of extended lists
# ------------------------------------------------------------


def test_load_happy_path_returns_cache(service, cache_file):
    # GIVEN: the cache file has all required category list keys
    cache_data = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "medium": ["fruit-veg", "pantry"],
        "long": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    # WHEN: the cache is loaded
    result = service.load()

    # THEN: the cached lists are returned as expected
    assert result is not None
    assert result["testing"] == ["fruit-veg"]
    assert result["full"] == ["fruit-veg", "pantry", "pet"]


def test_load_derives_medium_long_from_totals(service, cache_file):
    # GIVEN: medium and long are missing but category totals are present
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

    # WHEN: the cache is loaded
    result = service.load()

    # THEN: medium and long are derived from totals thresholds
    # medium threshold < 1800: fruit-veg (300), pantry (1500)
    assert sorted(result["medium"]) == ["fruit-veg", "pantry"]
    # long threshold < 10000: fruit-veg (300), pantry (1500), home-lifestyle (8000)
    assert sorted(result["long"]) == ["fruit-veg", "home-lifestyle", "pantry"]


def test_load_preserves_existing_medium_and_long(service, cache_file):
    # GIVEN: medium and long already exist in the cache
    cache_data = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg"],
        "medium": ["fruit-veg", "pantry"],
        "long": ["fruit-veg", "pantry", "pet"],
        "full": ["fruit-veg", "pantry", "pet", "baby"],
        "category_product_totals": {"fruit-veg": 300},
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    # WHEN: the cache is loaded
    result = service.load()

    # THEN: existing medium and long lists are preserved
    # Must not overwrite already-populated medium/long
    assert result["medium"] == ["fruit-veg", "pantry"]
    assert result["long"] == ["fruit-veg", "pantry", "pet"]


def test_load_falls_back_medium_to_short_when_no_totals(service, cache_file):
    # GIVEN: medium and long are missing and category totals are unavailable
    cache_data = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    # WHEN: the cache is loaded
    result = service.load()

    # THEN: medium falls back to short and long falls back to full
    assert result["medium"] == ["fruit-veg", "pantry"]
    assert result["long"] == ["fruit-veg", "pantry", "pet"]


# ============================================================
# List Refreshing: building category lists from product counts
# ============================================================


def test_refresh_builds_correct_lists_from_counts(service):
    # GIVEN: category counts spanning all list-size thresholds
    category_counts = [
        {"name": "fruit-veg", "count": 220},
        {"name": "pantry", "count": 1200},
        {"name": "dairy-eggs-fridge", "count": 1700},
        {"name": "home-lifestyle", "count": 5000},
        {"name": "electronics", "count": 12000},
        {"name": "liquor", "count": 80},
    ]

    # WHEN: category lists are refreshed
    out = service.refresh(category_counts)

    # THEN: each list and total map reflects threshold-based membership
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


def test_refresh_excludes_boundary_counts_from_short_medium_long(service):
    # GIVEN: category counts positioned on and around list-size boundaries
    category_counts = [
        {"name": "short-below", "count": 999},
        {"name": "short-boundary", "count": 1000},
        {"name": "medium-below", "count": 1799},
        {"name": "medium-boundary", "count": 1800},
        {"name": "long-below", "count": 9999},
        {"name": "long-boundary", "count": 10000},
    ]

    # WHEN: category lists are refreshed
    out = service.refresh(category_counts)

    # THEN: boundary values are excluded by strict less-than thresholds
    assert out["short"] == ["short-below"]
    assert out["medium"] == ["medium-below", "short-below", "short-boundary"]
    assert out["long"] == [
        "long-below",
        "medium-below",
        "medium-boundary",
        "short-below",
        "short-boundary",
    ]


def test_refresh_selects_testing_by_name_when_min_counts_tie(service):
    # GIVEN: multiple categories share the same minimum count
    category_counts = [
        {"name": "beta", "count": 10},
        {"name": "alpha", "count": 10},
        {"name": "gamma", "count": 20},
    ]

    # WHEN: category lists are refreshed
    out = service.refresh(category_counts)

    # THEN: the lexicographically first name is selected for testing
    assert out["testing"] == ["alpha"]


def test_refresh_computes_non_empty_list_product_totals(service):
    # GIVEN: category counts produce non-empty lists for all list sizes
    category_counts = [
        {"name": "a", "count": 100},
        {"name": "b", "count": 1000},
        {"name": "c", "count": 1799},
        {"name": "d", "count": 9999},
        {"name": "e", "count": 10000},
    ]

    # WHEN: category lists are refreshed
    out = service.refresh(category_counts)

    # THEN: list product totals are summed from the selected category sets
    assert out["list_product_totals"] == {
        "testing": 100,  # a=100
        "short": 100,  # a=100
        "medium": 2899,  # a=100 + b=1000 + c=1799
        "long": 12898,  # a=100 + b=1000 + c=1799 + d=9999
        "full": 22898,  # a=100 + b=1000 + c=1799 + d=9999 + e=10000
    }


def test_refresh_returns_empty_structure_when_all_counts_zero(service):
    # GIVEN: there are no category counts

    # WHEN: category lists are refreshed
    out = service.refresh([])

    # THEN: an empty structure with zero totals is returned
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
# Cache Persistence: writing normalised cache payloads
# ============================================================


def test_save_writes_correct_shape(tmp_path, logger):
    # GIVEN: a populated category list payload and a nested cache path
    cache_path = tmp_path / "cat" / "woolworths-category-lists.json"
    svc = CategoryListService(str(cache_path), logger)
    category_lists: CategoryListCache = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "medium": ["fruit-veg", "pantry"],
        "long": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
        "list_product_totals": {
            "testing": 100,
            "short": 500,
            "medium": 0,
            "long": 0,
            "full": 0,
        },
        "category_product_totals": {"fruit-veg": 300},
    }

    # WHEN: the cache is saved
    svc.save(category_lists, ["fruit-veg", "pantry", "pet"])

    with open(str(cache_path), "r", encoding="utf-8") as f:
        saved = json.load(f)

    # THEN: the saved file contains the expected schema and values
    assert saved["supermarket_categories"] == ["fruit-veg", "pantry", "pet"]
    assert saved["testing"] == ["fruit-veg"]
    assert saved["full"] == ["fruit-veg", "pantry", "pet"]
    assert saved["list_product_totals"] == {
        "testing": 100,
        "short": 500,
        "medium": 0,
        "long": 0,
        "full": 0,
    }
    assert saved["category_product_totals"] == {"fruit-veg": 300}


def test_save_normalizes_totals_when_list_product_totals_is_not_dict(tmp_path, logger):
    # GIVEN: list product totals are provided as a non-dictionary value
    cache_path = tmp_path / "woolworths-category-lists.json"
    svc = CategoryListService(str(cache_path), logger)
    category_lists: CategoryListCache = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg"],
        "full": ["fruit-veg"],
        "list_product_totals": "invalid",  # type: ignore[typeddict-item]
    }

    # WHEN: the cache is saved
    svc.save(category_lists, ["fruit-veg"])

    saved = json.loads(cache_path.read_text(encoding="utf-8"))

    # THEN: all totals are normalized to zero
    assert saved["list_product_totals"] == {
        "testing": 0,
        "short": 0,
        "medium": 0,
        "long": 0,
        "full": 0,
    }


def test_save_normalizes_non_int_total_values_to_zero(tmp_path, logger):
    # GIVEN: list product totals include non-integer values
    cache_path = tmp_path / "woolworths-category-lists.json"
    svc = CategoryListService(str(cache_path), logger)
    category_lists: CategoryListCache = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg"],
        "full": ["fruit-veg"],
        "list_product_totals": {
            "testing": 123,
            "short": "500",
            "medium": 3.14,
            "long": None,
            "full": [1, 2, 3],
        },
    }

    # WHEN: the cache is saved
    svc.save(category_lists, ["fruit-veg"])

    saved = json.loads(cache_path.read_text(encoding="utf-8"))

    # THEN: only integer values are preserved and others are normalized to zero
    assert saved["list_product_totals"] == {
        "testing": 123,
        "short": 0,
        "medium": 0,
        "long": 0,
        "full": 0,
    }


def test_save_works_when_cache_path_has_no_directory(tmp_path, logger, monkeypatch):
    # GIVEN: a cache filename without a parent directory component
    monkeypatch.chdir(tmp_path)
    cache_name = "woolworths-category-lists.json"
    svc = CategoryListService(cache_name, logger)
    category_lists: CategoryListCache = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
    }

    # WHEN: the cache is saved
    svc.save(category_lists, ["fruit-veg", "pantry", "pet"])

    saved = json.loads((tmp_path / cache_name).read_text(encoding="utf-8"))

    # THEN: the cache is written and missing totals are normalized to zero
    assert saved["supermarket_categories"] == ["fruit-veg", "pantry", "pet"]
    assert saved["testing"] == ["fruit-veg"]
    assert saved["list_product_totals"] == {
        "testing": 0,
        "short": 0,
        "medium": 0,
        "long": 0,
        "full": 0,
    }


# ============================================================
# List Selection: mapping list size to category list
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
    # GIVEN: category lists exist for each supported size
    category_lists = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "medium": ["fruit-veg", "pantry", "bakery"],
        "long": ["fruit-veg", "pantry", "bakery", "pet"],
        "full": ["fruit-veg", "pantry", "bakery", "pet", "baby"],
    }

    # WHEN: a list is selected by size
    result = service.select(category_lists, list_size)

    # THEN: the corresponding list is returned
    assert result == category_lists[key]


def test_select_missing_key_returns_empty(service):
    # GIVEN: no lists exist in the cache payload

    # WHEN: a missing list key is selected
    # THEN: an empty list is returned
    assert service.select({}, ListSize.FULL) == []


# ============================================================
# Cache Fallback Loading: resilient load behavior with logging
# ============================================================


def test_load_cached_lists_returns_loaded_cache_when_file_exists(service, cache_file):
    # GIVEN: a valid cache file is present
    cache_data = {
        "testing": ["fruit-veg"],
        "short": ["fruit-veg", "pantry"],
        "medium": ["fruit-veg", "pantry"],
        "long": ["fruit-veg", "pantry"],
        "full": ["fruit-veg", "pantry", "pet"],
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    # WHEN: cached lists are loaded through the fallback helper
    result = service.load_cached_lists()

    # THEN: cached category lists are returned
    assert result["testing"] == ["fruit-veg"]
    assert result["full"] == ["fruit-veg", "pantry", "pet"]


def test_load_cached_lists_logs_error_and_returns_empty_when_file_missing(
    service, logger
):
    # GIVEN: no usable cache file is present

    # WHEN: cached lists are loaded through the fallback helper
    result = service.load_cached_lists()

    # THEN: an error is logged and an empty cache is returned
    assert result == {}
    assert any(level == "ERROR" for level, _ in logger.records)
