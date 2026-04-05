import json
import os
import tomllib

import pytest

from isupermarket import ListSize
from tests.test_helpers import DummyFileHandler, DummyLogger
from web_driver import WebDriver
from woolworths import Woolworths


def _is_live_test_enabled() -> bool:
    project_root = os.path.dirname(os.path.dirname(__file__))
    pyproject_path = os.path.join(project_root, "pyproject.toml")

    try:
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        return bool(
            config.get("tool", {})
            .get("boxaroo", {})
            .get("tests", {})
            .get("run_live_woolworths", False)
        )
    except Exception:
        return False


@pytest.mark.skipif(
    not _is_live_test_enabled(),
    reason="Enable [tool.boxaroo.tests].run_live_woolworths in pyproject.toml to run live website integration test.",
)
def test_live_woolworths_category_discovery_count_classification_and_cache(tmp_path):
    logger = DummyLogger()
    file_handler = DummyFileHandler()
    driver = WebDriver(headless=False)

    try:
        woolworths = Woolworths(
            file_handler=file_handler, logger=logger, web_driver=driver
        )
        cache_file = tmp_path / "woolworths-category-lists.json"
        woolworths.category_lists_cache_path = str(cache_file)

        # Force a real refresh path: discover categories, count each category page, classify, and persist cache.
        full_list = woolworths._get_all_categories(
            list_size=ListSize.FULL, refresh_category_lists=True
        )
        short_list = woolworths._get_all_categories(
            list_size=ListSize.SHORT, refresh_category_lists=False
        )
        testing_list = woolworths._get_all_categories(
            list_size=ListSize.TESTING, refresh_category_lists=False
        )

        assert isinstance(full_list, list)
        assert isinstance(short_list, list)
        assert isinstance(testing_list, list)
        assert len(full_list) > 0
        assert len(testing_list) == 1

        # Logical list relationship guarantees regardless of live count drift.
        assert set(short_list).issubset(set(full_list))
        assert set(testing_list).issubset(set(short_list))

        assert cache_file.exists()
        cache_data = json.loads(cache_file.read_text(encoding="utf-8"))

        assert sorted(cache_data.keys()) == [
            "full",
            "short",
            "supermarket_categories",
            "testing",
        ]
        assert cache_data["full"] == full_list
        assert cache_data["short"] == short_list
        assert cache_data["testing"] == testing_list
        assert len(cache_data["supermarket_categories"]) >= len(full_list)
    finally:
        driver.quit()
