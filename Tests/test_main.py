import pytest
from Code.main import _format_eta, build_list_size_help, main
import Code.main as main_module
from Code.isupermarket import ListSize
from Code.logger import LoggingLevel
from Tests.test_helpers import (
    DummyLogger,
    DummyFileHandler,
    DummyWebDriver,
    DummySupermarket,
)


# 1-3: Test each valid ListSize
@pytest.mark.parametrize(
    "list_size_enum",
    [
        ListSize.TESTING,
        ListSize.SHORT,
        ListSize.MEDIUM,
        ListSize.LONG,
        ListSize.FULL,
    ],
)
def test_main_list_size_parameter(monkeypatch, list_size_enum):
    # GIVEN: A valid ListSize value
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    called = {"list_size": None}

    def logic(log, ls, refresh):
        called["list_size"] = ls

    supermarket = DummySupermarket(logger=logger, logic=logic)
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is invoked
    main(
        headless=True,
        logging_level=LoggingLevel.ERROR,
        default_list_size=list_size_enum,
        proxy_server=None,
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
    )

    # THEN: The supermarket receives the correct list_size
    assert (
        supermarket.get_categories_called
    ), "Expected get_categories to be called on DummySupermarket"
    assert (
        called["list_size"] == list_size_enum
    ), f"Expected list_size {list_size_enum}, got {called['list_size']}"


# 4: Test None defaults to TESTING
def test_main_default_list_size_none(monkeypatch):
    # GIVEN: default_list_size=None
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    called = {"list_size": None}

    def logic(log, ls, refresh):
        called["list_size"] = ls

    supermarket = DummySupermarket(logger=logger, logic=logic)
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is invoked
    main(
        headless=True,
        logging_level=LoggingLevel.ERROR,
        default_list_size=None,
        proxy_server=None,
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
    )

    # THEN: The supermarket receives ListSize.TESTING as the list_size
    assert (
        supermarket.get_categories_called
    ), "Expected get_categories to be called on DummySupermarket"
    assert (
        called["list_size"] == ListSize.TESTING
    ), f"Expected list_size ListSize.TESTING, got {called['list_size']}"


def test_main_refresh_category_lists_parameter(monkeypatch):
    # GIVEN: refresh_category_lists=True
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    supermarket = DummySupermarket(logger=logger)
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is invoked
    main(
        headless=True,
        logging_level=LoggingLevel.INFO,
        default_list_size=ListSize.FULL,
        refresh_category_lists=True,
        proxy_server=None,
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
    )

    # THEN: refresh_category_lists=True is forwarded to the supermarket
    assert supermarket.get_categories_called
    assert supermarket.last_refresh_category_lists is True


def test_main_refresh_category_lists_default_false(monkeypatch):
    # GIVEN: refresh_category_lists=False
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    supermarket = DummySupermarket(logger=logger)
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is invoked
    main(
        headless=True,
        logging_level=LoggingLevel.INFO,
        default_list_size=ListSize.FULL,
        refresh_category_lists=False,
        proxy_server=None,
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
    )

    # THEN: refresh_category_lists=False is forwarded to the supermarket
    assert supermarket.get_categories_called
    assert supermarket.last_refresh_category_lists is False


@pytest.mark.parametrize(
    "total_products, expected",
    [
        (None, "n/a"),
        (0, "~0s"),
        (108, "~27s"),
        (600, "~2m 30s"),
        (14892, "~1h 2m 3s"),
        (14400, "~1h"),
    ],
)
def test_format_eta(total_products, expected):
    # GIVEN: A total_products value and its expected ETA text
    # WHEN: _format_eta() is called
    # THEN: It returns the expected formatted ETA string
    assert _format_eta(total_products) == expected


def test_build_list_size_help_uses_formatted_eta(monkeypatch):
    # GIVEN: Cached product totals are available for each list size
    monkeypatch.setattr(
        "Code.main._load_list_product_totals",
        lambda: {
            "testing": 108,  # 27s
            "short": 600,  # 2m 30s
            "medium": 14400,  # 1h
            "long": 14892,  # 1h 2m 3s
            "full": 0,  # 0s
        },
    )

    # WHEN: build_list_size_help() is called
    help_text = build_list_size_help()

    # THEN: Help text includes each list size with a formatted ETA
    assert "TESTING ~27s" in help_text
    assert "SHORT ~2m 30s" in help_text
    assert "MEDIUM ~1h" in help_text
    assert "LONG ~1h 2m 3s" in help_text
    assert "FULL ~0s" in help_text


def test_build_list_size_help_with_no_cache_returns_all_na(monkeypatch):
    # GIVEN: No cached product totals are available
    monkeypatch.setattr(main_module, "_load_list_product_totals", lambda: {})

    # WHEN: build_list_size_help() is called
    help_text = build_list_size_help()

    # THEN: Help text shows n/a for all list sizes
    assert "TESTING n/a" in help_text
    assert "SHORT n/a" in help_text
    assert "MEDIUM n/a" in help_text
    assert "LONG n/a" in help_text
    assert "FULL n/a" in help_text


def test_main_quits_webdriver_on_success_and_preserves_output(monkeypatch):
    # GIVEN: Scraping succeeds and returns products
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    expected_products = [
        {
            "Product Name": "Milk",
            "Price": "$4.00",
            "Unit Price": "$2.00/L",
            "Promotion": "",
        }
    ]

    supermarket = DummySupermarket(
        logger=logger,
        file_handler=file_handler,
        web_driver=web_driver,
        products_to_store=expected_products,
    )
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is invoked
    main(
        headless=True,
        logging_level=LoggingLevel.INFO,
        default_list_size=ListSize.TESTING,
        refresh_category_lists=False,
        proxy_server=None,
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
    )

    # THEN: WebDriver is quit once and scraped output is preserved
    assert web_driver.called.count(("quit",)) == 1
    assert file_handler.saved == [expected_products]
    assert ("INFO", "WebDriver lifecycle start") in logger.records
    assert ("INFO", "WebDriver lifecycle stop") in logger.records


def test_main_quits_webdriver_when_get_category_data_raises(monkeypatch):
    # GIVEN: A category scrape raises an error during coordinator run
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()

    supermarket = DummySupermarket(
        logger=logger,
        file_handler=file_handler,
        web_driver=web_driver,
        categories=["fruit-veg"],
        get_category_data_error=RuntimeError("scrape failed"),
    )
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is invoked
    main(
        headless=True,
        logging_level=LoggingLevel.INFO,
        default_list_size=ListSize.TESTING,
        refresh_category_lists=False,
        proxy_server=None,
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
    )

    # THEN: category failure is logged and WebDriver teardown still completes
    assert web_driver.called.count(("quit",)) == 1
    assert ("INFO", "WebDriver lifecycle start") in logger.records
    assert ("INFO", "WebDriver lifecycle stop") in logger.records
    assert any(
        level == "ERROR"
        and "Failed to scrape category 'fruit-veg': scrape failed" in message
        for level, message in logger.records
    )


def test_main_quits_webdriver_when_get_categories_raises(monkeypatch):
    # GIVEN: Category selection raises an error before category scraping starts
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()

    supermarket = DummySupermarket(
        logger=logger,
        file_handler=file_handler,
        web_driver=web_driver,
        get_categories_error=RuntimeError("category selection failed"),
    )
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is invoked
    with pytest.raises(RuntimeError, match="category selection failed"):
        main(
            headless=True,
            logging_level=LoggingLevel.INFO,
            default_list_size=ListSize.TESTING,
            refresh_category_lists=False,
            proxy_server=None,
            file_handler=file_handler,
            logger=logger,
            web_driver=web_driver,
        )

    # THEN: WebDriver is still quit once and lifecycle logs are emitted
    assert web_driver.called.count(("quit",)) == 1
    assert ("INFO", "WebDriver lifecycle start") in logger.records
    assert ("INFO", "WebDriver lifecycle stop") in logger.records


def test_main_raises_quit_error_when_scrape_succeeds_and_quit_fails(monkeypatch):
    # GIVEN: Scraping succeeds but WebDriver.quit() fails
    logger = DummyLogger()
    file_handler = DummyFileHandler()

    class QuitFailingDriver(DummyWebDriver):
        def quit(self):
            self.called.append(("quit",))
            raise RuntimeError("quit failed")

    web_driver = QuitFailingDriver()

    supermarket = DummySupermarket(
        logger=logger,
        file_handler=file_handler,
        web_driver=web_driver,
    )
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is invoked
    with pytest.raises(RuntimeError, match="quit failed"):
        main(
            headless=True,
            logging_level=LoggingLevel.INFO,
            default_list_size=ListSize.TESTING,
            refresh_category_lists=False,
            proxy_server=None,
            file_handler=file_handler,
            logger=logger,
            web_driver=web_driver,
        )

    # THEN: The quit error is raised and logged, and stop log is not emitted
    assert web_driver.called.count(("quit",)) == 1
    assert ("INFO", "WebDriver lifecycle start") in logger.records
    assert ("INFO", "WebDriver lifecycle stop") not in logger.records
    assert any(
        level == "ERROR" and "WebDriver quit failed: quit failed" in message
        for level, message in logger.records
    )


def test_main_preserves_scrape_error_when_quit_also_raises(monkeypatch):
    # GIVEN: Scraping fails and WebDriver.quit() also fails
    logger = DummyLogger()
    file_handler = DummyFileHandler()

    class QuitFailingDriver(DummyWebDriver):
        def quit(self):
            self.called.append(("quit",))
            raise RuntimeError("quit failed")

    web_driver = QuitFailingDriver()

    supermarket = DummySupermarket(
        logger=logger,
        file_handler=file_handler,
        web_driver=web_driver,
        get_categories_error=RuntimeError("scrape failed"),
    )
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is invoked
    with pytest.raises(RuntimeError, match="scrape failed"):
        main(
            headless=True,
            logging_level=LoggingLevel.INFO,
            default_list_size=ListSize.TESTING,
            refresh_category_lists=False,
            proxy_server=None,
            file_handler=file_handler,
            logger=logger,
            web_driver=web_driver,
        )

    # THEN: The scrape error is preserved and quit failure is only logged
    assert web_driver.called.count(("quit",)) == 1
    assert ("INFO", "WebDriver lifecycle start") in logger.records
    assert ("INFO", "WebDriver lifecycle stop") not in logger.records
    assert any(
        level == "ERROR" and "WebDriver quit failed: quit failed" in message
        for level, message in logger.records
    )


# logging_level tests
@pytest.mark.parametrize(
    "logging_level",
    [LoggingLevel.DEBUG, LoggingLevel.INFO, LoggingLevel.ERROR],
)
def test_main_logging_level_passed_to_logger(monkeypatch, logging_level):
    # GIVEN: No logger is injected and logging_level is provided
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    supermarket = DummySupermarket(logger=DummyLogger())
    monkeypatch.setattr(DummyLogger, "instances", [])
    monkeypatch.setattr("Code.main.Logger", DummyLogger)
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is called without a logger
    main(
        headless=True,
        logging_level=logging_level,
        default_list_size=ListSize.TESTING,
        proxy_server=None,
        file_handler=file_handler,
        logger=None,
        web_driver=web_driver,
    )

    # THEN: Logger is constructed once with the given logging_level
    assert len(DummyLogger.instances) == 1
    assert DummyLogger.instances[0].logging_level == logging_level


def test_main_logging_level_default_is_info(monkeypatch):
    # GIVEN: No logging_level is specified and no logger is injected
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    supermarket = DummySupermarket(logger=DummyLogger())
    monkeypatch.setattr(DummyLogger, "instances", [])
    monkeypatch.setattr("Code.main.Logger", DummyLogger)
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is called
    main(
        headless=True,
        default_list_size=ListSize.TESTING,
        proxy_server=None,
        file_handler=file_handler,
        logger=None,
        web_driver=web_driver,
    )

    # THEN: Logger defaults to LoggingLevel.INFO
    assert len(DummyLogger.instances) == 1
    assert DummyLogger.instances[0].logging_level == LoggingLevel.INFO


def test_main_injected_logger_not_replaced(monkeypatch):
    # GIVEN: A logger is injected
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    supermarket = DummySupermarket(logger=logger)
    monkeypatch.setattr(DummyLogger, "instances", [])
    monkeypatch.setattr("Code.main.Logger", DummyLogger)
    monkeypatch.setattr("Code.main.Woolworths", lambda *args, **kwargs: supermarket)

    # WHEN: main() is called with an injected logger
    main(
        headless=True,
        logging_level=LoggingLevel.ERROR,
        default_list_size=ListSize.TESTING,
        proxy_server=None,
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
    )

    # THEN: The Logger constructor is not called; the injected logger is used as-is
    assert len(DummyLogger.instances) == 0
