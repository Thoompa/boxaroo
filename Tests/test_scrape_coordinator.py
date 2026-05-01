from Code.isupermarket import ListSize
from Code.scrape_coordinator import ScrapeCoordinator
from Tests.test_helpers import (
    DummyFileHandler,
    DummyLogger,
    DummySupermarket,
)


def test_scrape_coordinator_keeps_dependencies_without_starting_runtime_work():
    # Construction guardrail: this test protects the coordinator wiring contract.
    # GIVEN: a coordinator with a supermarket adapter, logger and file handler
    logger = DummyLogger()
    supermarket = DummySupermarket(logger=logger)
    file_handler = DummyFileHandler()

    # WHEN: the coordinator is created
    coordinator = ScrapeCoordinator(
        supermarket=supermarket,
        logger=logger,
        file_handler=file_handler,
    )

    # THEN: the boundary is represented without triggering scraping
    assert coordinator.supermarket is supermarket
    assert coordinator.logger is logger
    assert coordinator.file_handler is file_handler
    assert supermarket.get_categories_called is False


def test_coordinator_run_stores_products_per_category_and_logs_total():
    # GIVEN: a supermarket with two categories and product payloads
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger,
        categories=["fruit-veg", "bakery"],
        category_data={
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
        },
    )
    coordinator = ScrapeCoordinator(
        supermarket=supermarket,
        logger=logger,
        file_handler=file_handler,
    )

    # WHEN: coordinator.run() is called
    coordinator.run(list_size=ListSize.SHORT)

    # THEN: each category payload is stored and the total success log is recorded
    assert len(file_handler.saved) == 2
    assert len(file_handler.saved[0]) == 1
    assert len(file_handler.saved[1]) == 2
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any("Successfully scraped 3 products" in msg for msg in info_messages)


def test_coordinator_run_continues_when_a_category_raises(monkeypatch):
    # GIVEN: three categories where one category scrape raises an error
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger,
        categories=["fruit-veg", "pantry", "bakery"],
    )
    coordinator = ScrapeCoordinator(
        supermarket=supermarket,
        logger=logger,
        file_handler=file_handler,
    )

    attempted_categories = []

    def fake_get_category_data(category_name: str):
        attempted_categories.append(category_name)
        if category_name == "pantry":
            raise RuntimeError("pantry failed")
        if category_name == "fruit-veg":
            return {
                "category": "fruit-veg",
                "total": 1,
                "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
                "incomplete_items": [],
                "scraped": 1,
                "incomplete": 0,
            }
        return {
            "category": "bakery",
            "total": 1,
            "products": [["Bread each", "$3.50", "$3.50 / 1EA", ""]],
            "incomplete_items": [],
            "scraped": 1,
            "incomplete": 0,
        }

    monkeypatch.setattr(supermarket, "get_category_data", fake_get_category_data)

    # WHEN: coordinator.run() is called
    coordinator.run(list_size=ListSize.TESTING)

    # THEN: all categories are attempted and successful categories are persisted
    assert attempted_categories == ["fruit-veg", "pantry", "bakery"]
    assert len(file_handler.saved) == 2
    assert file_handler.saved[0][0][0] == "Apple each"
    assert file_handler.saved[1][0][0] == "Bread each"


def test_coordinator_run_skips_invalid_non_dict_category_payload(monkeypatch):
    # GIVEN: categories where one returns malformed non-dict payload
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger,
        categories=["fruit-veg", "pantry", "bakery"],
    )
    coordinator = ScrapeCoordinator(
        supermarket=supermarket,
        logger=logger,
        file_handler=file_handler,
    )

    def fake_get_category_data(category_name: str):
        if category_name == "pantry":
            return ["invalid-payload"]
        if category_name == "fruit-veg":
            return {
                "category": "fruit-veg",
                "total": 1,
                "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
                "incomplete_items": [],
                "scraped": 1,
                "incomplete": 0,
            }
        return {
            "category": "bakery",
            "total": 1,
            "products": [["Bread each", "$3.50", "$3.50 / 1EA", ""]],
            "incomplete_items": [],
            "scraped": 1,
            "incomplete": 0,
        }

    monkeypatch.setattr(supermarket, "get_category_data", fake_get_category_data)

    # WHEN: coordinator.run() is called
    coordinator.run(list_size=ListSize.TESTING)

    # THEN: malformed payload is skipped, valid categories are stored, and an error is logged
    assert len(file_handler.saved) == 2
    assert file_handler.saved[0][0][0] == "Apple each"
    assert file_handler.saved[1][0][0] == "Bread each"
    error_messages = [msg for level, msg in logger.records if level == "ERROR"]
    assert any("Invalid category data for 'pantry'" in msg for msg in error_messages)


def test_coordinator_run_continues_when_a_category_returns_empty_payload():
    # GIVEN: three categories where one returns an empty products list
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger,
        categories=["fruit-veg", "pantry", "bakery"],
        category_data={
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
        },
    )
    coordinator = ScrapeCoordinator(
        supermarket=supermarket,
        logger=logger,
        file_handler=file_handler,
    )

    # WHEN: coordinator.run() is called
    coordinator.run(list_size=ListSize.TESTING)

    # THEN: all three categories are stored, empty payload is persisted as-is,
    #       later categories are not skipped, and the total reflects only real products
    assert len(file_handler.saved) == 3
    assert file_handler.saved[0] == [["Apple each", "$1.00", "$1.00 / 1EA", ""]]
    assert file_handler.saved[1] == []
    assert file_handler.saved[2] == [["Bread each", "$3.50", "$3.50 / 1EA", ""]]
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any("Successfully scraped 2 products" in msg for msg in info_messages)


def test_coordinator_run_logs_start_message():
    # GIVEN: a supermarket and logger for coordinator orchestration
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger,
        categories=["fruit-veg"],
        category_data={
            "fruit-veg": {
                "category": "fruit-veg",
                "total": 1,
                "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
                "incomplete_items": [],
                "scraped": 1,
                "incomplete": 0,
            }
        },
    )
    coordinator = ScrapeCoordinator(
        supermarket=supermarket,
        logger=logger,
        file_handler=file_handler,
    )

    # WHEN: coordinator.run() is executed
    coordinator.run()

    # THEN: an INFO message records generic scraping plus adapter identity
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any("Scraping DummySupermarket categories" in msg for msg in info_messages)
