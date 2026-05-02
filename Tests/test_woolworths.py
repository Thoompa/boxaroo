import pytest

from Code.woolworths import Woolworths
from Tests.test_helpers import (
    DummyFileHandler,
    DummyLogger,
    DummyProductParser,
    DummyWebDriver,
)


@pytest.fixture
def logger():
    return DummyLogger()


@pytest.fixture
def file_handler():
    return DummyFileHandler()


@pytest.fixture
def parser():
    return DummyProductParser()


@pytest.fixture
def web_driver():
    driver = DummyWebDriver()
    driver.script_response = ""
    return driver


@pytest.fixture
def woolworths(file_handler, logger, web_driver, parser):
    return Woolworths(
        file_handler=file_handler,
        logger=logger,
        web_driver=web_driver,
        product_parser=parser,
    )


def test_cache_path_source_of_truth_is_category_list_service(woolworths, tmp_path):
    # GIVEN: a cache path set on the category list service
    cache_file = tmp_path / "woolworths-category-lists.json"
    woolworths.category_list_service.cache_path = str(cache_file)

    # WHEN: the cache path is accessed
    # THEN: the value is retrieved from the category list service
    assert woolworths.category_list_service.cache_path == str(cache_file)
    assert not hasattr(woolworths, "category_lists_cache_path")
