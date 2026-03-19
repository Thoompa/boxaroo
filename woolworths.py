import re
from typing import List, Tuple
from bs4 import BeautifulSoup

from file_handler import IFileHandler
from logger import ILogger
from isupermarket import ISuperMarket, ListSize
from web_driver import IWebDriver


class Woolworths(ISuperMarket):
    def __init__(self, file_handler: IFileHandler, logger: ILogger, web_driver: IWebDriver):
        self.file_handler = file_handler
        self.logger = logger
        self.woolworths_product_container_class_names = ["product-tile-v2", "product-tile-group"]
        self.driver = web_driver
        self.base_url = "https://www.woolworths.com.au"
        self.url = "https://www.woolworths.com.au/shop/browse/"


    def get_data(self, list_size: ListSize = ListSize.FULL) -> None:
        self.logger.debug("Getting Woolworths categories (list size - {0})".format(list_size))
        categories = self._get_all_categories(list_size)
        self.logger.log("Scraping Woolworths categories - {0}".format(categories))
        
        num_products = 0
        
        for category in categories:
            category_data = self._get_category_data(category)
            
            # TODO KAN-16 inject just this method instead of the whole file handler
            if category_data is not None:
                products = category_data.get('products', []) if isinstance(category_data, dict) else []
                self.file_handler.store_data(products)
                num_products += len(products)

        self.logger.log("Successfully scraped {0} products".format(num_products))

    
    def _get_all_categories(self, list_size: ListSize) -> List[str]:
        ##########################################################################
        # TODO KAN-5 do this properly
        # self.driver.get_page(self.base_url)
        # find button containing "Browse" => click
        # find div class = "category-list"
        # Find each <a> tag, get href
        
        # # Wait for the products to load (you can adjust the wait time if needed)
        # wait = WebDriverWait(driver, 10)
        # wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "browseMenuDesktop")))
        
        # driver.find_element(By.CLASS_NAME, "browseMenuDesktop").click()
        
        # # Get the page source after waiting for the elements to load
        # page_source = driver.page_source
        # soup = BeautifulSoup(page_source, "html.parser")
        # products = soup.find_all("section", class_="item")
        ##########################################################################
        testing_list = ["fruit-veg"]
        short_category_list = [
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
        ]
        full_category_list = [
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
        ]
        
        if list_size == ListSize.TESTING:
            return testing_list
        elif list_size == ListSize.SHORT:
            return short_category_list
        elif list_size == ListSize.FULL:
            return full_category_list


    def _get_category_data(self, category_url: str) -> dict:
        url = self.url + category_url

        try:
            self.logger.log("Getting page data for {0} - {1}".format(category_url, url))
            self.driver.get_page(url)

            category_total = self.driver.get_category_total_items()
            self.logger.log(f"{category_url} total count (page data): {category_total if category_total is not None else 'unknown'}")

            data_result = self.driver.get_products(self._get_products_data)
            products = data_result.get('products', []) if isinstance(data_result, dict) else data_result
            incomplete_items = data_result.get('incomplete_items', []) if isinstance(data_result, dict) else []
            page_stats = data_result.get('page_stats', []) if isinstance(data_result, dict) else []

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

            self.logger.log(f"Category {category_url}: expected {category_total}, scraped {scraped_count}, incomplete {incomplete_count}")

            for item in incomplete_items:
                self.logger.log(f"Incomplete product: name='{item.get('name', '[unknown]')}', missing={item.get('missing', [])}")

            return {
                'category': category_url,
                'total': category_total,
                'products': products,
                'incomplete_items': incomplete_items,
                'scraped': scraped_count,
                'incomplete': incomplete_count
            }
        except Exception as e:
            msg = getattr(e, 'msg', None) or str(e) or repr(e)
            self.logger.error(f"{type(e).__name__}: {msg}")
            return {'category': category_url, 'total': 0, 'products': [], 'incomplete_items': [], 'scraped': 0, 'incomplete': 0}
            
    def _get_products_data(self, products) -> dict:
        products_data = []
        incomplete_items = []
        self.logger.log("Reading product data for {0} products".format(len(products)))
        self.logger.debug("Reading product data for - {0}".format(products))

        for i, product_element in enumerate(products):
            try:
                self.logger.debug("Reading data for product - {0}".format(product_element))
                text = self._get_product_string_from_element(product_element)

                # Parse the product data into structured fields
                parsed_product = self._parse_product_data(text)
                if parsed_product:
                    product_name, price, unit_price, promotion = parsed_product

                    missing_fields = []
                    if not product_name:
                        missing_fields.append('name')
                    if not price:
                        missing_fields.append('price')
                    if not unit_price:
                        missing_fields.append('unit_price')

                    if not price and unit_price:
                        price = unit_price

                    if any([product_name, price, unit_price, promotion]):
                        products_data.append([product_name, price, unit_price, promotion])
                        self.logger.debug(f"Parsed product {i}: {[product_name, price, unit_price, promotion]}")

                        if missing_fields:
                            item_name = product_name if product_name else '[unknown]'
                            incomplete_items.append({'name': item_name, 'missing': missing_fields})
                            self.logger.debug(f"Marked incomplete product {i}: {item_name}, missing={missing_fields}")
                    else:
                        self.logger.debug(f"Skipped empty product data at index {i}")

            except TimeoutError as e:
                msg = getattr(e, 'msg', None) or str(e) or repr(e)
                self.logger.debug(f"Timeout error!")
                self.logger.error(f"{type(e).__name__}: {msg}")
                self.driver.reload_page()

            except Exception as e:
                msg = getattr(e, 'msg', None) or str(e) or repr(e)
                self.logger.error(f"{type(e).__name__}: {msg}")
                self.logger.log("Item skipped")

        return {'products': products_data, 'incomplete_items': incomplete_items}

    def _parse_product_data(self, text: str) -> List[str]:
        """Parse the raw product text into structured data fields."""
        if text is None:
            text = ""
        elif not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                text = ""

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        product_name = ""
        price = ""
        unit_price = ""
        promotion = ""
        # Remove common UI/clutter lines that are not product name
        blacklist = [
            'add to cart', 'save to list', 'promoted', 'new', 'out of stock',
            'sometimes available', 'compare', 'delisted', 'click to save'
        ]

        def is_price_line(value: str) -> bool:
            return bool(re.match(r"^\$\d+(\.\d{2})?$", value.strip()))

        def is_unit_price_line(value: str) -> bool:
            return bool(re.match(r"^\$.*\/.+$", value.strip()))

        def is_valid_name(value: str) -> bool:
            v = value.lower().strip()
            if any(x in v for x in blacklist):
                return False
            if value.startswith('$'):
                return False
            if 'for $' in v or 'save' in v or 'each' not in v and len(v) < 4:
                # keep name lines with decent length and non-promo semantics
                pass
            return bool(re.search(r"[a-zA-Z]", value))

        # price/unit/promo extraction
        for line in lines:
            if not price and is_price_line(line):
                price = line
            if not unit_price and is_unit_price_line(line):
                unit_price = line
            if not promotion and ('for $' in line.lower() or re.match(r"^\d+\s*for\s*\$", line.lower())):
                promotion = line

        def is_product_name_candidate(value: str) -> bool:
            v = value.strip()
            if not v or v.startswith('$'):
                return False
            if not re.search('[a-zA-Z]', v):
                return False
            low = v.lower()
            if any(x in low for x in blacklist):
                return False
            if 'for $' in low or re.match(r"^\d+\s*for\s*\$", low):
                return False
            if 'price' in low and len(low.split()) <= 4:
                return False
            if 'save' in low and '$' in low:
                return False
            if low.startswith('was ') or 'was $' in low:
                return False
            if len(v) < 6:
                return False
            return True

        # product name: first meaningful non-price line that is not UI text
        for line in lines:
            if is_product_name_candidate(line) and not is_price_line(line) and not is_unit_price_line(line):
                product_name = line
                break

        # fallback: last non-price non-blacklist line
        if not product_name:
            for line in reversed(lines):
                if is_valid_name(line) and not is_price_line(line) and not is_unit_price_line(line):
                    product_name = line
                    break

        return [product_name, price, unit_price, promotion]

    def _get_product_string_from_element(self, element) -> str:
        """Extract product text from a WebElement (wc-product-tile)"""
        try:
            if element is None:
                return ""

            text = ""
            try:
                text = element.text or ""
            except Exception:
                text = ""

            if isinstance(text, str) and text.strip():
                self.logger.debug(f"Element text: '{text[:200]}...'")
                return text.strip()

            # If no text, try to access shadow root
            shadow_script = '''
            var element = arguments[0];
            if (element && element.shadowRoot) {
                var section = element.shadowRoot.querySelector("section > div");
                return section ? section.textContent.trim() : "";
            }
            return "";
            '''
            text = self.driver.execute_script(shadow_script, element)

            if isinstance(text, str) and text.strip():
                self.logger.debug(f"Shadow root text: '{text[:200]}...'")
                return text.strip()

            # Very rarely element might itself be a string-like object
            if not isinstance(text, str):
                text = str(text)

            return text.strip()

        except Exception as e:
            self.logger.debug(f"Error extracting text from element: {e}")
            return ""

    def _get_product_string(self, child_index: int) -> str:
        # First, let's see what product tiles are actually on the page
        script = '''
        try {
            var tiles = document.querySelectorAll("wc-product-tile");
            if (tiles.length === 0) {
                return "NO_PRODUCT_TILES_FOUND";
            }
            if (''' + str(child_index) + ''' >= tiles.length) {
                return "INDEX_OUT_OF_BOUNDS_" + tiles.length;
            }
            var element = tiles[''' + str(child_index) + '''];
            return element.outerHTML;
        } catch (e) {
            return "ERROR: " + e.message;
        }
        '''
        html = self.driver.execute_script(script)
        self.logger.debug(f"Product {child_index} HTML: '{html[:200]}...'")  # Log first 200 chars
        
        # Parse the HTML to extract text content
        if html and not html.startswith("NO_") and not html.startswith("INDEX_") and not html.startswith("ERROR:"):
            try:
                soup = BeautifulSoup(html, 'html.parser')
                # Try to find text content in various ways
                text_content = soup.get_text(separator='\n', strip=True)
                self.logger.debug(f"Product {child_index} parsed text: '{text_content[:200]}...'")
                return text_content
            except Exception as e:
                self.logger.debug(f"Error parsing HTML for product {child_index}: {e}")
                return html
        else:
            return html
    
    def _get_details_from_product_string(self, text: str) -> Tuple[str, str, str]:
        rows = text.split('\n')
        price_regex = r"^\$([0-9])+\.[0-9][0-9]$"
        price_per_unit_regex = ""
        product_name = ""
        
        for row in rows:
            if re.search(price_regex, row):
                price = row
            elif re.search(price_per_unit_regex, row):
                price_per_unit = row
            else:
                product_name += row
        ##########################################################################
        # TODO KAN-20
        # product_name = rows[2]
        # price = rows[0]
        # price_per_unit = rows[1]
        ##########################################################################
        return product_name, price, price_per_unit

    def _get_product_group(self, product: BeautifulSoup) -> any:
        shadow_root = self._get_shadow_root(product)
        section = shadow_root.findChildren("section")
        ##########################################################################
        # TODO KAN-20
        # if (not section):
        #     print(product.findChildren())
        #     for child in product.children:
        #         print(child)
        ##########################################################################
                
        product_tile_body = section.find("div", class_="product-tile-body")
        product_tile_content = product_tile_body.find("div", class_="product-tile-content")
        return product_tile_content.find("div", class_="product-tile-group")

    def _get_shadow_root(self, element: BeautifulSoup) -> str:
        shadow_root = self.driver.execute_script('return document.querySelector("#search-content > div > shared-grid > div > div:nth-child(1) > shared-product-tile > shared-web-component-wrapper > wc-product-tile").shadowRoot.querySelector("section > div")')
        ##########################################################################
        # TODO KAN-20
        # shadow_root = driver.execute_script('return arguments[0].shadowRoot', element)
        # return driver.execute_script('return arguments[0].innerHTML',shadow_root)
        ##########################################################################
        return shadow_root

    def _get_product_name(self, product: BeautifulSoup) -> str:
        container = product.find("div", class_="product-title-container")
        shared_product_tile = container.find("shared-product-tile-title")
        return shared_product_tile.find("div", class_="product-tile-title").text.strip()

    def _get_product_price(self, product) -> Tuple[str, str]:
        container = product.find("div", class_="product-information-container")
        product_tile_prices_div = container.find("div", class_="product-tile-v2--prices")
        shared_product_tile_price = product_tile_prices_div.find("shared-product-tile-price")
        product_price_tile = shared_product_tile_price.find("div", "product-tile-price")
        
        primary = product_price_tile.find("div", "primary")
        price = primary.text.strip()
        
        secondary = product_price_tile.find("div", "secondary")
        price_per_unit = secondary.find("span", class_="price-per-cup").text.strip()
        
        return price, price_per_unit