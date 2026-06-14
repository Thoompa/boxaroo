"""Coles supermarket adapter.

Ownership:
- Own Coles-specific URLs, DOM access, category discovery, and translation
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
from Code.coles_category_data_normaliser import ColesCategoryDataNormaliser
from Code.coles_category_source import ColesCategorySource
from Code.product_parser import IProductParser
from Code.file_handler import IFileHandler
from Code.logger import ILogger
from Code.web_driver import IWebDriver


class Coles(ISuperMarket):
    """Supermarket adapter for Coles category scraping and normalization."""

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
        self.coles_product_container_class_names = [
            "product-tile-v2",
            "product-tile-group",
        ]
        self.driver = web_driver
        self.base_url = "https://www.coles.com.au"
        self.url = "https://www.coles.com.au/shop/browse/"
        default_cache_path = os.path.join(
            "Data", "category_lists", "coles-category-lists.json"
        )
        self.category_list_service = CategoryListService(
            default_cache_path, self.logger
        )
        self.category_source = ColesCategorySource(
            logger=self.logger,
            web_driver=self.driver,
            category_list_service=self.category_list_service,
            base_url=self.base_url,
            browse_url=self.url,
        )
        self.category_data_normaliser = ColesCategoryDataNormaliser(
            logger=self.logger,
            web_driver=self.driver,
            product_parser=self.product_parser,
            browse_url=self.url,
        )

    def get_categories(
        self,
        list_size: ListSize = ListSize.FULL,
        refresh_category_lists: bool = False,
    ) -> list[str]:
        return self.category_source.get_categories(
            list_size=list_size,
            refresh_category_lists=refresh_category_lists,
        )

    def get_category_data(self, category_name: str) -> CategoryData:
        return self.category_data_normaliser.get_category_data(category_name)
