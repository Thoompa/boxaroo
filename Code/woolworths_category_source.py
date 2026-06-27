import time
from collections.abc import Callable

from Code.contracts import (
    CategoryCount,
    CategoryListCache,
    ICategoryListService,
    ListSize,
    WebsiteCategory,
)
from Code.logger import ILogger
from Code.web_driver import IWebDriver


class WoolworthsCategorySource:
    """Handles Woolworths category discovery and cache refresh policy."""

    def __init__(
        self,
        logger: ILogger,
        web_driver: IWebDriver,
        category_list_service: ICategoryListService,
        base_url: str,
        browse_url: str,
    ):
        self.logger = logger
        self.web_driver = web_driver
        self.category_list_service = category_list_service
        self.base_url = base_url
        self.browse_url = browse_url

    def get_categories(
        self,
        list_size: ListSize,
        category: str | None = None,
        refresh_category_lists: bool = False,
        category_discovery: Callable[[], list[WebsiteCategory]] | None = None,
    ) -> list[str]:
        # Keep current cache in memory for the happy path and for fallback recovery.
        cached_lists = self.category_list_service.load()
        discover_categories = category_discovery or self._get_supermarket_categories

        try:
            # Always attempt a live discovery first so we can validate cache freshness.
            website_categories = discover_categories()
            website_category_names = (
                [item["name"] for item in website_categories]
                if website_categories
                else []
            )
            selected_cached_categories = (
                self.category_list_service.select(cached_lists, list_size)
                if cached_lists
                else []
            )

            # Category override path: validate against available category names and
            # return the single requested category without list-size refresh/counting.
            if category is not None:
                available_categories = (
                    website_category_names
                    or (cached_lists.get("full", []) if cached_lists else [])
                    or selected_cached_categories
                )
                return self._select_requested_category_or_exit(
                    selected_categories=[],
                    requested_category=category,
                    available_categories=available_categories,
                )

            # Fast path gate:
            # - user did not force refresh
            # - we have cached categories for this list size
            # - cached categories still exist on the website
            # - for TESTING runs, each cached category still reports products
            # If all checks pass, we skip recounting categories from the site.
            if (
                not refresh_category_lists
                and selected_cached_categories
                and self._selected_categories_match_site(
                    selected_cached_categories, website_category_names
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
                self.logger.log(
                    f"Selected {len(selected_cached_categories)} categories: {selected_cached_categories}"
                )
                # Build a lookup source for --category validation in priority order:
                # 1) freshly discovered site names, 2) cached full list, 3) selected list.
                # This keeps validation resilient when one source is temporarily empty.
                available_categories = (
                    website_category_names
                    or (cached_lists.get("full", []) if cached_lists else [])
                    or selected_cached_categories
                )
                return self._select_requested_category_or_exit(
                    selected_cached_categories,
                    category,
                    available_categories,
                )

            # Slow path: rebuild category lists from live category counts and persist them.
            refreshed_lists = self._refresh_category_lists_from_site(website_categories)
            if not website_category_names:
                website_category_names = refreshed_lists.get("full", [])
            self.category_list_service.save(refreshed_lists, website_category_names)
            selected_categories = self.category_list_service.select(
                refreshed_lists, list_size
            )
            available_categories = (
                website_category_names
                or refreshed_lists.get("full", [])
                or selected_categories
            )
            return self._select_requested_category_or_exit(
                selected_categories,
                category,
                available_categories,
            )

        except Exception as e:
            # Recovery path: log discovery/refresh failure and use cached lists if available.
            msg = getattr(e, "msg", None) or str(e) or repr(e)
            self.logger.error(f"{type(e).__name__}: {msg}")
            self.logger.log(
                "Falling back to cached category lists (or empty if cache is missing)"
            )

            fallback_lists = (
                cached_lists or self.category_list_service.load_cached_lists()
            )
            selected_categories = self.category_list_service.select(
                fallback_lists, list_size
            )
            available_categories = fallback_lists.get("full", []) or selected_categories
            return self._select_requested_category_or_exit(
                selected_categories,
                category,
                available_categories,
            )

    def _select_requested_category_or_exit(
        self,
        selected_categories: list[str],
        requested_category: str | None,
        available_categories: list[str],
    ) -> list[str]:
        if requested_category is None:
            return selected_categories

        normalized_requested = requested_category.strip().lower()
        available_lookup = {
            name.strip().lower(): name
            for name in available_categories
            if isinstance(name, str) and name.strip()
        }

        if normalized_requested in available_lookup:
            return [available_lookup[normalized_requested]]

        self.logger.error(
            f"Category '{requested_category}' was not found in available Woolworths categories"
        )
        raise SystemExit(1)

    def _selected_categories_match_site(
        self, selected_categories: list[str], website_names: list[str]
    ) -> bool:
        return set(selected_categories).issubset(set(website_names))

    def _selected_categories_have_products(
        self, selected_categories: list[str]
    ) -> bool:
        for name in selected_categories:
            self.web_driver.get_page(self.browse_url + name)
            count = self.web_driver.get_category_total_items()
            if not isinstance(count, int) or count <= 0:
                self.logger.log(
                    f"Refreshing category lists because '{name}' has no products"
                )
                return False
        return True

    def _get_supermarket_categories(self) -> list[WebsiteCategory]:
        self.web_driver.get_page(self.base_url)

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

                var path = href.split('?')[0].split('#')[0];
                if (path.endsWith('/')) {
                    path = path.slice(0, -1);
                }

                var name = path.split('/').pop();
                if (!name || seen[name]) {
                    continue;
                }

                seen[name] = true;
                categories.push({ name: name, href: href });
            }
            return categories;
        } catch (e) {
            return [];
        }
        """

        self.web_driver.execute_script(open_menu_script)

        categories = []
        for _ in range(6):
            categories = self.web_driver.execute_script(extract_menu_categories_script)
            if isinstance(categories, list) and len(categories) > 0:
                break
            time.sleep(0.5)

        if not isinstance(categories, list):
            return []

        clean: list[WebsiteCategory] = []
        for item in categories:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            href = item.get("href")
            if isinstance(name, str) and name.strip() and isinstance(href, str):
                if href.startswith("/"):
                    href = self.base_url.rstrip("/") + href
                clean.append({"name": name.strip(), "href": href})
        return clean

    def _refresh_category_lists_from_site(
        self, categories: list[WebsiteCategory] | None = None
    ) -> CategoryListCache:
        # Retry discovery up to 2 times to allow for transient page load failures
        max_discovery_attempts = 2
        for attempt in range(max_discovery_attempts):
            if not categories or len(categories) == 0:
                if attempt > 0:
                    self.logger.log(
                        f"Retrying category discovery (attempt {attempt + 1}/{max_discovery_attempts})"
                    )
                categories = self._get_supermarket_categories()

            if categories and len(categories) > 0:
                break

            if attempt < max_discovery_attempts - 1:
                time.sleep(0.5)

        # If discovery failed after all retries, raise to trigger cache fallback
        if not categories or len(categories) == 0:
            raise RuntimeError("No categories discovered from site after retries")

        category_counts: list[CategoryCount] = []
        for item in categories:
            name = item.get("name")
            if not name:
                continue

            category_url = self.browse_url + name
            self.web_driver.get_page(category_url)
            count = self.web_driver.get_category_total_items()
            count = count if isinstance(count, int) and count >= 0 else 0
            if count > 0:
                category_counts.append({"name": name, "count": count})
        return self.category_list_service.refresh(category_counts)
