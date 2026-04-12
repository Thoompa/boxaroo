import pytest
from cli import _format_eta, build_list_size_help, main
import cli as cli_module
from isupermarket import ListSize
from logger import LoggingLevel
from tests.test_helpers import (
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
    # GIVEN: The CLI is called with a valid ListSize value
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    called = {"list_size": None}

    def logic(log, ls, refresh):
        called["list_size"] = ls

    supermarket = DummySupermarket(logger, logic=logic)
    monkeypatch.setattr("cli.Woolworths", lambda *args, **kwargs: supermarket)

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
        supermarket.get_data_called
    ), "Expected get_data to be called on DummySupermarket"
    assert (
        called["list_size"] == list_size_enum
    ), f"Expected list_size {list_size_enum}, got {called['list_size']}"


# 4: Test None defaults to TESTING
def test_main_default_list_size_none(monkeypatch):
    # GIVEN: The CLI is called with default_list_size=None
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    called = {"list_size": None}

    def logic(log, ls, refresh):
        called["list_size"] = ls

    supermarket = DummySupermarket(logger, logic=logic)
    monkeypatch.setattr("cli.Woolworths", lambda *args, **kwargs: supermarket)

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
        supermarket.get_data_called
    ), "Expected get_data to be called on DummySupermarket"
    assert (
        called["list_size"] == ListSize.TESTING
    ), f"Expected list_size ListSize.TESTING, got {called['list_size']}"


def test_main_refresh_category_lists_parameter(monkeypatch):
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    supermarket = DummySupermarket(logger)
    monkeypatch.setattr("cli.Woolworths", lambda *args, **kwargs: supermarket)

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

    assert supermarket.get_data_called
    assert supermarket.last_refresh_category_lists is True


def test_main_refresh_category_lists_default_false(monkeypatch):
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    supermarket = DummySupermarket(logger)
    monkeypatch.setattr("cli.Woolworths", lambda *args, **kwargs: supermarket)

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

    assert supermarket.get_data_called
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
    assert _format_eta(total_products) == expected


def test_build_list_size_help_uses_formatted_eta(monkeypatch):
    monkeypatch.setattr(
        "cli._load_list_product_totals",
        lambda: {
            "testing": 108,  # 27s
            "short": 600,  # 2m 30s
            "medium": 14400,  # 1h
            "long": 14892,  # 1h 2m 3s
            "full": 0,  # 0s
        },
    )

    help_text = build_list_size_help()

    assert "TESTING ~27s" in help_text
    assert "SHORT ~2m 30s" in help_text
    assert "MEDIUM ~1h" in help_text
    assert "LONG ~1h 2m 3s" in help_text
    assert "FULL ~0s" in help_text


def test_build_list_size_help_with_no_cache_returns_all_na(monkeypatch):
    """
    Test that when the category cache is missing/empty,
    build_list_size_help shows 'n/a' for all list sizes.
    """
    monkeypatch.setattr(cli_module, "_load_list_product_totals", lambda: {})

    help_text = build_list_size_help()

    assert "TESTING n/a" in help_text
    assert "SHORT n/a" in help_text
    assert "MEDIUM n/a" in help_text
    assert "LONG n/a" in help_text
    assert "FULL n/a" in help_text
