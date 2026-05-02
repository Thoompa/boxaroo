from Code.contracts import CategoryData, IncompleteProductItem, ProductsData
from Code.logger import ILogger
from Code.product_parser import IProductParser
from Code.web_driver import IWebDriver


class WoolworthsCategoryDataNormaliser:
    """Normalises Woolworths category page payloads into Boxaroo contracts."""

    def __init__(
        self,
        logger: ILogger,
        web_driver: IWebDriver,
        product_parser: IProductParser,
        browse_url: str,
    ):
        self.logger = logger
        self.web_driver = web_driver
        self.product_parser = product_parser
        self.browse_url = browse_url

    def dedupe_products(self, products: list[list[str]]) -> list[list[str]]:
        seen: set[tuple[str, ...]] = set()
        deduped: list[list[str]] = []

        for product in products:
            key = tuple(product)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(product)

        return deduped

    def dedupe_incomplete_items(
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

    def get_category_data(self, category_url: str) -> CategoryData:
        url = self.browse_url + category_url

        try:
            self.logger.log("Getting page data for {0} - {1}".format(category_url, url))
            self.web_driver.get_page(url)

            category_total = self.web_driver.get_category_total_items()
            self.logger.log(
                f"{category_url} total count (page data): {category_total if category_total is not None else 'unknown'}"
            )

            data_result = self.web_driver.get_products(self.get_products_data)
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

            products = self.dedupe_products(products)
            incomplete_items = self.dedupe_incomplete_items(incomplete_items)

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

    def get_products_data(self, products: list[str]) -> ProductsData:
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
