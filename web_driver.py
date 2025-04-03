from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import Callable, List


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
    
class WebDriver(IWebDriver):
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = self._get_web_driver()
        
    def _get_web_driver(self) -> webdriver:
        # Use headless option to run Chrome in the background without GUI
        chrome_options = Options()
        if (self.headless):
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920, 1080")
        return webdriver.Chrome(options=chrome_options)
    
    def get_page(self, url: str) -> None:
        self.driver.get(url)
        
    def execute_script(self, script: str) -> str:
        return self.driver.execute_script(script).text
        
    def quit(self) -> None:
        self.driver.quit()
        
    def get_products(self, _callback: Callable[any, None] = None) -> List[str]: # type: ignore
        data = []
        while True:
            # Wait for the products to load (you can adjust the wait time if needed)
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.XPATH, "//wc-product-tile")))
            
            # Get the page source after waiting for the elements to load
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            products = soup.find_all("wc-product-tile")
            
            if _callback:
                data.extend(_callback(products))
            
            try:
                self.driver.find_element(By.CLASS_NAME,"paging-next").click()
            except:
                break
        
        return data