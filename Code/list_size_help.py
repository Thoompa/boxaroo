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
    headless: RuntimeProfile
    interactive: RuntimeProfile


PERFORMANCE_CONFIG_PATH = os.path.join("Config", "performance.json")
LIST_TOTALS_CACHE_PATH = os.path.join(
    "Data", "category_lists", "woolworths-category-lists.json"
)
LIST_SIZE_KEYS = tuple(size.name.lower() for size in ListSize)
_PERFORMANCE_MODES = tuple(PerformanceConfig.__annotations__)

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
            if isinstance(value, int) and value >= 0
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
        return None

    if not isinstance(raw_profile, dict):
        return None

    profiles: dict[str, RuntimeProfile] = {}
    for mode in _PERFORMANCE_MODES:
        profile = _validate_runtime_profile(raw_profile.get(mode))
        if profile is None:
            return None
        profiles[mode] = profile

    return profiles  # type: ignore[return-value]


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


def build_list_size_help(
    *,
    headless: bool = False,
    config_path: str = PERFORMANCE_CONFIG_PATH,
    cache_path: str = LIST_TOTALS_CACHE_PATH,
) -> str:
    totals = _load_list_product_totals(cache_path)
    performance_profile = load_performance_profile(config_path)

    if _eta_is_available(performance_profile, totals):
        mode: str = "headless" if headless else "interactive"
        mode_profile = performance_profile[mode]  # type: ignore[literal-required]
        values = [
            f"{size.upper()} {format_list_size_eta(totals.get(size), mode_profile)}"
            for size in LIST_SIZE_KEYS
        ]
        return (
            "Size of category list to scrape. "
            f"Estimated runtime by list ({mode} mode): " + ", ".join(values) + "."
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
