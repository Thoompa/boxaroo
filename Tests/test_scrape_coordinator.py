from Code.scrape_coordinator import ScrapeCoordinator
from Tests.test_helpers import DummyFileHandler, DummyLogger


def test_run_stores_products_per_category_and_logs_total_and_incomplete_items():
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    coordinator = ScrapeCoordinator(file_handler=file_handler, logger=logger)

    category_payloads = {
        "fruit-veg": {
            "category": "fruit-veg",
            "total": 2,
            "products": [
                ["Apple each", "$1.00", "$1.00 / 1EA", ""],
                ["Pear each", "$1.20", "$1.20 / 1EA", ""],
            ],
            "incomplete_items": [{"name": "Pear each", "missing": ["promotion"]}],
            "scraped": 2,
            "incomplete": 1,
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

    def get_category_data(category_name: str):
        return category_payloads[category_name]

    coordinator.run(["fruit-veg", "bakery"], get_category_data)

    assert len(file_handler.saved) == 2
    assert len(file_handler.saved[0]) == 2
    assert len(file_handler.saved[1]) == 1

    info_messages = [message for level, message in logger.records if level == "INFO"]
    assert any(
        "Successfully scraped 3 products" in message for message in info_messages
    )
    assert any(
        "Incomplete product: name='Pear each', missing=['promotion']" in message
        for message in info_messages
    )


def test_run_continues_when_category_returns_empty_payload_shape():
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    coordinator = ScrapeCoordinator(file_handler=file_handler, logger=logger)

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

    def get_category_data(category_name: str):
        return category_payloads[category_name]

    coordinator.run(["fruit-veg", "pantry", "bakery"], get_category_data)

    assert len(file_handler.saved) == 3
    assert len(file_handler.saved[0]) == 1
    assert len(file_handler.saved[1]) == 0
    assert len(file_handler.saved[2]) == 1

    info_messages = [message for level, message in logger.records if level == "INFO"]
    assert any(
        "Successfully scraped 2 products" in message for message in info_messages
    )


def test_run_logs_page_stats_when_present():
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    coordinator = ScrapeCoordinator(file_handler=file_handler, logger=logger)

    category_payload = {
        "category": "fruit-veg",
        "total": 1,
        "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
        "incomplete_items": [],
        "page_stats": [
            {
                "page": 1,
                "product_tiles": 1,
                "scraped": 1,
                "incomplete": 0,
            }
        ],
        "scraped": 1,
        "incomplete": 0,
    }

    coordinator.run(["fruit-veg"], lambda _: category_payload)

    info_messages = [message for level, message in logger.records if level == "INFO"]
    assert any(
        "Category fruit-veg - page 1 : tiles=1 scraped=1 incomplete=0" in message
        for message in info_messages
    )
