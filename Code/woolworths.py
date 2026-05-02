"""Woolworths supermarket adapter.

Ownership:
- Own Woolworths-specific URLs, DOM access, category discovery, and translation
    of browser payloads into Boxaroo data structures.
- Decide when to consult CategoryListService, while CategoryListService owns
    cache persistence and list-size selection rules.
- Delegate product field extraction to the injected product parser, which owns
    parsing rules for raw product text.

Non-ownership:
- Does not own application composition or WebDriver lifecycle.
- Does not own cross-category runtime orchestration.
"""

import os
import time
from typing import List

from Code.category_list_service import CategoryListService
from Code.contracts import (
    CategoryCount,
    CategoryData,
    CategoryListCache,
    IncompleteProductItem,
    ISuperMarket,
    ListSize,
    ProductsData,
    WebsiteCategory,
)
from Code.product_parser import IProductParser
from Code.file_handler import IFileHandler
from Code.logger import ILogger
from Code.web_driver import IWebDriver


class Woolworths(ISuperMarket):
    """Supermarket adapter for Woolworths category scraping and normalization."""

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
        default_cache_path = os.path.join(
            "Data", "category_lists", "woolworths-category-lists.json"
        )
        self.category_list_service = CategoryListService(
            default_cache_path, self.logger
        )

    def get_categories(
        self,
        list_size: ListSize = ListSize.FULL,
        refresh_category_lists: bool = False,
    ) -> List[str]:
        """Coordinator-facing category selection seam.

        This delegates to the existing adapter logic so Goal 1 can expose the
        future orchestration boundary without changing runtime behavior.
        """

        return self._get_all_categories(
            list_size, refresh_category_lists=refresh_category_lists
        )

    def get_category_data(self, category_name: str) -> CategoryData:
        """Coordinator-facing category scrape seam backed by existing logic."""

        return self._get_category_data(category_name)

    def _get_all_categories(
        self, list_size: ListSize, refresh_category_lists: bool = False
    ) -> List[str]:
        cached_lists = self.category_list_service.load()

        try:
            website_categories = self._get_supermarket_categories()
            website_names = [item["name"] for item in website_categories]
            selected_cached_categories = (
                self.category_list_service.select(cached_lists, list_size)
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
            self.category_list_service.save(refreshed_lists, website_names)
            return self.category_list_service.select(refreshed_lists, list_size)

        except Exception as e:
            msg = getattr(e, "msg", None) or str(e) or repr(e)
            self.logger.error(f"{type(e).__name__}: {msg}")
            self.logger.log(
                "Falling back to cached category lists (or empty if cache is missing)"
            )

            fallback_lists = (
                cached_lists or self.category_list_service.load_cached_lists()
            )
            return self.category_list_service.select(fallback_lists, list_size)

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

    def _get_supermarket_categories(self) -> List[WebsiteCategory]:
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
        self, categories: List[WebsiteCategory] | None = None
    ) -> CategoryListCache:
        categories = categories or self._get_supermarket_categories()

        category_counts: list[CategoryCount] = []
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
        return self.category_list_service.refresh(category_counts)

    def _dedupe_products(self, products: list[list[str]]) -> list[list[str]]:
        seen: set[tuple[str, ...]] = set()
        deduped: list[list[str]] = []

        for product in products:
            key = tuple(product)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(product)

        return deduped

    def _dedupe_incomplete_items(
        self, incomplete_items: list[IncompleteProductItem]
    ) -> list[IncompleteProductItem]:
        seen: set[tuple[str, tuple[str, ...]]] = set()
        deduped: list[IncompleteProductItem] = []

        for item in incomplete_items:
            name = str(item.get("name", ""))
            missing = item.get("missing", [])
            if not isinstance(missing, list):
                missing = []
            missing_key = tuple(str(field) for field in missing)
            key = (name, missing_key)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        return deduped

    def _get_category_data(self, category_url: str) -> CategoryData:
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

            products = self._dedupe_products(products)
            incomplete_items = self._dedupe_incomplete_items(incomplete_items)

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

    def _get_products_data(self, products: List[str]) -> ProductsData:
        products_data = []
        incomplete_items = []
        self.logger.log("Reading product data for {0} products".format(len(products)))
        self.logger.debug("Reading product data for - {0}".format(products))

        for i, product_text in enumerate(products):
            try:
                self.logger.debug("Reading data for product - {0}".format(product_text))
                parsed_product = self.product_parser.parse(product_text)

                product_name = parsed_product["name"]
                price = parsed_product["price"]
                unit_price = parsed_product["unit_price"]
                promotion = parsed_product["promotion"]
                missing_fields = parsed_product["missing_fields"]

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
            parsed["name"],
            parsed["price"],
            parsed["unit_price"],
            parsed["promotion"],
        ]
