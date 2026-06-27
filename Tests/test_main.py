import pytest
from datetime import date
from Code.contracts import ListSize, Supermarket
from Code.main import main
from Code.logger import LoggingLevel
from Tests.test_helpers import (
    DummyLogger,
    DummyFileHandler,
    DummyWebDriver,
    DummySupermarket,
    DummySupermarketFactory,
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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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


def test_main_does_not_create_webdriver_when_file_handler_init_raises(monkeypatch):
    # GIVEN: output initialization fails before main can start its own browser
    logger = DummyLogger()
    monkeypatch.setattr(
        "Code.main.FileHandler",
        lambda *args, **kwargs: DummyFileHandler(error_on_init=True),
    )
    monkeypatch.setattr(
        "Code.main.WebDriver",
        lambda *args, **kwargs: DummyWebDriver(error_on_init=True),
    )

    # WHEN: main() is invoked without an injected web driver
    with pytest.raises(OSError, match="permission denied"):
        main(
            headless=True,
            logging_level=LoggingLevel.INFO,
            default_list_size=ListSize.TESTING,
            refresh_category_lists=False,
            proxy_server=None,
            file_handler=None,
            logger=logger,
            web_driver=None,
        )

    # THEN: browser lifecycle is never started on the fail-fast path
    assert ("INFO", "WebDriver lifecycle start") not in logger.records
    assert ("INFO", "WebDriver lifecycle stop") not in logger.records


@pytest.mark.parametrize("hard_driver_reset", [False, True])
def test_main_wires_webdriver_constructor_args(monkeypatch, hard_driver_reset):
    # GIVEN: No injected webdriver and a selected hard driver reset state
    logger = DummyLogger()
    captured_args = None
    captured_kwargs = None

    monkeypatch.setattr(
        "Code.main.FileHandler",
        lambda *args, **kwargs: DummyFileHandler(),
    )

    def capture_web_driver(*args, **kwargs):
        nonlocal captured_args, captured_kwargs
        captured_args = args
        captured_kwargs = kwargs
        return DummyWebDriver()

    monkeypatch.setattr("Code.main.WebDriver", capture_web_driver)
    supermarket = DummySupermarket(logger=logger)
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

    # WHEN: main() is invoked without an injected web driver
    main(
        headless=True,
        logging_level=LoggingLevel.INFO,
        default_list_size=ListSize.TESTING,
        refresh_category_lists=False,
        proxy_server="http://host:port",
        file_handler=None,
        logger=logger,
        web_driver=None,
        hard_driver_reset=hard_driver_reset,
    )

    # THEN: WebDriver receives the expected constructor arguments
    assert captured_args == ()
    assert captured_kwargs == {
        "logger": logger,
        "headless": True,
        "proxy_server": "http://host:port",
        "hard_driver_reset": hard_driver_reset,
        "max_pages_per_session": 12,
    }


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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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


def test_main_forwards_category_to_coordinator_run(monkeypatch):
    # GIVEN: A patched coordinator run method that records run() arguments
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    supermarket = DummySupermarket(logger=logger)
    run_kwargs = {}

    def dummy_run(self, **kwargs):
        run_kwargs.update(kwargs)

    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )
    monkeypatch.setattr("Code.main.ScrapeCoordinator.run", dummy_run)

    # WHEN: main() is invoked with a category override
    main(
        headless=True,
        logging_level=LoggingLevel.INFO,
        default_list_size=ListSize.FULL,
        category="fruit-veg",
        refresh_category_lists=False,
        proxy_server=None,
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
    )

    # THEN: coordinator.run() receives the selected category
    assert run_kwargs["category"] == "fruit-veg"


def test_main_uses_category_in_output_file_name_when_category_override_is_set(
    monkeypatch,
):
    # GIVEN: A run with a category override and no injected runtime dependencies
    logger = DummyLogger()
    captured = {}

    def capture_file_handler(file_name, file_path, header, logger):
        captured["file_name"] = file_name
        captured["file_path"] = file_path
        captured["header"] = header
        return DummyFileHandler()

    monkeypatch.setattr("Code.main.FileHandler", capture_file_handler)
    monkeypatch.setattr("Code.main.WebDriver", lambda *args, **kwargs: DummyWebDriver())
    monkeypatch.setattr(
        "Code.main.supermarket_factory",
        lambda *args, **kwargs: DummySupermarket(logger=logger),
    )
    category = "fruit-veg"

    # WHEN: main() is invoked with category override
    main(
        headless=True,
        logging_level=LoggingLevel.INFO,
        default_list_size=ListSize.FULL,
        category=category,
        refresh_category_lists=False,
        proxy_server=None,
        file_handler=None,
        logger=logger,
        web_driver=None,
    )

    # THEN: the output file name uses the category slug instead of list size
    expected_name = f"woolworths-{date.today()}-{category}.csv"
    assert captured["file_name"] == expected_name


def test_main_resolves_selected_supermarket_via_supermarket_factory(monkeypatch):
    # GIVEN: A selected supermarket key and a composition factory
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    selected_supermarket = Supermarket.WOOLWORTHS.value
    resolved_supermarket = DummySupermarket(logger=logger)
    factory = DummySupermarketFactory(resolved_supermarket=resolved_supermarket)

    monkeypatch.setattr(
        "Code.main.supermarket_factory",
        factory,
        raising=False,
    )

    # WHEN: main() is invoked with a selected supermarket key
    main(
        headless=True,
        logging_level=LoggingLevel.INFO,
        default_list_size=ListSize.TESTING,
        refresh_category_lists=False,
        supermarket=selected_supermarket,
        proxy_server=None,
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
    )

    # THEN: The supermarket is resolved via supermarket_factory
    assert factory.factory_calls == [Supermarket.WOOLWORTHS]
    assert resolved_supermarket.get_categories_called


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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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


def test_main_logs_category_failure_and_quits_webdriver(monkeypatch):
    # GIVEN: A category scrape fails during coordinator run
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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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
        and "Failed to scrape category 'fruit-veg': RuntimeError: scrape failed"
        in message
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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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


def test_main_quits_injected_webdriver_when_file_handler_init_raises(monkeypatch):
    # GIVEN: file-handler initialization fails before coordinator setup
    logger = DummyLogger()
    web_driver = DummyWebDriver()
    monkeypatch.setattr(
        "Code.main.FileHandler",
        lambda *args, **kwargs: DummyFileHandler(error_on_init=True),
    )

    # WHEN: main() is invoked with an injected web driver
    with pytest.raises(OSError, match="permission denied"):
        main(
            headless=True,
            logging_level=LoggingLevel.INFO,
            default_list_size=ListSize.TESTING,
            refresh_category_lists=False,
            proxy_server=None,
            file_handler=None,
            logger=logger,
            web_driver=web_driver,
        )

    # THEN: the injected web driver is still quit and no unmatched lifecycle log is emitted
    assert web_driver.called.count(("quit",)) == 1
    assert ("INFO", "WebDriver lifecycle start") not in logger.records
    assert ("INFO", "WebDriver lifecycle stop") not in logger.records


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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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
    monkeypatch.setattr(
        "Code.main.supermarket_factory", lambda *args, **kwargs: supermarket
    )

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
