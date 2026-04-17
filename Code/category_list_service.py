import json
import os
from typing import TypedDict, cast

from Code.isupermarket import ListSize
from Code.logger import ILogger


class CategoryCount(TypedDict):
    name: str
    count: int


class ListProductTotals(TypedDict):
    testing: int
    short: int
    medium: int
    long: int
    full: int


class CategoryListCache(TypedDict, total=False):
    testing: list[str]
    short: list[str]
    medium: list[str]
    long: list[str]
    full: list[str]
    supermarket_categories: list[str]
    list_product_totals: ListProductTotals
    category_product_totals: dict[str, int]


class CategoryListService:
    def __init__(self, cache_path: str, logger: ILogger):
        self.cache_path = cache_path
        self.logger = logger

    def load(self) -> CategoryListCache | None:
        if not os.path.exists(self.cache_path):
            return None

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                cached_raw = json.load(f)

            if not isinstance(cached_raw, dict):
                return None

            cached = cast(CategoryListCache, cached_raw)

            for key in ["testing", "short", "full"]:
                if key not in cached or not isinstance(cached.get(key), list):
                    return None

            return self._ensure_extended_lists(cached)
        except Exception:
            return None

    def save(
        self, category_lists: CategoryListCache, category_names: list[str]
    ) -> None:
        saved_totals = self._normalized_list_product_totals(
            category_lists.get("list_product_totals")
        )
        cache_data = {
            "supermarket_categories": category_names,
            "testing": category_lists.get("testing", []),
            "short": category_lists.get("short", []),
            "medium": category_lists.get("medium", []),
            "long": category_lists.get("long", []),
            "full": category_lists.get("full", []),
            "list_product_totals": saved_totals,
            "category_product_totals": category_lists.get(
                "category_product_totals", {}
            ),
        }

        cache_dir = os.path.dirname(self.cache_path)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

    def _normalized_list_product_totals(
        self, list_product_totals: object
    ) -> ListProductTotals:
        if not isinstance(list_product_totals, dict):
            list_product_totals = {}

        testing = list_product_totals.get("testing", 0)
        short = list_product_totals.get("short", 0)
        medium = list_product_totals.get("medium", 0)
        long = list_product_totals.get("long", 0)
        full = list_product_totals.get("full", 0)

        return {
            "testing": testing if isinstance(testing, int) else 0,
            "short": short if isinstance(short, int) else 0,
            "medium": medium if isinstance(medium, int) else 0,
            "long": long if isinstance(long, int) else 0,
            "full": full if isinstance(full, int) else 0,
        }

    def refresh(self, category_counts: list[CategoryCount]) -> CategoryListCache:
        if not category_counts:
            return {
                "testing": [],
                "short": [],
                "medium": [],
                "long": [],
                "full": [],
                "list_product_totals": {
                    "testing": 0,
                    "short": 0,
                    "medium": 0,
                    "long": 0,
                    "full": 0,
                },
                "category_product_totals": {},
            }

        testing = [min(category_counts, key=lambda x: (x["count"], x["name"]))["name"]]
        short = sorted([x["name"] for x in category_counts if x["count"] < 1000])
        medium = sorted([x["name"] for x in category_counts if x["count"] < 1800])
        long = sorted([x["name"] for x in category_counts if x["count"] < 10000])
        full = sorted([x["name"] for x in category_counts])

        count_map = {x["name"]: x["count"] for x in category_counts}

        list_product_totals: ListProductTotals = {
            "testing": sum(count_map.get(name, 0) for name in testing),
            "short": sum(count_map.get(name, 0) for name in short),
            "medium": sum(count_map.get(name, 0) for name in medium),
            "long": sum(count_map.get(name, 0) for name in long),
            "full": sum(count_map.get(name, 0) for name in full),
        }

        return {
            "testing": testing,
            "short": short,
            "medium": medium,
            "long": long,
            "full": full,
            "list_product_totals": list_product_totals,
            "category_product_totals": count_map,
        }

    def select(
        self, category_lists: CategoryListCache, list_size: ListSize
    ) -> list[str]:
        if list_size == ListSize.TESTING:
            return category_lists.get("testing", [])
        if list_size == ListSize.SHORT:
            return category_lists.get("short", [])
        if list_size == ListSize.MEDIUM:
            return category_lists.get("medium", [])
        if list_size == ListSize.LONG:
            return category_lists.get("long", [])
        return category_lists.get("full", [])

    def load_cached_lists(self) -> CategoryListCache:
        loaded = self.load()
        if loaded is None:
            self.logger.error(
                f"No usable category list cache available at {self.cache_path} - cannot provide fallback lists"
            )
            return {}
        return loaded

    def _ensure_extended_lists(self, cached: CategoryListCache) -> CategoryListCache:
        category_totals = cached.get("category_product_totals", {})
        full = cached.get("full", [])
        short = cached.get("short", [])

        if not isinstance(cached.get("medium"), list):
            if isinstance(category_totals, dict) and category_totals:
                cached["medium"] = sorted(
                    [
                        name
                        for name in full
                        if isinstance(category_totals.get(name), int)
                        and category_totals.get(name, 0) < 1800
                    ]
                )
            else:
                cached["medium"] = short

        if not isinstance(cached.get("long"), list):
            if isinstance(category_totals, dict) and category_totals:
                cached["long"] = sorted(
                    [
                        name
                        for name in full
                        if isinstance(category_totals.get(name), int)
                        and category_totals.get(name, 0) < 10000
                    ]
                )
            else:
                cached["long"] = full

        return cached
