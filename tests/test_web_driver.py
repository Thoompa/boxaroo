from web_driver import WebDriver


class DummyWebDriverShell(WebDriver):
    def __init__(self):
        # Avoid starting a real browser
        self.scripts = []
        self._category_total_script_response = None

    def execute_script(self, script, *args, **kwargs):
        self.scripts.append(script)
        return self._category_total_script_response

    def get_page(self, url):
        pass

    def get_products(self, _callback=None):
        return {"products": [], "incomplete_items": [], "page_stats": []}

    def quit(self):
        pass

    def reload_page(self):
        pass


def test_get_category_total_items_from_selector(monkeypatch):
    driver = DummyWebDriverShell()
    driver._category_total_script_response = "Showing 480 products"

    total = driver.get_category_total_items()

    assert total == 480


def test_get_category_total_items_fallback_to_tile_count(monkeypatch):
    driver = DummyWebDriverShell()
    # This is returned because no selector is found and we rely on wc-product-tile fallback
    driver._category_total_script_response = "wc-product-tile:42"

    total = driver.get_category_total_items()

    assert total == 42


def test_get_products_page_stats_aggregation(monkeypatch):
    class DummyPageWebDriver(DummyWebDriverShell):
        def __init__(self):
            super().__init__()
            self.page_saved = 0

        def get_products(self, _callback=None):
            self.page_saved += 1
            # return one page only
            items = ["$1.00\nItem A each", "$2.00\nItem B each"]
            if _callback:
                _callback(items)
            return {
                "products": ["A", "B"],
                "incomplete_items": [{"name": "A", "missing": ["unit_price"]}],
                "page_stats": [
                    {"page": 1, "product_tiles": 2, "scraped": 2, "incomplete": 1}
                ],
            }

    driver = DummyPageWebDriver()
    res = driver.get_products(
        lambda x: {
            "products": ["A", "B"],
            "incomplete_items": [{"name": "A", "missing": ["unit_price"]}],
        }
    )

    assert isinstance(res, dict)
    assert res["page_stats"][0]["page"] == 1
    assert res["page_stats"][0]["scraped"] == 2
    assert res["page_stats"][0]["incomplete"] == 1
