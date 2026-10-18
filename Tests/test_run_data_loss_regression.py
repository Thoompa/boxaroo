"""Regression guard for known-issues #1: failed runs lost all data and still
reported success.

These tests run the real coordinator, normaliser and file handler against a
driver double that crashes part-way, then check what is on disk and what the run
reports. If a refactor brings the old behaviour back, they fail.
"""

import csv
import json

from Code.contracts import CategoryData, ISuperMarket, ListSize, RowSink
from Code.scrape_coordinator import ScrapeCoordinator
from Tests.test_helpers import (
    DummyLogger,
    DummyPagedWebDriver,
    EchoProductParser,
    make_file_handler,
    make_woolworths_category_data_normaliser,
)


class NormaliserBackedSupermarket(ISuperMarket):
    """Minimal adapter wiring the real normaliser to the coordinator."""

    def __init__(self, normaliser, categories):
        self.normaliser = normaliser
        self.categories = categories

    def get_categories(
        self, list_size=ListSize.FULL, refresh_category_lists=False, category=None
    ):
        return self.categories

    def get_category_data(
        self, category_name: str, on_rows: RowSink | None = None
    ) -> CategoryData:
        return self.normaliser.get_category_data(category_name, on_rows=on_rows)


def _run(tmp_path, web_driver):
    handler, _ = make_file_handler(tmp_path)
    logger = DummyLogger()
    normaliser = make_woolworths_category_data_normaliser(
        logger=logger, web_driver=web_driver, product_parser=EchoProductParser()
    )
    supermarket = NormaliserBackedSupermarket(normaliser, ["baby"])
    summary = ScrapeCoordinator(supermarket, logger, handler).run(
        list_size=ListSize.TESTING
    )
    return summary, logger


def _csv_names(tmp_path):
    with open(tmp_path / "out.csv", newline="") as f:
        return [row[0] for row in list(csv.reader(f))[1:]]


def _summary_line(logger):
    return next(
        msg for level, msg in logger.records if level == "INFO" and "Run summary" in msg
    )


def test_crash_mid_category_keeps_earlier_pages_on_disk_and_is_not_reported_as_success(
    tmp_path,
):
    # GIVEN: a category of three pages where the tab crashes on page 3
    web_driver = DummyPagedWebDriver(
        pages=[["A", "B"], ["C", "D"], ["E", "F"]], fail_after_pages=2
    )
    web_driver.category_total_items = 6

    # WHEN: the run completes
    summary, logger = _run(tmp_path, web_driver)

    # THEN: the rows from the pages read before the crash are in the CSV
    assert _csv_names(tmp_path) == ["A", "B", "C", "D"]

    # AND: the run is not ok and the summary does not claim a clean success
    assert summary.ok is False
    line = _summary_line(logger)
    assert "categories_succeeded=0" in line
    assert "categories_partial=1" in line
    assert "products_scraped=4" in line
    assert not any("Successfully scraped" in msg for _, msg in logger.records)

    # AND: the status file says what happened
    status = json.loads((tmp_path / "out.csv.status.json").read_text())
    assert status["categories"]["baby"]["state"] == "partial"
    assert "tab crashed" in status["categories"]["baby"]["error"]
    assert status["categories"]["baby"]["rows_written"] == 4


def test_crash_before_any_page_is_reported_as_failed_not_as_an_empty_success(
    tmp_path,
):
    # GIVEN: a category that crashes before the first page is read
    web_driver = DummyPagedWebDriver(pages=[["A"]], fail_after_pages=0)
    web_driver.category_total_items = 10

    # WHEN: the run completes
    summary, logger = _run(tmp_path, web_driver)

    # THEN: nothing is stored and the run reports one failed category
    assert _csv_names(tmp_path) == []
    assert summary.ok is False
    line = _summary_line(logger)
    assert "categories_failed=1" in line
    assert "categories_succeeded=0" in line


def test_clean_run_stores_every_page_and_reports_success(tmp_path):
    # GIVEN: a category that completes without error
    web_driver = DummyPagedWebDriver(pages=[["A", "B"], ["C"]])
    web_driver.category_total_items = 3

    # WHEN: the run completes
    summary, logger = _run(tmp_path, web_driver)

    # THEN: all rows are stored and the run is ok
    assert _csv_names(tmp_path) == ["A", "B", "C"]
    assert summary.ok is True
    assert "categories_succeeded=1" in _summary_line(logger)
    assert "categories_failed=0" in _summary_line(logger)


def test_run_summary_line_keeps_the_fields_log_readers_depend_on(tmp_path):
    # GIVEN: any finished run
    web_driver = DummyPagedWebDriver(pages=[["A"]])
    web_driver.category_total_items = 1

    # WHEN: the run completes
    _, logger = _run(tmp_path, web_driver)

    # THEN: the summary line still carries each field the log analysis reads
    line = _summary_line(logger)
    for field in (
        "categories_attempted=",
        "categories_succeeded=",
        "categories_partial=",
        "categories_failed=",
        "products_found=",
        "products_scraped=",
        "incomplete_products=",
        "took=",
    ):
        assert field in line
