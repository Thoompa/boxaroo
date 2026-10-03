import json

import pytest

from Code.contracts import ListSize
from Code.product_parser import ProductParser
from Tests.test_helpers import DummyFileHandler
from Code.woolworths import Woolworths


@pytest.mark.live
def test_live_woolworths_category_discovery_count_classification_and_cache(
    tmp_path, live_driver, live_logger
):
    driver = live_driver
    file_handler = DummyFileHandler()
    parser = ProductParser(logger=live_logger)

    woolworths = Woolworths(
        file_handler=file_handler,
        logger=live_logger,
        web_driver=driver,
        product_parser=parser,
    )
    cache_file = tmp_path / "woolworths-category-lists.json"
    woolworths.category_list_service.cache_path = str(cache_file)

    # Force a real refresh path: discover categories, count each category page, classify, and persist cache.
    full_list = woolworths.get_categories(
        list_size=ListSize.FULL, refresh_category_lists=True
    )
    short_list = woolworths.get_categories(
        list_size=ListSize.SHORT, refresh_category_lists=False
    )
    testing_list = woolworths.get_categories(
        list_size=ListSize.TESTING, refresh_category_lists=False
    )

    assert isinstance(full_list, list)
    assert isinstance(short_list, list)
    assert isinstance(testing_list, list)
    assert len(full_list) > 0, (
        "No categories discovered from the live site; the browse menu markup "
        "has probably changed (see Logs/live-test-failures/ and the printed log)"
    )
    assert len(testing_list) == 1

    # Logical list relationship guarantees regardless of live count drift.
    assert set(short_list).issubset(set(full_list))
    assert set(testing_list).issubset(set(short_list))

    assert cache_file.exists()
    cache_data = json.loads(cache_file.read_text(encoding="utf-8"))

    for key in [
        "testing",
        "short",
        "medium",
        "long",
        "full",
        "supermarket_categories",
        "list_product_totals",
        "category_product_totals",
    ]:
        assert key in cache_data
    assert cache_data["full"] == full_list
    assert cache_data["short"] == short_list
    assert cache_data["testing"] == testing_list
    assert len(cache_data["supermarket_categories"]) >= len(full_list)
