from datetime import date
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logger
from data_storage import store_data
from web_driver import get_web_driver

def get_woolworths_data(split_files_by_category=False):
    woolworths_url = "https://www.woolworths.com.au/shop/browse/"
    categories = get_all_categories()
    data = []
    header = ["Product Name", "Price", "Price per Unit"]
    
    for category in categories:
        category_data = get_category_data(woolworths_url, category)
        
        if split_files_by_category:
            file_name = "woolworths-{0}-{1}.csv".format(category, date.today())
            store_data(file_name, category_data, header)
        
        data.extend(category_data)

    if not split_files_by_category:
        file_name = "woolworths-{0}.csv".format(date.today())
        store_data(file_name, data, header)
        
    return data
        
def get_all_categories():
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
    return [
        "winter",
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

def get_category_data(base_url, category_url):
    
    url = base_url + category_url
    driver = get_web_driver()

    try:
        driver.get(url)
        
        data = []
        
        while True:
            # Wait for the products to load (you can adjust the wait time if needed)
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "product-tile-v2")))

            # Get the page source after waiting for the elements to load
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            products = soup.find_all("section", class_="product-tile-v2")
            
            data.extend(get_products_data(products))
            
            try:
                driver.find_element(By.CLASS_NAME,"paging-next").click()
            except:
                break
        
        return data
       
    except Exception as e:
        logger.error(e)
        return data
    finally:
        driver.quit()
        
def get_products_data(products):
    data = []
    
    for product in products:
        try:
            product_name = get_product_name(product)
            price, price_per_unit = get_product_price(product)
        
        except:
            logger.log("Item skipped: %s" % product_name)
            continue
        data.append([product_name, price, price_per_unit])
    
    return data

def get_product_name(product: BeautifulSoup):
    container = product.find("div", class_="product-title-container")
    shared_product_tile = container.find("shared-product-tile-title")
    return shared_product_tile.find("div", class_="product-tile-title").text.strip()

def get_product_price(product):
    container = product.find("div", class_="product-information-container")
    product_tile_prices_div = container.find("div", class_="product-tile-v2--prices")
    shared_product_tile_price = product_tile_prices_div.find("shared-product-tile-price")
    product_price_tile = shared_product_tile_price.find("div", "product-tile-price")
    
    primary = product_price_tile.find("div", "primary")
    price = primary.text.strip()
    
    secondary = product_price_tile.find("div", "secondary")
    price_per_unit = secondary.find("span", class_="price-per-cup").text.strip()
    
    return price, price_per_unit