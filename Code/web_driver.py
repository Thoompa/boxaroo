import re
import os
import platform
import shutil
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Any
import time
import random
from Code.contracts import IWebDriver, ProductsCallback, ProductsPageResult


class WebDriver(IWebDriver):

    @staticmethod
    def _resolve_executable(candidate: str | None) -> str | None:
        if candidate is None:
            return None

        resolved_candidate = candidate.strip()
        if not resolved_candidate:
            return None

        if os.path.sep in resolved_candidate:
            if os.path.isfile(resolved_candidate) and os.access(
                resolved_candidate, os.X_OK
            ):
                return resolved_candidate
            return None

        return shutil.which(resolved_candidate)

    @classmethod
    def _resolve_browser_binary(cls) -> str | None:
        env_browser_binary = cls._resolve_executable(os.getenv("CHROME_BINARY"))
        if env_browser_binary:
            return env_browser_binary

        browser_candidates = (
            "chromium",
            "chromium-browser",
            "google-chrome",
            "google-chrome-stable",
        )
        for browser_candidate in browser_candidates:
            resolved_binary = cls._resolve_executable(browser_candidate)
            if resolved_binary:
                return resolved_binary

        return None

    @classmethod
    def _resolve_chromedriver_binary(cls) -> str | None:
        env_chromedriver = cls._resolve_executable(os.getenv("CHROMEDRIVER"))
        if env_chromedriver:
            return env_chromedriver

        return cls._resolve_executable("chromedriver")

    @staticmethod
    def _build_driver_setup_error(
        browser_binary: str | None,
        chromedriver_binary: str | None,
    ) -> str:
        diagnostics = (
            "Boxaroo could not locate a supported browser and/or chromedriver. "
            f"Detected browser binary: {browser_binary or 'not found'}, "
            f"detected chromedriver: {chromedriver_binary or 'not found'}."
        )
        linux_setup = (
            "Install Chromium and chromedriver, then verify with 'which' commands.\n"
            "- Debian/Ubuntu/Raspberry Pi OS: sudo apt install chromium chromium-driver\n"
            "- Arch/EndeavourOS: sudo pacman -S chromium chromedriver\n"
            "- Fedora: sudo dnf install chromium chromedriver\n"
            "- openSUSE: sudo zypper install chromium chromedriver\n"
            "Verify: which chromium || which google-chrome; which chromedriver\n"
            "For non-standard locations, set CHROME_BINARY and CHROMEDRIVER."
        )
        return f"{diagnostics}\n{linux_setup}"

    @classmethod
    def _resolve_driver_binaries(cls) -> tuple[str, str]:
        browser_binary = cls._resolve_browser_binary()
        chromedriver_binary = cls._resolve_chromedriver_binary()
        if not browser_binary or not chromedriver_binary:
            raise RuntimeError(
                cls._build_driver_setup_error(browser_binary, chromedriver_binary)
            )
        return browser_binary, chromedriver_binary

    def __init__(self, headless: bool = False, proxy_server: str | None = None):
        self.headless = headless
        self.proxy_server = proxy_server
        browser_binary = None
        chromedriver_binary = None
        resolution_error = None
        try:
            browser_binary, chromedriver_binary = self._resolve_driver_binaries()
        except RuntimeError as exc:
            # Keep a setup diagnostic for later if Selenium Manager fallback also fails.
            resolution_error = str(exc)

        # Configure Chrome options
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")

        if browser_binary:
            chrome_options.binary_location = browser_binary

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
        try:
            if browser_binary and chromedriver_binary:
                self.driver = ChromeWebDriver(
                    service=Service(executable_path=chromedriver_binary),
                    options=chrome_options,
                )
            else:
                # Fallback to Selenium Manager for environments where binaries
                # are available via Selenium-managed resolution.
                self.driver = ChromeWebDriver(options=chrome_options)
        except Exception as exc:
            if resolution_error is not None:
                raise RuntimeError(
                    f"{resolution_error}\nSelenium Manager fallback also failed: {exc}"
                ) from exc
            raise

        platform_name = os.getenv(
            "SELENIUM_STEALTH_PLATFORM", f"Linux {platform.machine()}"
        )

        # Apply selenium-stealth
        stealth(
            self.driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform=platform_name,
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

    def execute_script(self, script: str, *args) -> Any:
        # Small delay before executing script
        time.sleep(random.uniform(0.5, 1.5))
        return self.driver.execute_script(script, *args)

    def reload_page(self) -> None:
        time.sleep(random.uniform(1, 2))
        self.driver.refresh()
        time.sleep(random.uniform(2, 4))

    def quit(self) -> None:
        self.driver.quit()

    def get_category_total_items(self) -> int | None:
        # Read visible total count from the page. Try a few common selectors, then fallback to counting tiles.
        script = r"""
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
            var bodyText = (document.body && (document.body.innerText || document.body.textContent)) || '';
            var displayMatch = bodyText.match(/displaying\s+\d+\s*[–-]\s*(?:to\s*)?\d+\s+of\s+\d[\d,]*\s+products/i);
            if (displayMatch && displayMatch[0]) {
                return displayMatch[0].trim();
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

        total_match = re.search(r"\bof\s+(\d[\d,]*)\b", raw_text, re.IGNORECASE)
        if total_match:
            try:
                return int(total_match.group(1).replace(",", ""))
            except ValueError:
                return None

        matches = re.findall(r"\d[\d,]*", raw_text)
        if matches:
            try:
                return int(matches[-1].replace(",", ""))
            except ValueError:
                return None

        return None

    def _advance_to_next_page(self) -> bool:
        try:
            next_button = self.driver.find_element(By.CSS_SELECTOR, ".paging-next")
            if not next_button.is_displayed() or not next_button.is_enabled():
                return False

            current_url = self.driver.current_url
            next_href = (next_button.get_attribute("href") or "").strip()

            if next_href and next_href != current_url:
                time.sleep(random.uniform(1, 2))
                self.driver.get(next_href)
                time.sleep(random.uniform(3, 6))
                return True

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", next_button
            )
            time.sleep(random.uniform(0.5, 1.0))
            self.driver.execute_script("arguments[0].click();", next_button)
            time.sleep(random.uniform(3, 6))
            return self.driver.current_url != current_url
        except Exception:
            return False

    def _extract_text_from_product_element(self, element: Any) -> str:
        """Return plain product text from a Selenium tile element."""
        if element is None:
            return ""

        if isinstance(element, str):
            return element.strip()

        try:
            text = element.text or ""
        except TimeoutError:
            raise
        except Exception:
            text = ""

        if isinstance(text, str) and text.strip():
            return text.strip()

        # If direct text is empty, fallback to shadow root extraction.
        shadow_script = """
        var element = arguments[0];
        if (element && element.shadowRoot) {
            var section = element.shadowRoot.querySelector("section > div");
            return section ? section.textContent.trim() : "";
        }
        return "";
        """
        try:
            text = self.driver.execute_script(shadow_script, element)
        except TimeoutError:
            raise
        except Exception:
            text = ""

        if text is None:
            return ""

        if isinstance(text, str):
            return text.strip()

        try:
            return str(text).strip()
        except Exception:
            return ""

    def get_products(
        self,
        _callback: ProductsCallback | None = None,
    ) -> ProductsPageResult:
        """Paginate product tiles and expose only plain text payloads to callback."""
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
            product_payloads = []
            extraction_failures = 0
            for element in product_elements:
                try:
                    product_payloads.append(
                        self._extract_text_from_product_element(element)
                    )
                except TimeoutError:
                    extraction_failures += 1
                    self.reload_page()
                except Exception:
                    extraction_failures += 1

            page_products_count = 0
            page_incomplete_count = 0
            if _callback:
                callback_result = _callback(product_payloads, page_number=page_number)
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
                    "extraction_failures": extraction_failures,
                    "scraped": page_products_count,
                    "incomplete": page_incomplete_count,
                }
            )

            if not self._advance_to_next_page():
                break

        return {
            "products": all_data,
            "incomplete_items": all_incomplete,
            "page_stats": page_stats,
        }
