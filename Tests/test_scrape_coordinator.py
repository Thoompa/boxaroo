from Code.contracts import CategoryStatus, ListSize
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

    # AND: run summary reports an all-success baseline with no failures
    assert any(
        "Run summary" in msg
        and "categories_attempted=2" in msg
        and "categories_succeeded=2" in msg
        and "categories_failed=0" in msg
        and "products_found=3" in msg
        and "products_scraped=3" in msg
        and "incomplete_products=0" in msg
        and "took=" in msg
        for msg in info_messages
    )


def test_coordinator_run_logs_summary_when_all_categories_raise(monkeypatch):
    # GIVEN: three categories where every category scrape raises an error
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

    def fake_get_category_data(category_name: str, on_rows=None):
        attempted_categories.append(category_name)
        raise RuntimeError(f"{category_name} failed")

    monkeypatch.setattr(supermarket, "get_category_data", fake_get_category_data)

    # WHEN: coordinator.run() is called
    coordinator.run(list_size=ListSize.TESTING)

    # THEN: all categories are attempted and no category payloads are persisted
    assert attempted_categories == ["fruit-veg", "pantry", "bakery"]
    assert len(file_handler.saved) == 0

    # AND: failures include exception class context for diagnosis
    error_messages = [msg for level, msg in logger.records if level == "ERROR"]
    assert any("RuntimeError" in msg for msg in error_messages)

    # AND: run summary reflects a full-failure run with zero scraped products
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any(
        "Run summary" in msg
        and "categories_attempted=3" in msg
        and "categories_succeeded=0" in msg
        and "categories_failed=3" in msg
        and "products_found=0" in msg
        and "products_scraped=0" in msg
        and "incomplete_products=0" in msg
        and "took=" in msg
        for msg in info_messages
    )


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

    def fake_get_category_data(category_name: str, on_rows=None):
        if category_name == "pantry":
            return ["invalid-payload"]
        if category_name == "fruit-veg":
            on_rows([["Apple each", "$1.00", "$1.00 / 1EA", ""]])
            return {
                "category": "fruit-veg",
                "total": 1,
                "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
                "incomplete_items": [],
                "scraped": 1,
                "incomplete": 0,
            }
        on_rows([["Bread each", "$3.50", "$3.50 / 1EA", ""]])
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
    # GIVEN: three categories with zero found totals where one returns an empty products list
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger,
        categories=["fruit-veg", "pantry", "bakery"],
        category_data={
            "fruit-veg": {
                "category": "fruit-veg",
                "total": 0,
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
                "total": 0,
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

    # THEN: the empty category stores nothing, later categories are not
    #       skipped, and the total reflects only real products
    assert len(file_handler.saved) == 2
    assert file_handler.saved[0] == [["Apple each", "$1.00", "$1.00 / 1EA", ""]]
    assert file_handler.saved[1] == [["Bread each", "$3.50", "$3.50 / 1EA", ""]]
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any("Successfully scraped 2 products" in msg for msg in info_messages)

    # AND: run summary reports zero found products while preserving scraped totals
    assert any(
        "Run summary" in msg
        and "categories_attempted=3" in msg
        and "categories_succeeded=3" in msg
        and "categories_failed=0" in msg
        and "products_found=0" in msg
        and "products_scraped=2" in msg
        and "incomplete_products=0" in msg
        and "took=" in msg
        for msg in info_messages
    )


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

    # THEN: category data is persisted and an INFO message records adapter identity
    assert len(file_handler.saved) == 1
    assert file_handler.saved[0] == [["Apple each", "$1.00", "$1.00 / 1EA", ""]]
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any("Scraping DummySupermarket categories" in msg for msg in info_messages)

    # AND: run summary reports the single-category baseline
    assert any(
        "Run summary" in msg
        and "categories_attempted=1" in msg
        and "categories_succeeded=1" in msg
        and "categories_failed=0" in msg
        and "products_found=1" in msg
        and "products_scraped=1" in msg
        and "incomplete_products=0" in msg
        and "took=" in msg
        for msg in info_messages
    )


def test_coordinator_run_logs_summary_when_no_categories_are_returned():
    # GIVEN: a supermarket that returns no categories for the selected list size
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger,
        categories=[],
        category_data={},
    )
    coordinator = ScrapeCoordinator(
        supermarket=supermarket,
        logger=logger,
        file_handler=file_handler,
    )

    # WHEN: coordinator.run() is called
    coordinator.run(list_size=ListSize.TESTING)

    # THEN: no category payloads are persisted
    assert file_handler.saved == []

    # AND: run summary is still emitted with zero totals
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any(
        "Run summary" in msg
        and "categories_attempted=0" in msg
        and "categories_succeeded=0" in msg
        and "categories_failed=0" in msg
        and "products_found=0" in msg
        and "products_scraped=0" in msg
        and "incomplete_products=0" in msg
        and "took=" in msg
        for msg in info_messages
    )


def test_coordinator_run_logs_rollup_summary_with_category_metrics():
    # GIVEN: two successful categories and one failed category
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger,
        categories=["fruit-veg", "pantry", "bakery"],
        category_data={
            "fruit-veg": {
                "category": "fruit-veg",
                "total": 5,
                "products": [["Apple each", "$1.00", "$1.00 / 1EA", ""]],
                "incomplete_items": [],
                "scraped": 1,
                "incomplete": 0,
            },
            "bakery": {
                "category": "bakery",
                "total": 3,
                "products": [
                    ["Bread each", "$3.50", "$3.50 / 1EA", ""],
                    ["Bagel each", "$1.50", "$1.50 / 1EA", ""],
                ],
                "incomplete_items": [{"name": "Bagel each", "missing": ["promotion"]}],
                "scraped": 2,
                "incomplete": 1,
            },
        },
    )

    def fake_get_category_data(category_name: str, on_rows=None):
        if category_name == "pantry":
            raise RuntimeError("pantry failed")
        data = supermarket.category_data[category_name]
        on_rows(data["products"])
        return data

    supermarket.get_category_data = fake_get_category_data
    coordinator = ScrapeCoordinator(
        supermarket=supermarket,
        logger=logger,
        file_handler=file_handler,
    )

    # WHEN: coordinator.run() is called
    coordinator.run(list_size=ListSize.SHORT)

    # THEN: run summary includes attempted/success/failed totals and elapsed runtime
    info_messages = [msg for level, msg in logger.records if level == "INFO"]
    assert any(
        "Run summary" in msg
        and "categories_attempted=3" in msg
        and "categories_succeeded=2" in msg
        and "categories_failed=1" in msg
        and "products_found=8" in msg
        and "products_scraped=3" in msg
        and "incomplete_products=1" in msg
        and "took=" in msg
        for msg in info_messages
    )


def test_coordinator_run_warns_when_category_has_found_but_zero_scraped():
    # GIVEN: a category payload where found products are non-zero but scraped is zero
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger,
        categories=["fruit-veg"],
        category_data={
            "fruit-veg": {
                "category": "fruit-veg",
                "total": 12,
                "products": [],
                "incomplete_items": [],
                "scraped": 0,
                "incomplete": 0,
            }
        },
    )
    coordinator = ScrapeCoordinator(
        supermarket=supermarket,
        logger=logger,
        file_handler=file_handler,
    )

    # WHEN: coordinator.run() is called
    coordinator.run(list_size=ListSize.TESTING)

    # THEN: a warning is logged to highlight potential scrape coverage issues
    warning_messages = [msg for level, msg in logger.records if level == "WARNING"]
    assert any(
        "Category fruit-veg returned found=12 but scraped=0" in msg
        for msg in warning_messages
    )


# ============================================================
# Honest run reporting (known-issues #1)
# ============================================================


def _category_payload(status, rows, total, error=None):
    return {
        "category": "baby",
        "total": total,
        "products": rows,
        "incomplete_items": [],
        "scraped": len(rows),
        "incomplete": 0,
        "status": status,
        "error": error,
        "pages_committed": 2,
        "rows_stored": len(rows),
    }


def _run_single_category(payload):
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger, categories=["baby"], category_data={"baby": payload}
    )
    coordinator = ScrapeCoordinator(supermarket, logger, file_handler)
    summary = coordinator.run(list_size=ListSize.TESTING)
    return summary, logger, file_handler


def test_coordinator_run_reports_failed_category_instead_of_success():
    # GIVEN: a category that crashed before saving anything
    payload = _category_payload(CategoryStatus.FAILED, [], 0, "TimeoutException")

    # WHEN: the coordinator runs it
    summary, logger, file_handler = _run_single_category(payload)

    # THEN: the run is not ok and the summary counts a failure, not a success
    assert summary.ok is False
    assert (summary.categories_succeeded, summary.categories_failed) == (0, 1)
    info = [msg for level, msg in logger.records if level == "INFO"]
    assert any(
        "Run summary" in m
        and "categories_succeeded=0" in m
        and "categories_partial=0" in m
        and "categories_failed=1" in m
        for m in info
    )
    assert not any("Successfully scraped" in m for m in info)

    # AND: the failure is logged against the category and recorded in the status file
    errors = [msg for level, msg in logger.records if level == "ERROR"]
    assert any("Category baby FAILED" in m and "TimeoutException" in m for m in errors)
    assert file_handler.statuses["baby"]["state"] == "failed"
    assert file_handler.statuses["baby"]["error"] == "TimeoutException"


def test_coordinator_run_reports_partial_category_and_counts_its_rows():
    # GIVEN: a category that crashed after two rows had been read
    rows = [["A", "$1", "$1 / 1EA", ""], ["B", "$2", "$2 / 1EA", ""]]
    payload = _category_payload(CategoryStatus.PARTIAL, rows, 10, "tab crashed")

    # WHEN: the coordinator runs it
    summary, logger, file_handler = _run_single_category(payload)

    # THEN: the rows that were saved are counted, but the run is not ok
    assert summary.ok is False
    assert (summary.categories_partial, summary.categories_failed) == (1, 0)
    assert summary.products_scraped == 2
    info = [msg for level, msg in logger.records if level == "INFO"]
    assert any("categories_partial=1" in m and "products_scraped=2" in m for m in info)
    assert not any("Successfully scraped" in m for m in info)

    # AND: the status file says how far it got
    status = file_handler.statuses["baby"]
    assert status["state"] == "partial"
    assert status["rows_written"] == 2
    assert status["pages_committed"] == 2
    assert status["expected_total"] == 10


def test_coordinator_run_is_ok_and_writes_complete_status_for_clean_category():
    # GIVEN: a category that finished cleanly
    rows = [["A", "$1", "$1 / 1EA", ""]]
    payload = _category_payload(CategoryStatus.COMPLETE, rows, 1)

    # WHEN: the coordinator runs it
    summary, logger, file_handler = _run_single_category(payload)

    # THEN: the run is ok and its status is recorded as complete
    assert summary.ok is True
    assert file_handler.statuses["baby"]["state"] == "complete"


def test_coordinator_run_saves_rows_as_the_adapter_reports_them_even_if_it_then_raises():
    # GIVEN: an adapter that streams one page then raises
    file_handler = DummyFileHandler()
    logger = DummyLogger()
    supermarket = DummySupermarket(logger=logger, categories=["baby"])

    def streams_then_raises(category_name, on_rows=None):
        on_rows([["A", "$1", "$1 / 1EA", ""]])
        raise RuntimeError("boom")

    supermarket.get_category_data = streams_then_raises
    coordinator = ScrapeCoordinator(supermarket, logger, file_handler)

    # WHEN: the coordinator runs
    summary = coordinator.run(list_size=ListSize.TESTING)

    # THEN: the streamed row was stored and the category is partial, not failed
    assert file_handler.saved == [[["A", "$1", "$1 / 1EA", ""]]]
    assert summary.categories_partial == 1
    assert summary.products_scraped == 1


def test_coordinator_run_survives_a_status_write_error():
    # GIVEN: a file handler whose status write fails
    file_handler = DummyFileHandler()

    def failing_write_status(category, status):
        raise OSError("disk full")

    file_handler.write_status = failing_write_status
    logger = DummyLogger()
    supermarket = DummySupermarket(
        logger=logger, products_to_store=[["A", "1", "1", ""]]
    )
    coordinator = ScrapeCoordinator(supermarket, logger, file_handler)

    # WHEN: the coordinator runs
    summary = coordinator.run(list_size=ListSize.TESTING)

    # THEN: the run still finishes and the error is logged
    assert summary.categories_succeeded == 1
    assert any(
        level == "ERROR" and "Could not write status" in msg
        for level, msg in logger.records
    )
