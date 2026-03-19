import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from abc import ABC, abstractmethod
from typing import Callable, List
import time
import random


class IWebDriver(ABC):

    @abstractmethod
    def get_page(self, url: str) -> None:
        pass

    @abstractmethod
    def get_products(self, _callback: Callable[any, None]) -> List[str]:  # type: ignore
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
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Configure proxy if provided
        if self.proxy_server:
            chrome_options.add_argument(f"--proxy-server={self.proxy_server}")

        # Initialize the driver
        self.driver = webdriver.Chrome(options=chrome_options)

        # Apply selenium-stealth
        stealth(
            self.driver,
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

    def get_category_total_items(self) -> int | None:
        # Read visible total count from the page. Try a few common selectors, then fallback to counting tiles.
        script = """
        try {
            var selectors = [
                '.ais-Stats-text',
                '.search-result-count',
                '.search-results-count',
                '.ais-SearchResults__status',
                '.paging-summary',
                '.results-count',
                '.search-title',
                '.search-title-count'
            ];
            for (var s of selectors) {
                var el = document.querySelector(s);
                if (el && el.textContent && el.textContent.trim().length > 0) {
                    return el.textContent.trim();
                }
            }
            var tiles = document.querySelectorAll('wc-product-tile');
            if (tiles) {
                return 'wc-product-tile:' + tiles.length;
            }
            return '';
        } catch (e) {
            return '';
        }
        """
        raw_text = self.execute_script(script)
        if not raw_text or not raw_text.strip():
            return None

        if raw_text.startswith("wc-product-tile:"):
            try:
                return int(raw_text.split(":", 1)[1])
            except ValueError:
                return None

        match = re.search(r"(\d[\d,]*)", raw_text)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                return None

        return None

    def get_products(self, _callback: Callable[any, None] = None) -> dict:
        all_data = []
        all_incomplete = []
        page_stats = []
        page_number = 0

        while True:
            page_number += 1

            # Add delay before waiting for products
            time.sleep(random.uniform(1, 2))

            # Wait for the products to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "wc-product-tile"))
            )

            # Simulate scrolling to load more content
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight / 2)"
            )
            time.sleep(random.uniform(1, 2))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(random.uniform(1, 2))

            # Get all product tiles
            product_elements = self.driver.find_elements(By.TAG_NAME, "wc-product-tile")

            page_products_count = 0
            page_incomplete_count = 0
            if _callback:
                callback_result = _callback(product_elements)
                if isinstance(callback_result, dict):
                    products = callback_result.get("products", [])
                    incomplete_items = callback_result.get("incomplete_items", [])
                    all_data.extend(products)
                    all_incomplete.extend(incomplete_items)
                    page_products_count = len(products)
                    page_incomplete_count = len(incomplete_items)
                else:
                    all_data.extend(callback_result)
                    page_products_count = len(callback_result)

            page_stats.append(
                {
                    "page": page_number,
                    "product_tiles": len(product_elements),
                    "scraped": page_products_count,
                    "incomplete": page_incomplete_count,
                }
            )

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
            except Exception:
                break

        return {
            "products": all_data,
            "incomplete_items": all_incomplete,
            "page_stats": page_stats,
        }
