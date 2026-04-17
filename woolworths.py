import json
import os
import time
from typing import List

from product_parser import IProductParser
from file_handler import IFileHandler
from logger import ILogger
from isupermarket import ISuperMarket, ListSize
from web_driver import IWebDriver


class Woolworths(ISuperMarket):
    def __init__(
        self,
        file_handler: IFileHandler,
        logger: ILogger,
        web_driver: IWebDriver,
        product_parser: IProductParser,
    ):
        self.file_handler = file_handler
        self.logger = logger
        self.product_parser = product_parser
        self.woolworths_product_container_class_names = [
            "product-tile-v2",
            "product-tile-group",
        ]
        self.driver = web_driver
        self.base_url = "https://www.woolworths.com.au"
        self.url = "https://www.woolworths.com.au/shop/browse/"
        self.category_lists_cache_path = os.path.join(
            "Data", "category_lists", "woolworths-category-lists.json"
        )

    def get_data(
        self,
        list_size: ListSize = ListSize.FULL,
        refresh_category_lists: bool = False,
    ) -> None:
        self.logger.debug(
            "Getting Woolworths categories (list size - {0})".format(list_size)
        )
        categories = self._get_all_categories(
            list_size, refresh_category_lists=refresh_category_lists
        )
        self.logger.log("Scraping Woolworths categories - {0}".format(categories))

        num_products = 0

        for category in categories:
            category_data = self._get_category_data(category)

            if category_data is not None:
                products = (
                    category_data.get("products", [])
                    if isinstance(category_data, dict)
                    else []
                )
                self.file_handler.store_data(products)
                num_products += len(products)

        self.logger.log("Successfully scraped {0} products".format(num_products))

    def _get_all_categories(
        self, list_size: ListSize, refresh_category_lists: bool = False
    ) -> List[str]:
        cached_lists = self._load_category_lists_cache()

        try:
            website_categories = self._get_supermarket_categories()
            website_names = [item["name"] for item in website_categories]
            selected_cached_categories = (
                self._get_categories_for_size(cached_lists, list_size)
                if cached_lists
                else []
            )

            if (
                not refresh_category_lists
                and selected_cached_categories
                and self._selected_categories_match_site(
                    selected_cached_categories, website_names
                )
                and (
                    list_size != ListSize.TESTING
                    or self._selected_categories_have_products(
                        selected_cached_categories
                    )
                )
            ):
                self.logger.log(
                    "Using cached category lists (selected categories match website)"
                )
                return selected_cached_categories

            refreshed_lists = self._refresh_category_lists_from_site(website_categories)
            self._save_category_lists_cache(refreshed_lists, website_names)
            return self._get_categories_for_size(refreshed_lists, list_size)

        except Exception as e:
            msg = getattr(e, "msg", None) or str(e) or repr(e)
            self.logger.error(f"{type(e).__name__}: {msg}")
            self.logger.log("Falling back to cached/default category lists")

            fallback_lists = cached_lists or self._get_default_category_lists()
            return self._get_categories_for_size(fallback_lists, list_size)

    def _get_default_category_lists(self) -> dict:
        return {
            "testing": ["fruit-veg"],
            "short": [
                "fruit-veg",
                "lunch-box",
                "poultry-meat-seafood",
                "bakery",
                "deli-chilled-meals",
                "dairy-eggs-fridge",
                "pantry",
                "snacks-confectionery",
                "freezer",
                "drinks",
                "liquor",
            ],
            "medium": [
                "fruit-veg",
                "lunch-box",
                "poultry-meat-seafood",
                "bakery",
                "deli-chilled-meals",
                "dairy-eggs-fridge",
                "pantry",
                "snacks-confectionery",
                "freezer",
                "drinks",
                "liquor",
            ],
            "long": [
                "fruit-veg",
                "lunch-box",
                "poultry-meat-seafood",
                "bakery",
                "deli-chilled-meals",
                "dairy-eggs-fridge",
                "pantry",
                "snacks-confectionery",
                "freezer",
                "drinks",
                "liquor",
                "health-wellness",
                "beauty-personal-care",
                "baby",
                "cleaning-maintenance",
                "pet",
                "home-lifestyle",
            ],
            "full": [
                "fruit-veg",
                "lunch-box",
                "poultry-meat-seafood",
                "bakery",
                "deli-chilled-meals",
                "dairy-eggs-fridge",
                "pantry",
                "snacks-confectionery",
                "freezer",
                "drinks",
                "liquor",
                "health-wellness",
                "beauty-personal-care",
                "baby",
                "cleaning-maintenance",
                "pet",
                "home-lifestyle",
            ],
        }

    def _get_categories_for_size(
        self, category_lists: dict, list_size: ListSize
    ) -> List[str]:
        if list_size == ListSize.TESTING:
            return category_lists.get("testing", [])
        if list_size == ListSize.SHORT:
            return category_lists.get("short", [])
        if list_size == ListSize.MEDIUM:
            return category_lists.get("medium", [])
        if list_size == ListSize.LONG:
            return category_lists.get("long", [])
        return category_lists.get("full", [])

    def _ensure_extended_lists(self, cached: dict) -> dict:
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

    def _selected_categories_match_site(
        self, selected_categories: List[str], website_names: List[str]
    ) -> bool:
        return set(selected_categories).issubset(set(website_names))

    def _selected_categories_have_products(
        self, selected_categories: List[str]
    ) -> bool:
        for name in selected_categories:
            self.driver.get_page(self.url + name)
            count = self.driver.get_category_total_items()
            if not isinstance(count, int) or count <= 0:
                self.logger.log(
                    f"Refreshing category lists because '{name}' has no products"
                )
                return False
        return True

    def _load_category_lists_cache(self) -> dict | None:
        if not os.path.exists(self.category_lists_cache_path):
            return None

        try:
            with open(self.category_lists_cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)

            if not isinstance(cached, dict):
                return None

            for key in ["testing", "short", "full"]:
                if key not in cached or not isinstance(cached.get(key), list):
                    return None
            return self._ensure_extended_lists(cached)
        except Exception:
            return None

    def _save_category_lists_cache(
        self, category_lists: dict, category_names: List[str]
    ) -> None:
        cache_data = {
            "supermarket_categories": category_names,
            "testing": category_lists.get("testing", []),
            "short": category_lists.get("short", []),
            "medium": category_lists.get("medium", []),
            "long": category_lists.get("long", []),
            "full": category_lists.get("full", []),
            "list_product_totals": category_lists.get("list_product_totals", {}),
            "category_product_totals": category_lists.get(
                "category_product_totals", {}
            ),
        }

        os.makedirs(os.path.dirname(self.category_lists_cache_path), exist_ok=True)
        with open(self.category_lists_cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

    def _get_supermarket_categories(self) -> List[dict]:
        self.driver.get_page(self.base_url)

        open_menu_script = """
        try {
            function normText(el) {
                return ((el && (el.innerText || el.textContent || el.getAttribute('aria-label'))) || '')
                    .toLowerCase()
                    .trim();
            }

            var controls = Array.from(document.querySelectorAll('button, a, [role="button"], [aria-label]'));
            var browseControl = controls.find(function (el) {
                var t = normText(el);
                return t === 'browse products' || t.indexOf('browse products') !== -1;
            });

            if (browseControl && typeof browseControl.click === 'function') {
                browseControl.click();
                return true;
            }

            return false;
        } catch (e) {
            return false;
        }
        """

        extract_menu_categories_script = """
        try {
            var links = document.querySelectorAll(
                'a.item.ng-star-inserted[href^="/shop/browse/"], a.item[href^="/shop/browse/"]'
            );
            var seen = {};
            var categories = [];
            for (var i = 0; i < links.length; i++) {
                var href = links[i].getAttribute('href') || '';
                if (!href) {
                    continue;
                }

                var fullHref = href;
                if (href.startsWith('/')) {
                    fullHref = 'https://www.woolworths.com.au' + href;
                }

                var path = fullHref.split('?')[0].split('#')[0];
                if (path.endsWith('/')) {
                    path = path.slice(0, -1);
                }

                var name = path.split('/').pop();
                if (!name || seen[name]) {
                    continue;
                }

                seen[name] = true;
                categories.push({ name: name, href: fullHref });
            }
            return categories;
        } catch (e) {
            return [];
        }
        """

        self.driver.execute_script(open_menu_script)

        categories = []
        for _ in range(6):
            categories = self.driver.execute_script(extract_menu_categories_script)
            if isinstance(categories, list) and len(categories) > 0:
                break
            time.sleep(0.5)

        if not isinstance(categories, list):
            return []

        clean = []
        for item in categories:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            href = item.get("href")
            if isinstance(name, str) and name.strip() and isinstance(href, str):
                clean.append({"name": name.strip(), "href": href})
        return clean

    def _refresh_category_lists_from_site(
        self, categories: List[dict] | None = None
    ) -> dict:
        categories = categories or self._get_supermarket_categories()

        category_counts = []
        for item in categories:
            name = item.get("name")
            if not name:
                continue

            category_url = self.url + name
            self.driver.get_page(category_url)
            count = self.driver.get_category_total_items()
            count = count if isinstance(count, int) and count >= 0 else 0
            if count > 0:
                category_counts.append({"name": name, "count": count})

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

        list_product_totals = {
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

    def _get_category_data(self, category_url: str) -> dict:
        url = self.url + category_url

        try:
            self.logger.log("Getting page data for {0} - {1}".format(category_url, url))
            self.driver.get_page(url)

            category_total = self.driver.get_category_total_items()
            self.logger.log(
                f"{category_url} total count (page data): {category_total if category_total is not None else 'unknown'}"
            )

            data_result = self.driver.get_products(self._get_products_data)
            products = (
                data_result.get("products", [])
                if isinstance(data_result, dict)
                else data_result
            )
            incomplete_items = (
                data_result.get("incomplete_items", [])
                if isinstance(data_result, dict)
                else []
            )
            page_stats = (
                data_result.get("page_stats", [])
                if isinstance(data_result, dict)
                else []
            )

            for page_info in page_stats:
                self.logger.log(
                    f"Category {category_url} - page {page_info.get('page')} : "
                    f"tiles={page_info.get('product_tiles')} scraped={page_info.get('scraped')} "
                    f"incomplete={page_info.get('incomplete')}"
                )

            scraped_count = len(products)
            incomplete_count = len(incomplete_items)
            if category_total is None:
                category_total = scraped_count

            self.logger.log(
                f"Category {category_url}: expected {category_total}, scraped {scraped_count}, incomplete {incomplete_count}"
            )

            for item in incomplete_items:
                self.logger.log(
                    f"Incomplete product: name='{item.get('name', '[unknown]')}', missing={item.get('missing', [])}"
                )

            return {
                "category": category_url,
                "total": category_total,
                "products": products,
                "incomplete_items": incomplete_items,
                "scraped": scraped_count,
                "incomplete": incomplete_count,
            }
        except Exception as e:
            msg = getattr(e, "msg", None) or str(e) or repr(e)
            self.logger.error(f"{type(e).__name__}: {msg}")
            return {
                "category": category_url,
                "total": 0,
                "products": [],
                "incomplete_items": [],
                "scraped": 0,
                "incomplete": 0,
            }

    def _get_products_data(self, products: List[str]) -> dict:
        products_data = []
        incomplete_items = []
        self.logger.log("Reading product data for {0} products".format(len(products)))
        self.logger.debug("Reading product data for - {0}".format(products))

        for i, product_text in enumerate(products):
            try:
                self.logger.debug("Reading data for product - {0}".format(product_text))
                parsed_product = self.product_parser.parse(product_text)

                product_name = parsed_product.get("name", "")
                price = parsed_product.get("price", "")
                unit_price = parsed_product.get("unit_price", "")
                promotion = parsed_product.get("promotion", "")
                missing_fields = parsed_product.get("missing_fields", [])

                if not price and unit_price:
                    price = unit_price

                if any([product_name, price, unit_price, promotion]):
                    products_data.append([product_name, price, unit_price, promotion])
                    self.logger.debug(
                        f"Parsed product {i}: {[product_name, price, unit_price, promotion]}"
                    )

                    if missing_fields:
                        item_name = product_name if product_name else "[unknown]"
                        incomplete_items.append(
                            {"name": item_name, "missing": missing_fields}
                        )
                        self.logger.debug(
                            f"Marked incomplete product {i}: {item_name}, missing={missing_fields}"
                        )
                else:
                    self.logger.debug(f"Skipped empty product data at index {i}")

            except Exception as e:
                msg = getattr(e, "msg", None) or str(e) or repr(e)
                self.logger.error(f"{type(e).__name__}: {msg}")
                self.logger.log("Item skipped")

        return {"products": products_data, "incomplete_items": incomplete_items}

    def _parse_product_data(self, text: str) -> List[str]:
        """Backwards-compatible wrapper around the injected product parser."""
        parsed = self.product_parser.parse(text)
        return [
            parsed.get("name", ""),
            parsed.get("price", ""),
            parsed.get("unit_price", ""),
            parsed.get("promotion", ""),
        ]
