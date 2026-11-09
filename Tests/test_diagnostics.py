from datetime import datetime

import pytest
from selenium.common.exceptions import TimeoutException, WebDriverException

import Code.web_driver as web_driver_module
from Code import diagnostics
from Code.web_driver import WebDriver
from Tests.test_helpers import (
    DummyBrokenPsutil,
    DummyCaptureSession,
    DummyDriverFactory,
    DummyPsutil,
    DummySeleniumSession,
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
# Per-page stats
# ============================================================


def _stat_keys(line):
    return [pair.split("=", 1)[0] for pair in line.split(" ") if "=" in pair]


def test_page_stats_line_has_every_key_when_nothing_is_available():
    # GIVEN: failing psutil calls, a driver with no performance.memory, and macOS
    session = DummySeleniumSession(script_result=None)

    # WHEN: the stats are collected and formatted
    stats = diagnostics.collect_stats(
        session,
        category="dairy",
        page=3,
        psutil_module=DummyBrokenPsutil(),
        platform_name="darwin",
    )
    line = diagnostics.format_stats(stats)

    # THEN: every key is present, and the unavailable ones are empty
    assert _stat_keys(line) == list(diagnostics.PAGE_STAT_KEYS)
    assert line.startswith("category=dairy page=3 tiles_dom= grid_tiles= ")
    assert "browser_rss_mb= " in line
    assert "shm_used_mb= " in line
    assert line.endswith("read_s=")


def test_page_stats_use_psutil_and_the_javascript_probe_when_available():
    # GIVEN: a driver reporting DOM and heap numbers, a fake psutil and Linux
    session = DummyCaptureSession(
        pages=PAGES,
        page_urls=URLS,
        probe={
            "tiles_dom": 72,
            "dom_nodes": 5000,
            "js_heap_used": 50 * 1024 * 1024,
            "js_heap_total": 80 * 1024 * 1024,
            "js_heap_limit": None,
        },
    )
    session.service = type(
        "Service", (), {"process": type("Process", (), {"pid": 42})()}
    )()

    # WHEN: the stats are collected
    stats = diagnostics.collect_stats(
        session,
        category="dairy",
        page=2,
        grid_tiles=36,
        read_s=4.0,
        uptime_s=61.0,
        pages_this_driver=2,
        psutil_module=DummyPsutil(),
        shm_path="/nonexistent-shm",
        platform_name="linux",
    )

    # THEN: the values come through, with the JS heap limit left blank
    assert stats["tiles_dom"] == 72
    assert stats["dom_nodes"] == 5000
    assert stats["js_heap_used_mb"] == 50.0
    assert stats["js_heap_limit_mb"] is None
    assert stats["browser_rss_mb"] == 300.0
    assert stats["browser_procs"] == 3
    assert stats["sys_mem_avail_mb"] == 2048.0
    assert stats["swap_used_mb"] == 512.0
    assert stats["shm_used_mb"] is None  # path missing, so left blank
    assert diagnostics.format_stats(stats).endswith("read_s=4.0")


def test_a_page_stats_line_is_logged_after_each_page_read(monkeypatch):
    # GIVEN: a category of two pages that read cleanly
    _quiet(monkeypatch)
    driver = _capture_driver()

    # WHEN: the products are retrieved
    WebDriver.get_products(driver, _collect, category_name="dairy")

    # THEN: one INFO line per page, each with every key
    lines = [
        message
        for level, message in driver.logger.records
        if level == "INFO" and message.startswith("Page stats: ")
    ]
    assert len(lines) == 2
    for number, line in enumerate(lines, start=1):
        keys = _stat_keys(line.removeprefix("Page stats: "))
        assert keys == list(diagnostics.PAGE_STAT_KEYS)
        assert f"category=dairy page={number} " in line
        assert "grid_tiles=2 " in line
        assert f"pages_this_driver={number} " in line


def test_pages_this_driver_restarts_after_the_driver_is_replaced(monkeypatch):
    # GIVEN: page 2 crashes once, so the driver is restarted
    _quiet(monkeypatch)
    driver = _capture_driver()
    original_find = driver.driver.find_elements
    state = {"raised": 0}

    def crash_on_page_two(by, value):
        if driver.driver.page_index == 1 and state["raised"] == 0:
            state["raised"] += 1
            raise WebDriverException("tab crashed")
        return original_find(by, value)

    driver.driver.find_elements = crash_on_page_two

    # WHEN: the products are retrieved
    WebDriver.get_products(driver, _collect, category_name="dairy")

    # THEN: the count starts again from one on the fresh driver
    lines = [
        message
        for level, message in driver.logger.records
        if message.startswith("Page stats: ")
    ]
    assert "pages_this_driver=1 " in lines[0]
    assert "page=2 " in lines[1] and "pages_this_driver=1 " in lines[1]


def test_the_driver_start_description_names_versions_flags_and_proxy():
    # GIVEN: a driver reporting its versions and user agent
    session = DummySeleniumSession(script_result="UA/1.0")
    session.capabilities = {
        "browserVersion": "147.0.1",
        "chrome": {"chromedriverVersion": "147.0.2 (abc)"},
    }

    # WHEN: the start is described and formatted
    info = diagnostics.describe_driver_start(
        session, ["--headless=new", "--no-sandbox"], headless=True, proxy_set=False
    )
    line = diagnostics.format_driver_start(info)

    # THEN: the line names everything needed to compare runs
    assert line == (
        "Driver started: chrome=147.0.1 chromedriver=147.0.2 user_agent=UA/1.0 "
        "headless=on proxy=none args=--headless=new --no-sandbox"
    )


@pytest.mark.parametrize("platform_name,expected", [("darwin", None), ("win32", None)])
def test_shm_usage_is_left_blank_off_linux(platform_name, expected):
    # GIVEN: a platform without /dev/shm
    # WHEN: the system stats are collected
    stats = diagnostics.collect_system_stats(DummyPsutil(), platform_name=platform_name)

    # THEN: shm is blank but memory and swap are still reported
    assert stats["shm_used_mb"] is expected
    assert stats["sys_mem_avail_mb"] == 2048.0


# ============================================================
# Unresponsive browser and proxy redaction
# ============================================================


def test_a_wait_timeout_is_not_treated_as_an_unresponsive_browser():
    # GIVEN/WHEN/THEN: Selenium's wait timeout is not a read timeout
    assert diagnostics.is_unresponsive(TimeoutException("tiles did not load")) is False
    assert diagnostics.is_unresponsive(ReadTimeoutError("x")) is True


def test_the_proxy_address_is_redacted_from_the_driver_start_line():
    # GIVEN: Chrome arguments including a proxy with credentials
    session = DummySeleniumSession()

    # WHEN: the start is described
    info = diagnostics.describe_driver_start(
        session, ["--proxy-server=http://u:p@10.0.0.1:8080"], False, True
    )

    # THEN: the address is not logged
    assert info["args"] == ["--proxy-server=<redacted>"]
