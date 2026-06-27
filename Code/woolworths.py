"""Woolworths supermarket adapter.

Ownership:
- Own Woolworths-specific URLs, DOM access, category discovery, and translation
    of browser payloads into Boxaroo data structures.
- Decide when to consult CategoryListService, while CategoryListService owns
    cache persistence and list-size selection rules.
- Delegate product field extraction to the injected product parser, which owns
    parsing rules for raw product text.
"""

import os

from Code.category_list_service import CategoryListService
from Code.contracts import (
    CategoryData,
    ISuperMarket,
    ListSize,
)
from Code.woolworths_category_data_normaliser import WoolworthsCategoryDataNormaliser
from Code.woolworths_category_source import WoolworthsCategorySource
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
        self.category_source = WoolworthsCategorySource(
            logger=self.logger,
            web_driver=self.driver,
            category_list_service=self.category_list_service,
            base_url=self.base_url,
            browse_url=self.url,
        )
        self.category_data_normaliser = WoolworthsCategoryDataNormaliser(
            logger=self.logger,
            web_driver=self.driver,
            product_parser=self.product_parser,
            browse_url=self.url,
        )

    def get_categories(
        self,
        list_size: ListSize = ListSize.FULL,
        category: str | None = None,
        refresh_category_lists: bool = False,
    ) -> list[str]:
        return self.category_source.get_categories(
            list_size=list_size,
            category=category,
            refresh_category_lists=refresh_category_lists,
        )

    def get_category_data(self, category_name: str) -> CategoryData:
        return self.category_data_normaliser.get_category_data(category_name)
