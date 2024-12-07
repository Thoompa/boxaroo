from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from web_driver import get_web_driver
import re
from enum import Enum


class Categories(Enum):
    TESTING = 1
    SHORT = 2
    FULL = 3


# TODO make Woolworths implement a Supermarket interface
class Woolworths:
    def __init__(self, file_handler, logger, run_headless, separate_columns) -> None:
        self.file_handler = file_handler
        self.logger = logger
        self.separate_columns = separate_columns
        self.woolworths_product_container_class_names = ["product-tile-v2", "product-tile-group"]
        self.driver = None
        self.headless = run_headless


    def get_data(self):
        woolworths_url = "https://www.woolworths.com.au/shop/browse/"
        categories = self.get_all_categories(Categories.FULL)
        # data = []
        
        # TODO make logger log to a file
        
        for category in categories:
            category_data = self.get_category_data(woolworths_url, category, self.separate_columns)
            
            self.file_handler.store_data(category_data)
            
            # if split_files_by_category:
            #     data.append({"name": category, "data": category_data})
            # else:
            #     data.extend(category_data)
            # data.extend(category_data)
        
        # return data

    
    def get_all_categories(self, list_size):
        # TODO do this properly
        # driver = get_web_driver()
        # driver.get(url)
        
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
            "halloween",
            "winter",
            "summer",
            "home-lifestyle",
        ]
        
        if list_size == Categories.TESTING:
            return testing_list
        elif list_size == Categories.SHORT:
            return short_category_list
        elif list_size == Categories.FULL:
            return full_category_list


    def get_category_data(self, base_url, category_url, separate_columns):
        
        url = base_url + category_url
        self.driver = get_web_driver()

        try:
            self.driver.get(url)
            
            data = []
            
            while True:
                # Wait for the products to load (you can adjust the wait time if needed)
                wait = WebDriverWait(self.driver, 10)
                wait.until(EC.presence_of_all_elements_located((By.XPATH, "//wc-product-tile")))
                
                # current_container_class_name = woolworths_product_container_class_names[1]
                
                # if current_container_class_name == "":
                #     for container_class_name in woolworths_product_container_class_names:
                #         try:
                #             wait.until(EC.presence_of_all_elements_located((By.XPATH, "//wc-product-tile/section/div[1]/div[2]/div[1]")))
                #             current_container_class_name = container_class_name
                #             break
                #         except:
                #             pass
                # else:
                #     wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, container_class_name)))

                # Get the page source after waiting for the elements to load
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
                products = soup.find_all("wc-product-tile")
                data.extend(self.get_products_data(products, separate_columns))
                
                try:
                    self.driver.find_element(By.CLASS_NAME,"paging-next").click()
                except:
                    break
            
            return data
        
        except Exception as e:
            self.logger.error(e)
            return data
        finally:
            self.driver.quit()
            
    def get_products_data(self, products, separate_columns):
        products_data = []
        
        for i in range(len(products)):
            try:
                text = self.get_product_string(i)
                
                if not separate_columns:
                    products_data.append(text)
                    continue
                product_name, price, price_per_unit = self.get_details_from_product_string(text)
                # product_group = get_product_group(product)
                # product_name = get_product_name(product_group)
                # price, price_per_unit = get_product_price(product_group)
            
            except Exception as e:
                self.logger.error(e)
                try:
                    self.logger.log("Item skipped: %s" % product_name)
                except:
                    self.logger.log("Item skipped")
                continue
            products_data.append([product_name, price, price_per_unit])
        
        return products_data

    def get_product_string(self, i):
        script = 'return document.querySelector("#search-content > div > shared-grid > div > div:nth-child(' + str(i+1) + ') > shared-product-tile > shared-web-component-wrapper > wc-product-tile").shadowRoot.querySelector("section > div")'
        text = self.driver.execute_script(script).text
        return text

    def get_details_from_product_string(self, text):
        print(text)
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

    def get_product_group(self, product: BeautifulSoup):
        # print(product, product.arguments)
        shadow_root = self.get_shadow_root(product)
        section = shadow_root.findChildren("section")
        if (not section):
            print(product.findChildren())
            for child in product.children:
                print(child)
                
        product_tile_body = section.find("div", class_="product-tile-body")
        product_tile_content = product_tile_body.find("div", class_="product-tile-content")
        return product_tile_content.find("div", class_="product-tile-group")

    def get_shadow_root(self, element: BeautifulSoup):
        shadow_root = self.driver.execute_script('return document.querySelector("#search-content > div > shared-grid > div > div:nth-child(1) > shared-product-tile > shared-web-component-wrapper > wc-product-tile").shadowRoot.querySelector("section > div")')
        # shadow_root = driver.execute_script('return arguments[0].shadowRoot', element)
        # return driver.execute_script('return arguments[0].innerHTML',shadow_root)
        return shadow_root

    def get_product_name(self, product: BeautifulSoup):
        container = product.find("div", class_="product-title-container")
        shared_product_tile = container.find("shared-product-tile-title")
        return shared_product_tile.find("div", class_="product-tile-title").text.strip()

    def get_product_price(self, product):
        container = product.find("div", class_="product-information-container")
        product_tile_prices_div = container.find("div", class_="product-tile-v2--prices")
        shared_product_tile_price = product_tile_prices_div.find("shared-product-tile-price")
        product_price_tile = shared_product_tile_price.find("div", "product-tile-price")
        
        primary = product_price_tile.find("div", "primary")
        price = primary.text.strip()
        
        secondary = product_price_tile.find("div", "secondary")
        price_per_unit = secondary.find("span", class_="price-per-cup").text.strip()
        
        return price, price_per_unit