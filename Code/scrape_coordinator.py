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

from Code.file_handler import IFileHandler
from Code.isupermarket import ISuperMarket
from Code.isupermarket import ListSize
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
        refresh_category_lists: bool = False,
    ) -> None:
        self.logger.log("Scraping supermarket categories")
        categories = self.supermarket.get_categories(
            list_size, refresh_category_lists=refresh_category_lists
        )

        total_products = 0
        for category in categories:
            try:
                category_data = self.supermarket.get_category_data(category)
            except Exception as exc:
                self.logger.error(f"Failed to scrape category '{category}': {exc}")
                continue

            if not isinstance(category_data, dict):
                self.logger.error(
                    f"Invalid category data for '{category}': expected dict, got "
                    f"{type(category_data).__name__}"
                )
                continue

            products = category_data.get("products")
            if not isinstance(products, list):
                self.logger.error(
                    f"Invalid category data for '{category}': expected 'products' "
                    f"to be a list, got {type(products).__name__}"
                )
                continue

            self.file_handler.store_data(products)
            total_products += len(products)

        self.logger.log(f"Successfully scraped {total_products} products")
