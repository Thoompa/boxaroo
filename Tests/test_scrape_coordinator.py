from Code.isupermarket import ListSize
from Code.scrape_coordinator import ScrapeCoordinator
from Code.woolworths import Woolworths
from Tests.test_helpers import (
    DummyFileHandler,
    DummyLogger,
    DummyProductParser,
    DummySupermarket,
    DummyWebDriver,
)


def test_scrape_coordinator_keeps_dependencies_without_starting_runtime_work():
    # Transitional guardrail: replace with coordinator behavior tests once run() exists.
    # GIVEN: a coordinator with a supermarket adapter and logger
    logger = DummyLogger()
    supermarket = DummySupermarket(logger=logger)

    # WHEN: the coordinator is created
    coordinator = ScrapeCoordinator(supermarket=supermarket, logger=logger)

    # THEN: the boundary is represented without triggering scraping
    assert coordinator.supermarket is supermarket
    assert coordinator.logger is logger
    assert supermarket.get_data_called is False


def test_woolworths_exposes_category_level_methods_for_future_orchestration():
    # Transitional guardrail: replace with runtime wiring tests once coordinator owns orchestration.
    # GIVEN: a Woolworths adapter with existing private seams patched
    woolworths = Woolworths(
        file_handler=DummyFileHandler(),
        logger=DummyLogger(),
        web_driver=DummyWebDriver(),
        product_parser=DummyProductParser(),
    )
    expected_categories = ["fruit-veg", "pantry"]
    expected_category_data = {
        "category": "fruit-veg",
        "total": 1,
        "products": [["Apple", "$1.00", "$1.00 / 1EA", ""]],
        "incomplete_items": [],
        "scraped": 1,
        "incomplete": 0,
    }
    woolworths._get_all_categories = (
        lambda list_size, refresh_category_lists=False: expected_categories
    )
    woolworths._get_category_data = lambda category_name: expected_category_data

    # WHEN: the public category-level adapter methods are used
    categories = woolworths.get_categories(ListSize.SHORT, refresh_category_lists=True)
    category_data = woolworths.get_category_data("fruit-veg")

    # THEN: existing adapter behavior is exposed through coordinator-facing seams
    assert categories == expected_categories
    assert category_data == expected_category_data


def test_transitional_orchestration_path_stores_per_category_and_logs_total(
    monkeypatch,
):
    # Transitional guardrail: replace with coordinator run() behavior tests after Goal 2 wiring.
    # GIVEN: a Woolworths adapter with two categories of results
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    woolworths = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=DummyWebDriver(),
        product_parser=DummyProductParser(),
    )
    expected_categories = ["fruit-veg", "bakery"]
    category_payloads = {
        "fruit-veg": {
            "category": "fruit-veg",
            "total": 1,
            "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
            "incomplete_items": [],
            "scraped": 1,
            "incomplete": 0,
        },
        "bakery": {
            "category": "bakery",
            "total": 2,
            "products": [
                ["Bread each", "$3.50", "$3.50 / 1EA", ""],
                ["Bagel each", "$1.50", "$1.50 / 1EA", ""],
            ],
            "incomplete_items": [],
            "scraped": 2,
            "incomplete": 0,
        },
    }
    monkeypatch.setattr(
        woolworths,
        "_get_all_categories",
        lambda *_args, **_kwargs: expected_categories,
    )
    monkeypatch.setattr(
        woolworths,
        "_get_category_data",
        lambda category_name: category_payloads[category_name],
    )

    # WHEN: the transitional orchestration path is executed
    woolworths.get_data(list_size=ListSize.SHORT)

    # THEN: one payload is stored per category and total logs are preserved
    assert len(file_handler.saved) == 2
    assert len(file_handler.saved[0]) == 1
    assert len(file_handler.saved[1]) == 2
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any("Successfully scraped 3 products" in msg for msg in info_messages)


def test_transitional_orchestration_path_continues_when_a_category_returns_empty(
    monkeypatch,
):
    # Transitional guardrail: replace with coordinator failure-policy tests after Goal 2 wiring.
    # GIVEN: a Woolworths adapter where one category returns an empty payload
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    woolworths = Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=DummyWebDriver(),
        product_parser=DummyProductParser(),
    )
    monkeypatch.setattr(
        woolworths,
        "_get_all_categories",
        lambda *_args, **_kwargs: ["fruit-veg", "pantry", "bakery"],
    )
    category_payloads = {
        "fruit-veg": {
            "category": "fruit-veg",
            "total": 1,
            "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
            "incomplete_items": [],
            "scraped": 1,
            "incomplete": 0,
        },
        "pantry": {
            "category": "pantry",
            "total": 0,
            "products": [],
            "incomplete_items": [],
            "scraped": 0,
            "incomplete": 0,
        },
        "bakery": {
            "category": "bakery",
            "total": 1,
            "products": [["Bread each", "$3.50", "$3.50 / 1EA", ""]],
            "incomplete_items": [],
            "scraped": 1,
            "incomplete": 0,
        },
    }
    monkeypatch.setattr(
        woolworths,
        "_get_category_data",
        lambda category_name: category_payloads[category_name],
    )

    # WHEN: the transitional orchestration path is executed
    woolworths.get_data(list_size=ListSize.TESTING)

    # THEN: later categories are still stored and total excludes empty payloads
    assert len(file_handler.saved) == 3
    assert len(file_handler.saved[0]) == 1
    assert len(file_handler.saved[1]) == 0
    assert len(file_handler.saved[2]) == 1
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any("Successfully scraped 2 products" in msg for msg in info_messages)


def test_get_data_delegates_through_category_level_seams(monkeypatch):
    # Transitional compatibility guardrail: remove after runtime path uses coordinator directly.
    # GIVEN: a Woolworths adapter with seam methods instrumented
    file_handler = DummyFileHandler()
    woolworths = Woolworths(
        file_handler=file_handler,
        logger=DummyLogger(),
        web_driver=DummyWebDriver(),
        product_parser=DummyProductParser(),
    )
    called = {
        "get_categories": False,
        "get_category_data": [],
    }

    def fake_get_categories(list_size: ListSize, refresh_category_lists: bool = False):
        called["get_categories"] = True
        assert list_size == ListSize.MEDIUM
        assert refresh_category_lists is True
        return ["fruit-veg", "bakery"]

    def fake_get_category_data(category_name: str):
        called["get_category_data"].append(category_name)
        return {
            "category": category_name,
            "total": 1,
            "products": [[f"{category_name} item", "$1.00", "$1.00 / 1EA", ""]],
            "incomplete_items": [],
            "scraped": 1,
            "incomplete": 0,
        }

    monkeypatch.setattr(woolworths, "get_categories", fake_get_categories)
    monkeypatch.setattr(woolworths, "get_category_data", fake_get_category_data)

    # WHEN: get_data is called on the legacy runtime path
    woolworths.get_data(list_size=ListSize.MEDIUM, refresh_category_lists=True)

    # THEN: both contracts stay coupled through explicit delegation
    assert called["get_categories"] is True
    assert called["get_category_data"] == ["fruit-veg", "bakery"]
    assert len(file_handler.saved) == 2
