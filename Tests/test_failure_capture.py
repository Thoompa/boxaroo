import json
import re
from datetime import datetime

from selenium.common.exceptions import TimeoutException, WebDriverException

import Code.web_driver as web_driver_module
from Code import diagnostics, failure_capture
from Code.web_driver import WebDriver
from Tests.test_helpers import (
    DummyBrokenPsutil,
    DummyCaptureSession,
    DummyDriverFactory,
    DummySeleniumSession,
    DummyUnresponsiveSession,
    DummyWait,
    DummyWebDriverHarness,
    ReadTimeoutError,
)

URLS = [
    "https://shop.test/browse/a",
    "https://shop.test/browse/a?pageNumber=2",
]
PAGES = [["A", "B"], ["C", "D"]]
FIXED_NOW = datetime(2026, 11, 11, 8, 2, 12)

ACCESS_DENIED_PAGE = """
<html><head><title>Access Denied</title></head><body>
<h1>Access Denied</h1>You don't have permission to access this server.
Reference #18.2b3c1d02.1700000000.abc
</body></html>
"""


def _collect(elements, *, page_number):
    return {"products": [tile["text"] for tile in elements], "incomplete_items": []}


def _quiet(monkeypatch):
    monkeypatch.setattr(web_driver_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(web_driver_module.random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(web_driver_module, "WebDriverWait", DummyWait)


def _capture_driver(**session_kwargs):
    driver = DummyWebDriverHarness()
    driver.driver = DummyCaptureSession(pages=PAGES, page_urls=URLS, **session_kwargs)
    driver._create_fresh_driver = DummyDriverFactory(pages=PAGES, page_urls=URLS)
    driver._category_name = "dairy"
    return driver


def _fail_page_one_once(monkeypatch):
    class WaitThatTimesOutOnce(DummyWait):
        timeouts = 0

        def until(self, condition):
            if WaitThatTimesOutOnce.timeouts < 1:
                WaitThatTimesOutOnce.timeouts += 1
                raise TimeoutException("tiles did not load")
            return super().until(condition)

    monkeypatch.setattr(web_driver_module, "WebDriverWait", WaitThatTimesOutOnce)


def _captures(tmp_path, suffix):
    return sorted((tmp_path / "captures").rglob(f"*{suffix}"))


# ============================================================
# Failure capture
# ============================================================


def test_a_timeout_failure_saves_a_screenshot_source_and_metadata(
    monkeypatch, tmp_path
):
    # GIVEN: the tiles never appear on page 1 of the first driver
    _quiet(monkeypatch)
    _fail_page_one_once(monkeypatch)
    driver = _capture_driver(body_text=ACCESS_DENIED_PAGE)

    # WHEN: the products are retrieved
    result = WebDriver.get_products(driver, _collect, category_name="dairy")

    # THEN: the category still completes after the retry
    assert result["products"] == ["A", "B", "C", "D"]

    # AND: a png, html and json were written with a shared stem
    pngs, htmls, jsons = (
        _captures(tmp_path, ext) for ext in (".png", ".html", ".json")
    )
    assert len(pngs) == len(htmls) == len(jsons) == 1
    assert pngs[0].stem == jsons[0].stem
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", jsons[0].parent.name)
    assert jsons[0].stem.startswith("dairy-p1-a1-")

    # AND: the metadata describes the failure and the page
    meta = json.loads(jsons[0].read_text())
    assert meta["exception"] == {
        "type": "TimeoutException",
        "message": "tiles did not load",
    }
    assert meta["requested_url"] == "https://shop.test/browse/a?pageNumber=1"
    assert meta["document_title"] == "Dummy shop"
    assert meta["ready_state"] == "complete"
    assert (meta["tiles_total"], meta["tiles_in_grid"]) == (72, 36)
    assert meta["challenge_markers"] == ["access denied", "reference #"]
    assert meta["console_errors"][0]["message"].startswith("net::ERR_FAILED")
    assert len(meta["console_errors"]) == 1
    assert meta["screenshot"] == "saved"
    assert "stats" in meta

    # AND: one warning names the saved stem, and the retry line carries stats
    warnings = [m for level, m in driver.logger.records if level == "WARNING"]
    assert any(m.startswith("Failure capture saved: ") for m in warnings)
    retry = next(m for m in warnings if "Page retry 1/3 on page 1" in m)
    assert "| stats: tiles_dom=" in retry


def test_a_failed_screenshot_is_recorded_and_the_retry_still_happens(
    monkeypatch, tmp_path
):
    # GIVEN: the tab has crashed, so the screenshot call raises
    _quiet(monkeypatch)
    driver = _capture_driver(screenshot_error=WebDriverException("tab crashed"))
    original_find = driver.driver.find_elements
    state = {"raised": 0}

    def crash_once(by, value):
        if state["raised"] == 0:
            state["raised"] += 1
            raise WebDriverException("tab crashed")
        return original_find(by, value)

    driver.driver.find_elements = crash_once

    # WHEN: the products are retrieved
    result = WebDriver.get_products(driver, _collect, category_name="dairy")

    # THEN: the original exception still drove a normal retry
    assert result["products"] == ["A", "B", "C", "D"]
    assert result.get("retries") == 1

    # AND: the JSON records the screenshot failure instead of raising
    meta = json.loads(_captures(tmp_path, ".json")[0].read_text())
    assert meta["screenshot"].startswith("failed: WebDriverException")
    assert "tab crashed" in meta["screenshot"]
    assert meta["exception"]["type"] == "WebDriverException"
    assert _captures(tmp_path, ".png") == []


def test_a_failure_past_the_retry_budget_is_still_captured_and_not_retried(
    monkeypatch, tmp_path
):
    # GIVEN: a plain driver whose probes all fail, and a category budget already spent
    _quiet(monkeypatch)
    driver = DummyWebDriverHarness()
    driver.driver = DummySeleniumSession(pages=PAGES, page_urls=URLS)
    driver.category_retries = web_driver_module.CATEGORY_RETRY_BUDGET

    # WHEN: the budget check runs for a failure
    retried = WebDriver._begin_retry(driver, TimeoutException("slow"), 1, "x", "y")

    # THEN: it simply declines to retry, and a capture was still attempted
    assert retried is False
    assert len(_captures(tmp_path, ".json")) == 1


def test_captures_stop_at_the_per_category_cap(tmp_path):
    # GIVEN: a capturer allowed two captures
    capturer = failure_capture.FailureCapturer(
        root=tmp_path, clock=lambda: FIXED_NOW, max_captures=2
    )
    session = DummyCaptureSession(pages=PAGES, page_urls=URLS)

    # WHEN: four failures are captured
    stems = [
        capturer.capture(
            session,
            category="dairy",
            page=1,
            attempt=attempt,
            exc=TimeoutException("slow"),
            requested_url=URLS[0],
            grid_selector="x",
        )
        for attempt in range(1, 5)
    ]

    # THEN: only the first two are written
    assert [stem is not None for stem in stems] == [True, True, False, False]
    assert len(list(tmp_path.rglob("*.json"))) == 2
    assert stems[0].endswith("dairy-p1-a1-080212")


def test_a_capture_that_cannot_write_returns_none_instead_of_raising(tmp_path):
    # GIVEN: a capture root that is a file, so its directory cannot be created
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    capturer = failure_capture.FailureCapturer(root=blocker, clock=lambda: FIXED_NOW)

    # WHEN: a failure is captured
    stem = capturer.capture(
        DummyCaptureSession(pages=PAGES, page_urls=URLS),
        category="dairy",
        page=1,
        attempt=1,
        exc=RuntimeError("boom"),
        requested_url=None,
        grid_selector="x",
    )

    # THEN: nothing is raised and nothing is reported saved
    assert stem is None


def test_an_oversized_page_source_is_truncated_and_noted(tmp_path):
    # GIVEN: a page source larger than the cap
    capturer = failure_capture.FailureCapturer(
        root=tmp_path, clock=lambda: FIXED_NOW, max_source_bytes=100
    )
    session = DummyCaptureSession(pages=PAGES, page_urls=URLS, page_source="x" * 5000)

    # WHEN: a failure is captured
    stem = capturer.capture(
        session,
        category="dairy",
        page=1,
        attempt=1,
        exc=RuntimeError("boom"),
        requested_url=None,
        grid_selector="x",
    )

    # THEN: the html is cut to the cap and the JSON says so
    assert (
        len((tmp_path / "2026-11-11" / "dairy-p1-a1-080212.html").read_bytes()) == 100
    )
    meta = json.loads((tmp_path / "2026-11-11" / "dairy-p1-a1-080212.json").read_text())
    assert meta["page_source"] == "truncated from 5000 bytes to 100"
    assert stem is not None


# ============================================================
# Challenge markers
# ============================================================


def test_challenge_markers_are_found_in_an_access_denied_page():
    # GIVEN: the text and HTML of an Akamai-style block page
    # WHEN: it is searched for challenge markers
    markers = failure_capture.find_challenge_markers(ACCESS_DENIED_PAGE, "")

    # THEN: the block page's phrases are reported, case-insensitively
    assert markers == ["access denied", "reference #"]


def test_no_challenge_markers_are_found_in_a_normal_page():
    # GIVEN: an ordinary product page
    page = "<html><body>Fresh milk 2L $3.00 Add to cart</body></html>"

    # WHEN: it is searched for challenge markers
    markers = failure_capture.find_challenge_markers("Fresh milk 2L", page)

    # THEN: none are reported
    assert markers == []


# ============================================================
# Resource timing summary
# ============================================================


def test_resource_summary_reports_error_and_zero_status_entries():
    # GIVEN: resource entries: OK, a 503, a failed request, and a cached zero-status
    entries = [
        {"name": "https://shop.test/a.js", "status": 200, "transfer_size": 10},
        {
            "name": "https://shop.test/apis/ui/browse?x=1",
            "status": 503,
            "transfer_size": 0,
            "duration_ms": 1200,
        },
        {
            "name": "https://shop.test/apis/ui/other?token=secret",
            "status": 0,
            "transfer_size": 0,
            "duration_ms": 30,
        },
        {"name": "https://shop.test/cached.js", "status": 0, "transfer_size": 300},
        {"name": "https://shop.test/old.js", "status": None, "transfer_size": 0},
    ]

    # WHEN: they are summarised
    summary = failure_capture.summarize_resource_timing(entries)

    # THEN: the 503 and the empty zero-status entry are listed without query strings
    assert summary["total"] == 5
    assert summary["suspect_total"] == 2
    assert summary["suspect"] == [
        {
            "host": "shop.test",
            "path": "/apis/ui/browse",
            "status": 503,
            "duration_ms": 1200,
        },
        {
            "host": "shop.test",
            "path": "/apis/ui/other",
            "status": 0,
            "duration_ms": 30,
        },
    ]


def test_resource_summary_lists_at_most_twenty_entries():
    # GIVEN: thirty failing entries
    entries = [
        {"name": f"https://shop.test/{n}", "status": 500, "transfer_size": 0}
        for n in range(30)
    ]

    # WHEN: they are summarised
    summary = failure_capture.summarize_resource_timing(entries)

    # THEN: all are counted but only twenty are listed
    assert summary["suspect_total"] == 30
    assert len(summary["suspect"]) == 20


# ============================================================
# Unresponsive browser and capture limit
# ============================================================


def _capture(capturer, session, exc):
    return capturer.capture(
        session,
        category="dairy",
        page=1,
        attempt=1,
        exc=exc,
        requested_url=None,
        grid_selector="x",
    )


def test_probing_stops_after_the_first_read_timeout(tmp_path):
    # GIVEN: a browser that hangs, discovered on the first probe
    session = DummyUnresponsiveSession()
    capturer = failure_capture.FailureCapturer(root=tmp_path, clock=lambda: FIXED_NOW)

    # WHEN: a failure that was not itself a read timeout is captured
    stem = _capture(capturer, session, TimeoutException("tiles did not load"))

    # THEN: only the first probe touched the driver; the rest are skipped
    assert session.calls == ["current_url"]
    meta = json.loads(open(stem + ".json").read())
    assert meta["current_url"].startswith("failed: ReadTimeoutError")
    assert meta["screenshot"] == failure_capture.UNRESPONSIVE_NOTE
    assert meta["resources"] == failure_capture.UNRESPONSIVE_NOTE


def test_a_read_timeout_failure_never_touches_the_driver(tmp_path):
    # GIVEN: a failure that is itself a read timeout
    session = DummyUnresponsiveSession()
    capturer = failure_capture.FailureCapturer(root=tmp_path, clock=lambda: FIXED_NOW)

    # WHEN: it is captured and its stats are collected
    stem = _capture(capturer, session, ReadTimeoutError("Read timed out"))
    stats = diagnostics.collect_stats(
        session, probe_driver=False, psutil_module=DummyBrokenPsutil()
    )

    # THEN: no driver call was made and the JSON still exists
    assert session.calls == []
    assert stats["driver_unresponsive"] is True
    assert json.loads(open(stem + ".json").read())["exception"]["type"] == (
        "ReadTimeoutError"
    )


def test_a_capture_skipped_at_the_limit_is_logged(monkeypatch, tmp_path):
    # GIVEN: a driver whose capturer is already full
    _quiet(monkeypatch)
    driver = _capture_driver()
    driver._failure_capturer = failure_capture.FailureCapturer(max_captures=0)

    # WHEN: a failure is captured
    WebDriver._capture_failure(driver, TimeoutException("slow"), 1)

    # THEN: the skip is warned about and nothing is written
    assert any(
        level == "WARNING" and "Failure capture skipped: limit of 0" in message
        for level, message in driver.logger.records
    )
    assert _captures(tmp_path, ".json") == []
