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
        # TODO KAN-3 work out what data was doing and whether it's worth keeping
        # data = []
        
        num_products = 0
        
        for category in categories:
            category_data = self._get_category_data(category)
            
            if category_data is not None: self.file_handler.store_data(category_data) # TODO KAN-16 inject just this method instead of the whole file handler
            
            num_products += len(category_data)
            # if split_files_by_category:
            #     data.append({"name": category, "data": category_data})
            # else:
            #     data.extend(category_data)
            # data.extend(category_data)
        
        self.logger.log("Successfully scraped {0} products".format(num_products))
        # return data

    
    def _get_all_categories(self, list_size: ListSize) -> List[str]:
        # TODO KAN-5 do this properly
        # self.driver.get_page(self.base_url)
        # find button containing "Browse" => click
        # find div class = "category-list"
        # Find each <a> tag, get href
        
        ##########################################################################
        # # Wait for the products to load (you can adjust the wait time if needed)
        # wait = WebDriverWait(driver, 10)
        # wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "browseMenuDesktop")))
        
        # driver.find_element(By.CLASS_NAME, "browseMenuDesktop").click()
        
        # # Get the page source after waiting for the elements to load
        # page_source = driver.page_source
        # soup = BeautifulSoup(page_source, "html.parser")
        # products = soup.find_all("section", class_="item")
        testing_list = ["deli-chilled-meals"]
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


    def _get_category_data(self, category_url: str) -> List[str]:
        url = self.url + category_url

        try:
            self.logger.log("Getting page data for {0} - {1}".format(category_url, url))
            self.driver.get_page(url)
            
            data = self.driver.get_products(self._get_products_data)            
            return data        
        except Exception as e:
            msg = getattr(e, 'msg', None) or str(e) or repr(e)
            self.logger.error(f"{type(e).__name__}: {msg}")
            return
        # finally:
        #     self.driver.quit()
            
    def _get_products_data(self, products: List[str]) -> List[List[str]]:
        products_data = []
        self.logger.log("Reading product data for {0} products".format(len(products)))
        self.logger.debug("Reading product data for - {0}".format(products))
        # KAN-3 work out if I can get rid of the commented out code
        # add it to another ticket if need be
        
        for i in range(len(products)):
            try:
                self.logger.debug("Reading data for product - {0}".format(products[i]))
                text = self._get_product_string(i)
                
                # if not separate_columns:
                products_data.append(text.split('\n'))
                # product_name, price, price_per_unit = self._get_details_from_product_string(text)
                # product_group = _get_product_group(product)
                # product_name = _get_product_name(product_group)
                # price, price_per_unit = _get_product_price(product_group)
            
            except TimeoutError as e:
                msg = getattr(e, 'msg', None) or str(e) or repr(e)
                self.logger.debug(f"Timeout error!")
                self.logger.error(f"{type(e).__name__}: {msg}")
                self.driver.reload_page()
            
            except Exception as e:
                msg = getattr(e, 'msg', None) or str(e) or repr(e)
                self.logger.error(f"{type(e).__name__}: {msg}")
                # try:
                #     self.logger.log("Item skipped: %s" % product_name)
                # except:
                self.logger.log("Item skipped")
                # continue
            # products_data.append([product_name, price, price_per_unit])
        
        return products_data

    def _get_product_string(self, child_index: int) -> str:
        script = 'return document.querySelector("#search-content > div > shared-grid > div > div:nth-child(' + str(child_index+1) + ') > shared-product-tile > shared-web-component-wrapper > wc-product-tile").shadowRoot.querySelector("section > div")'
        text = self.driver.execute_script(script)
        return text
    
    # KAN-3 the methods below aren't currently used

    def _get_details_from_product_string(self, text: str) -> Tuple[str, str, str]:
        # print(text)
        rows = text.split('\n')
        price_regex = "/^\$([0-9])+\.[0-9][0-9]$/g"
        price_per_unit_regex = ""
        product_name = ""
        
        for row in rows:
            if re.search(price_regex, row):
                price = row
            elif re.search(price_per_unit_regex, row):
                price_per_unit = row
            else:
                product_name += row
        # product_name = rows[2]
        # price = rows[0]
        # price_per_unit = rows[1]
        return product_name, price, price_per_unit

    def _get_product_group(self, product: BeautifulSoup) -> any:
        # print(product, product.arguments)
        shadow_root = self._get_shadow_root(product)
        section = shadow_root.findChildren("section")
        # if (not section):
        #     print(product.findChildren())
        #     for child in product.children:
        #         print(child)
                
        product_tile_body = section.find("div", class_="product-tile-body")
        product_tile_content = product_tile_body.find("div", class_="product-tile-content")
        return product_tile_content.find("div", class_="product-tile-group")

    def _get_shadow_root(self, element: BeautifulSoup) -> str:
        shadow_root = self.driver.execute_script('return document.querySelector("#search-content > div > shared-grid > div > div:nth-child(1) > shared-product-tile > shared-web-component-wrapper > wc-product-tile").shadowRoot.querySelector("section > div")')
        # shadow_root = driver.execute_script('return arguments[0].shadowRoot', element)
        # return driver.execute_script('return arguments[0].innerHTML',shadow_root)
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