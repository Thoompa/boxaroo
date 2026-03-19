from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import Callable, List
import time
import random


class IWebDriver(ABC):
    
    @abstractmethod
    def get_page(self, url: str) -> None:
        pass
    
    @abstractmethod
    def get_products(self, _callback: Callable[any, None]) -> List[str]: # type: ignore
        pass
    
    @abstractmethod
    def quit(self) -> None:
        pass
    
    @abstractmethod
    def execute_script(self, script: str) -> str:
        pass
    
    @abstractmethod
    def reload_page(self) -> None:
        pass
    
class WebDriver(IWebDriver):
    
    def __init__(self, headless: bool = False, proxy_server: str = None):
        self.headless = headless
        self.proxy_server = proxy_server
        
        # Configure Chrome options
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Anti-bot bypass arguments
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Configure proxy if provided
        if self.proxy_server:
            chrome_options.add_argument(f'--proxy-server={self.proxy_server}')
        
        # Initialize the driver
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Apply selenium-stealth
        stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Linux x86_64",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )
        
        # Set window size to avoid detection
        self.driver.set_window_size(1920, 1080)
        
    def get_page(self, url: str) -> None:
        # Add random delay before navigation (1-3 seconds)
        time.sleep(random.uniform(1, 3))
        self.driver.get(url)
        # Add delay after page load to simulate reading
        time.sleep(random.uniform(2, 5))
        
    def execute_script(self, script: str) -> str:
        # Small delay before executing script
        time.sleep(random.uniform(0.5, 1.5))
        return self.driver.execute_script(script)
    
    def reload_page(self) -> None:
        time.sleep(random.uniform(1, 2))
        self.driver.refresh()
        time.sleep(random.uniform(2, 4))
        
    def quit(self) -> None:
        self.driver.quit()
        
    def get_products(self, _callback: Callable[any, None] = None) -> List[str]: # type: ignore
        data = []
        while True:
            # Add delay before waiting for products
            time.sleep(random.uniform(1, 2))
            
            # Wait for the products to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "wc-product-tile"))
            )
            
            # Simulate scrolling to load more content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2)")
            time.sleep(random.uniform(1, 2))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(random.uniform(1, 2))
            
            # Get all product tiles
            product_elements = self.driver.find_elements(By.TAG_NAME, "wc-product-tile")
            
            if _callback:
                data.extend(_callback(product_elements))
            
            try:
                # Add delay before clicking next button
                time.sleep(random.uniform(2, 4))
                next_button = self.driver.find_element(By.CSS_SELECTOR, ".paging-next")
                if next_button.is_displayed() and next_button.is_enabled():
                    next_button.click()
                    # Wait for page to load after click
                    time.sleep(random.uniform(3, 6))
                else:
                    break
            except:
                break
        
        return data