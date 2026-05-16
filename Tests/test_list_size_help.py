import json
import os

import pytest

from Code.list_size_help import (
    RuntimeProfile,
    build_list_size_help,
    format_list_size_eta,
    load_performance_profile,
)

VALID_CONFIG_PATH = os.path.join("Tests", "fixtures", "performance.valid.json")


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle)


def _write_list_totals_cache(path, totals):
    _write_json(path, {"list_product_totals": totals})


def _assert_count_only_help(help_text: str) -> None:
    assert "Product counts by list" in help_text
    assert "Estimated runtime by list" not in help_text
    assert "~" not in help_text
    assert "products" in help_text


def test_load_performance_profile_returns_valid_fixture_data():
    # GIVEN: A valid per-device performance config fixture

    # WHEN: The performance profile is loaded
    profile = load_performance_profile(VALID_CONFIG_PATH)

    # THEN: Interactive and headless values are returned as runtime profiles
    assert profile is not None
    assert profile["interactive"]["products_per_second"] == 4.0
    assert profile["interactive"]["fixed_overhead_seconds"] == 0.0
    assert profile["headless"]["products_per_second"] == 2.0
    assert profile["headless"]["fixed_overhead_seconds"] == 30.0


@pytest.mark.parametrize(
    "total_products, expected_eta",
    [
        (600, "~2m 30s"),
        (14892, "~1h 2m 3s"),
        (14400, "~1h"),
    ],
)
def test_format_list_size_eta_preserves_large_duration_formatting(
    total_products, expected_eta
):
    # GIVEN: An interactive runtime profile and larger product totals
    profile: RuntimeProfile = {
        "products_per_second": 4.0,
        "fixed_overhead_seconds": 0.0,
    }

    # WHEN: The ETA text is formatted
    eta_text = format_list_size_eta(total_products, profile)

    # THEN: Minute and hour formatting remains stable after the helper move
    assert eta_text == expected_eta


def test_build_list_size_help_uses_dual_mode_eta_text(tmp_path):
    # GIVEN: A valid config and complete list totals cache
    cache_path = tmp_path / "woolworths-category-lists.json"
    _write_list_totals_cache(
        cache_path,
        {
            "testing": 8,
            "short": 16,
            "medium": 24,
            "long": 32,
            "full": 40,
        },
    )

    # WHEN: Help text is built
    help_text = build_list_size_help(
        config_path=VALID_CONFIG_PATH,
        cache_path=str(cache_path),
    )

    # THEN: ETA wording shows both interactive and headless runtimes
    assert "Estimated runtime by list (interactive / headless)" in help_text
    assert "TESTING ~2s / ~34s" in help_text
    assert "SHORT ~4s / ~38s" in help_text
    assert "MEDIUM ~6s / ~42s" in help_text
    assert "LONG ~8s / ~46s" in help_text
    assert "FULL ~10s / ~50s" in help_text


def test_build_list_size_help_falls_back_to_counts_when_config_missing(tmp_path):
    # GIVEN: Config file is missing and cache data exists
    cache_path = tmp_path / "woolworths-category-lists.json"
    _write_list_totals_cache(
        cache_path,
        {
            "testing": 11,
            "short": 22,
            "medium": 33,
            "long": 44,
            "full": 55,
        },
    )

    # WHEN: Help text is built with a missing config path
    help_text = build_list_size_help(
        config_path=str(tmp_path / "missing.json"),
        cache_path=str(cache_path),
    )

    # THEN: Count-only wording is shown instead of ETA wording
    _assert_count_only_help(help_text)
    assert "TESTING 11 products" in help_text
    assert "FULL 55 products" in help_text


def test_build_list_size_help_falls_back_to_counts_when_config_is_malformed(tmp_path):
    # GIVEN: Config file contains invalid JSON and cache data exists
    config_path = tmp_path / "performance.json"
    cache_path = tmp_path / "woolworths-category-lists.json"
    config_path.write_text("{", encoding="utf-8")
    _write_list_totals_cache(
        cache_path,
        {
            "testing": 11,
            "short": 22,
            "medium": 33,
            "long": 44,
            "full": 55,
        },
    )

    # WHEN: Help text is built
    help_text = build_list_size_help(
        config_path=str(config_path),
        cache_path=str(cache_path),
    )

    # THEN: Count-only wording is shown instead of ETA wording
    _assert_count_only_help(help_text)


def test_build_list_size_help_falls_back_to_counts_when_config_missing_fields(tmp_path):
    # GIVEN: Config file omits required fields and cache data exists
    config_path = tmp_path / "performance.json"
    cache_path = tmp_path / "woolworths-category-lists.json"
    _write_json(
        config_path,
        {
            "headless": {
                "products_per_second": 1.0,
            },
            "interactive": {
                "products_per_second": 1.0,
                "fixed_overhead_seconds": 0,
            },
        },
    )
    _write_list_totals_cache(
        cache_path,
        {
            "testing": 11,
            "short": 22,
            "medium": 33,
            "long": 44,
            "full": 55,
        },
    )

    # WHEN: Help text is built
    help_text = build_list_size_help(
        config_path=str(config_path),
        cache_path=str(cache_path),
    )

    # THEN: Count-only wording is shown instead of ETA wording
    _assert_count_only_help(help_text)


def test_build_list_size_help_falls_back_to_counts_when_rate_is_invalid(tmp_path):
    # GIVEN: Config file uses zero products-per-second and cache data exists
    config_path = tmp_path / "performance.json"
    cache_path = tmp_path / "woolworths-category-lists.json"
    _write_json(
        config_path,
        {
            "headless": {
                "products_per_second": 0,
                "fixed_overhead_seconds": 30,
            },
            "interactive": {
                "products_per_second": 4,
                "fixed_overhead_seconds": 0,
            },
        },
    )
    _write_list_totals_cache(
        cache_path,
        {
            "testing": 11,
            "short": 22,
            "medium": 33,
            "long": 44,
            "full": 55,
        },
    )

    # WHEN: Help text is built
    help_text = build_list_size_help(
        config_path=str(config_path),
        cache_path=str(cache_path),
    )

    # THEN: Count-only wording is shown instead of ETA wording
    _assert_count_only_help(help_text)


def test_build_list_size_help_falls_back_to_counts_when_cache_is_incomplete(tmp_path):
    # GIVEN: Config file is valid but cache omits list sizes
    cache_path = tmp_path / "woolworths-category-lists.json"
    _write_list_totals_cache(cache_path, {"testing": 11, "short": 22})

    # WHEN: Help text is built
    help_text = build_list_size_help(
        config_path=VALID_CONFIG_PATH,
        cache_path=str(cache_path),
    )

    # THEN: Count-only wording is shown instead of ETA wording
    _assert_count_only_help(help_text)
    assert "TESTING 11 products" in help_text
    assert "MEDIUM n/a products" in help_text


def test_build_list_size_help_falls_back_to_counts_when_cache_is_malformed(tmp_path):
    # GIVEN: Config file is valid but cache contains invalid JSON
    cache_path = tmp_path / "woolworths-category-lists.json"
    cache_path.write_text("{", encoding="utf-8")

    # WHEN: Help text is built
    help_text = build_list_size_help(
        config_path=VALID_CONFIG_PATH,
        cache_path=str(cache_path),
    )

    # THEN: Count-only wording is shown instead of ETA wording
    _assert_count_only_help(help_text)
    assert "TESTING n/a products" in help_text
    assert "FULL n/a products" in help_text
