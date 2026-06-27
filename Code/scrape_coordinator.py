"""Orchestration boundary for supermarket scraping.

Ownership for the coordinator layer:
- Ask a supermarket adapter for the selected categories for the current run.
- Iterate categories and invoke category-level scraping one category at a time.
- Apply cross-category policies such as progress reporting, retry policy, and
  failure handling.

Non-ownership:
- Application composition and WebDriver lifecycle remain in main.py.
- Supermarket-specific navigation, DOM extraction, cache refresh mechanics, and
  product parsing remain inside the supermarket adapter and its collaborators.

"""

from time import perf_counter

from Code.file_handler import IFileHandler
from Code.contracts import ISuperMarket, ListSize
from Code.logger import ILogger


class ScrapeCoordinator:
    """Runtime orchestration entry point for category-level scraping."""

    def __init__(
        self,
        supermarket: ISuperMarket,
        logger: ILogger,
        file_handler: IFileHandler,
    ) -> None:
        self.supermarket = supermarket
        self.logger = logger
        self.file_handler = file_handler

    def run(
        self,
        list_size: ListSize = ListSize.FULL,
        category: str | None = None,
        refresh_category_lists: bool = False,
    ) -> None:
        start_time = perf_counter()
        self.logger.log(f"Scraping {type(self.supermarket).__name__} categories")
        categories = self.supermarket.get_categories(
            list_size,
            category=category,
            refresh_category_lists=refresh_category_lists,
        )

        total_products = 0
        total_found = 0
        total_incomplete = 0
        categories_succeeded = 0
        categories_failed = 0

        for category in categories:
            try:
                category_data = self.supermarket.get_category_data(category)
            except Exception as exc:
                self.logger.error(
                    f"Failed to scrape category '{category}': {type(exc).__name__}: {exc}"
                )
                categories_failed += 1
                continue

            if not isinstance(category_data, dict):
                self.logger.error(
                    f"Invalid category data for '{category}': expected dict, got "
                    f"{type(category_data).__name__}; value={category_data!r}"
                )
                categories_failed += 1
                continue

            products = category_data.get("products")
            if not isinstance(products, list):
                self.logger.error(
                    f"Invalid category data for '{category}': expected 'products' "
                    f"to be a list, got {type(products).__name__}; value={products!r}; "
                    f"category_data={category_data!r}"
                )
                categories_failed += 1
                continue

            self.file_handler.store_data(products)
            total_products += len(products)
            categories_succeeded += 1

            category_total = category_data.get("total", 0)
            if isinstance(category_total, int) and category_total > 0:
                total_found += category_total
                if len(products) == 0:
                    self.logger.warning(
                        f"Category {category} returned found={category_total} but scraped=0"
                    )

            category_incomplete = category_data.get("incomplete", 0)
            if isinstance(category_incomplete, int):
                total_incomplete += category_incomplete

        elapsed_seconds = perf_counter() - start_time

        self.logger.log(f"Successfully scraped {total_products} products")
        self.logger.log(
            "Run summary: "
            f"categories_attempted={len(categories)} "
            f"categories_succeeded={categories_succeeded} "
            f"categories_failed={categories_failed} "
            f"products_found={total_found} "
            f"products_scraped={total_products} "
            f"incomplete_products={total_incomplete} "
            f"took={elapsed_seconds:.2f}s"
        )
