"""List-size help text helpers with per-device performance config."""

import json
import os
from collections.abc import Callable
from typing import TypedDict

from Code.contracts import ListSize


class RuntimeProfile(TypedDict):
    products_per_second: float
    fixed_overhead_seconds: float


class PerformanceConfig(TypedDict):
    max_pages_per_session: int
    headless: RuntimeProfile
    interactive: RuntimeProfile


PERFORMANCE_CONFIG_PATH = os.path.join("Config", "performance.json")
PERFORMANCE_CONFIG_TEMPLATE_PATH = os.path.join("Config", "performance.example.json")
LIST_TOTALS_CACHE_PATH = os.path.join(
    "Data", "category_lists", "woolworths-category-lists.json"
)
LIST_SIZE_KEYS = tuple(size.name.lower() for size in ListSize)
_PERFORMANCE_MODES = ("headless", "interactive")

_PROFILE_FIELD_CONSTRAINTS: dict[str, Callable[[float], bool]] = {
    "products_per_second": lambda v: v > 0,
    "fixed_overhead_seconds": lambda v: v >= 0,
}


def _load_list_product_totals(
    cache_path: str = LIST_TOTALS_CACHE_PATH,
) -> dict[str, int]:
    try:
        with open(cache_path, "r", encoding="utf-8") as file_handle:
            cached = json.load(file_handle)
        totals = cached.get("list_product_totals", {})
        if not isinstance(totals, dict):
            return {}
        return {
            str(key).lower(): int(value)
            for key, value in totals.items()
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        }
    except Exception:
        return {}


def _validate_runtime_profile(profile: object) -> RuntimeProfile | None:
    if not isinstance(profile, dict):
        return None

    validated: dict[str, float] = {}
    for key, is_valid in _PROFILE_FIELD_CONSTRAINTS.items():
        value = profile.get(key)
        if not isinstance(value, (int, float)) or not is_valid(value):
            return None
        validated[key] = float(value)

    return validated  # type: ignore[return-value]


def load_performance_profile(
    config_path: str = PERFORMANCE_CONFIG_PATH,
) -> PerformanceConfig | None:
    try:
        with open(config_path, "r", encoding="utf-8") as file_handle:
            raw_profile = json.load(file_handle)
    except Exception:
        if config_path != PERFORMANCE_CONFIG_PATH:
            return None
        try:
            with open(
                PERFORMANCE_CONFIG_TEMPLATE_PATH, "r", encoding="utf-8"
            ) as file_handle:
                raw_profile = json.load(file_handle)
        except Exception:
            return None

    if not isinstance(raw_profile, dict):
        return None

    max_pages_per_session = raw_profile.get("max_pages_per_session")
    if (
        not isinstance(max_pages_per_session, int)
        or isinstance(max_pages_per_session, bool)
        or max_pages_per_session <= 0
    ):
        return None

    profiles: dict[str, RuntimeProfile] = {}
    for mode in _PERFORMANCE_MODES:
        profile = _validate_runtime_profile(raw_profile.get(mode))
        if profile is None:
            return None
        profiles[mode] = profile

    return {
        "max_pages_per_session": max_pages_per_session,
        **profiles,
    }


def _format_duration(total_seconds: int) -> str:
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return "~" + " ".join(parts)


def format_list_size_eta(total_products: int | None, profile: RuntimeProfile) -> str:
    if total_products is None:
        return "n/a"

    estimated_seconds = profile["fixed_overhead_seconds"] + (
        total_products / profile["products_per_second"]
    )
    return _format_duration(round(estimated_seconds))


def format_list_size_count(total_products: int | None) -> str:
    if total_products is None:
        return "n/a products"
    return f"{total_products} products"


def _eta_is_available(
    performance_profile: PerformanceConfig | None, totals: dict[str, int]
) -> bool:
    return performance_profile is not None and all(
        size in totals for size in LIST_SIZE_KEYS
    )


def _format_list_size_mode_pair(
    size: str, totals: dict[str, int], performance_profile: PerformanceConfig
) -> str:
    interactive_eta = format_list_size_eta(
        totals.get(size), performance_profile["interactive"]
    )
    headless_eta = format_list_size_eta(
        totals.get(size), performance_profile["headless"]
    )
    return f"{size.upper()} {interactive_eta} / {headless_eta}"


def build_list_size_help(
    *,
    config_path: str = PERFORMANCE_CONFIG_PATH,
    cache_path: str = LIST_TOTALS_CACHE_PATH,
) -> str:
    totals = _load_list_product_totals(cache_path)
    performance_profile = load_performance_profile(config_path)

    if _eta_is_available(performance_profile, totals):
        assert performance_profile is not None
        values = [
            _format_list_size_mode_pair(size, totals, performance_profile)
            for size in LIST_SIZE_KEYS
        ]
        return (
            "Size of category list to scrape. "
            "Estimated runtime by list (interactive / headless): "
            + ", ".join(values)
            + "."
        )

    values = [
        f"{size.upper()} {format_list_size_count(totals.get(size))}"
        for size in LIST_SIZE_KEYS
    ]
    return (
        "Size of category list to scrape. "
        "Product counts by list (ETA unavailable: performance config or cache data is missing/invalid): "
        + ", ".join(values)
        + "."
    )
