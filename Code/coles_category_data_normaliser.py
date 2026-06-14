from Code.contracts import CategoryData, IncompleteProductItem, ProductsData
from Code.logger import ILogger
from Code.product_parser import IProductParser
from Code.web_driver import IWebDriver
from time import perf_counter


class ColesCategoryDataNormaliser:
    """Normalises Coles category page payloads into Boxaroo contracts."""

    GAP_WARNING_THRESHOLD = 0.5

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

    def get_category_data(self, category_name: str) -> CategoryData:
        url = self.browse_url + category_name
        start_time = perf_counter()

        try:
            self.logger.log(
                "Getting page data for {0} - {1}".format(category_name, url)
            )
            self.web_driver.get_page(url)

            category_total = self.web_driver.get_category_total_items()
            self.logger.log(
                f"{category_name} total count (page data): {category_total if category_total is not None else 'unknown'}"
            )

            data_result = self.web_driver.get_products(
                self._get_products_data, category_name=category_name
            )
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
                    f"Category {category_name} - page {page_info.get('page')} : "
                    f"tiles={page_info.get('product_tiles')} scraped={page_info.get('scraped')} "
                    f"incomplete={page_info.get('incomplete')}"
                )
                self.logger.log(
                    f"Category {category_name} - page {page_info.get('page')} extraction_failures="
                    f"{page_info.get('extraction_failures', 0)}"
                )

            scraped_count = len(products)
            incomplete_count = len(incomplete_items)
            if category_total is None:
                category_total = scraped_count

            self.logger.log(
                f"Category {category_name}: expected {category_total}, scraped {scraped_count}, incomplete {incomplete_count}"
            )

            elapsed_seconds = perf_counter() - start_time
            self.logger.log(
                f"Category {category_name} summary: found={category_total} scraped={scraped_count} "
                f"incomplete={incomplete_count} took={elapsed_seconds:.2f}s"
            )

            if category_total > 0:
                gap_ratio = (category_total - scraped_count) / category_total
                if gap_ratio >= self.GAP_WARNING_THRESHOLD:
                    self.logger.warning(
                        f"Category {category_name} scrape gap warning: found={category_total} scraped={scraped_count} "
                        f"gap={gap_ratio:.2%}"
                    )

            for item in incomplete_items:
                self.logger.log(
                    f"Incomplete product: name='{item.get('name', '[unknown]')}', missing={item.get('missing', [])}"
                )

            return {
                "category": category_name,
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
                "category": category_name,
                "total": 0,
                "products": [],
                "incomplete_items": [],
                "scraped": 0,
                "incomplete": 0,
            }

    def _get_products_data(
        self, products: list[str], page_number: int | None = None
    ) -> ProductsData:
        products_data = []
        incomplete_items = []
        if page_number is not None:
            self.logger.log(
                f"Reading product data for page {page_number} with {len(products)} products"
            )
        else:
            self.logger.log(
                "Reading product data for {0} products".format(len(products))
            )
        self.logger.debug("Reading product data for - {0}".format(products))

        for i, product_text in enumerate(products):
            try:
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
            normalised_missing = [str(field) for field in missing]
            normalised_item: IncompleteProductItem = {
                "name": name,
                "missing": normalised_missing,
            }
            missing_key = tuple(normalised_missing)
            key = (name, missing_key)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(normalised_item)

        return deduped
