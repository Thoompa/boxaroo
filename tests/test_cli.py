import pytest
from cli import main
from isupermarket import ListSize
from logger import LoggingLevel
from tests.test_helpers import DummyLogger, DummyFileHandler, DummyWebDriver


@pytest.mark.parametrize(
    "list_size_enum,list_size_str",
    [
        (ListSize.TESTING, "TESTING"),
        (ListSize.FULL, "FULL"),
        (ListSize.SHORT, "SHORT"),
    ],
)
def test_main_list_size_parameter(monkeypatch, list_size_enum, list_size_str):
    # Given the application is launched with --list_size {list_size_str}
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    import woolworths

    monkeypatch.setattr(
        woolworths.Woolworths,
        "_get_all_categories",
        lambda self, ls: [f"cat-{ls.name}"],
    )
    monkeypatch.setattr(
        woolworths.Woolworths, "_get_category_data", lambda self, cat: {"products": []}
    )

    # When the application initialises
    main(
        headless=True,
        logging_level=LoggingLevel.ERROR,
        default_list_size=list_size_enum,
        proxy_server=None,
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
    )

    # Then only the {list_size_str} dataset is processed (verified by logger)
    found = any(
        list_size_str in msg for level, msg in logger.records if level == "INFO"
    )
    assert found, f"Expected log message with list size {list_size_str}"


def test_main_invalid_list_size(monkeypatch):
    # Given the application is launched with an invalid list size
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    web_driver = DummyWebDriver()
    import woolworths

    monkeypatch.setattr(
        woolworths.Woolworths,
        "_get_all_categories",
        lambda self, ls: [f"cat-{ls.name}"],
    )
    monkeypatch.setattr(
        woolworths.Woolworths, "_get_category_data", lambda self, cat: {"products": []}
    )

    # When the application initialises with an invalid enum
    # Then an exception is raised
    with pytest.raises(Exception):
        main(
            headless=True,
            logging_level=LoggingLevel.ERROR,
            default_list_size=None,  # Invalid
            proxy_server=None,
            file_handler=file_handler,
            logger=logger,
            web_driver=web_driver,
        )
