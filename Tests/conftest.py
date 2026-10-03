"""Fixtures for live (real-site) tests; run them with `pytest -m live`."""

import os
import re
from datetime import datetime
from pathlib import Path

import pytest

from Code.contracts import ILogger
from Code.web_driver import WebDriver

FAILURE_DIR = Path(__file__).resolve().parent.parent / "Logs" / "live-test-failures"


class PrintingLogger(ILogger):
    """Prints everything so pytest shows it alongside a live test failure."""

    def __init__(self, logging_level=None):
        self.logging_level = logging_level

    def debug(self, message):
        print(f"DEBUG: {message}")

    def log(self, message):
        print(f"INFO: {message}")

    def warning(self, message):
        print(f"WARNING: {message}")

    def error(self, message):
        print(f"ERROR: {message}")


def _live_opted_in(config) -> bool:
    markexpr = config.option.markexpr or ""
    return "live" in markexpr and "not live" not in markexpr


def _explicitly_selected(config, item) -> bool:
    """True when the test's file was named on the command line (e.g. clicking the
    test in the VS Code Testing panel), as opposed to a whole-directory run."""
    for arg in config.args:
        path = Path(config.invocation_params.dir, arg.split("::")[0]).resolve()
        if path.is_file() and path == Path(item.path).resolve():
            return True
    return False


def pytest_collection_modifyitems(config, items):
    """Live tests stay visible to test explorers but are skipped on a plain run."""
    if _live_opted_in(config):
        return
    skip_live = pytest.mark.skip(
        reason="live test: run with `pytest -m live` or select it explicitly"
    )
    for item in items:
        if "live" in item.keywords and not _explicitly_selected(config, item):
            item.add_marker(skip_live)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


def _save_failure_artifacts(driver: WebDriver, test_name: str) -> None:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", test_name)
    stem = FAILURE_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{safe_name}"
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        driver.driver.save_screenshot(str(stem) + ".png")
        Path(str(stem) + ".html").write_text(
            driver.driver.page_source, encoding="utf-8"
        )
        print(f"Saved live failure artifacts: {stem}.png / .html")
    except Exception as exc:
        print(f"Could not save live failure artifacts: {type(exc).__name__}: {exc}")


@pytest.fixture(scope="session")
def _live_browser():
    """One real browser shared by every live test in the session (launching is slow)."""
    headless = os.getenv("BOXAROO_LIVE_HEADED") != "1"
    driver = WebDriver(logger=PrintingLogger(), headless=headless)
    try:
        yield driver
    finally:
        driver.quit()


@pytest.fixture
def live_logger():
    return PrintingLogger()


@pytest.fixture
def live_driver(request, _live_browser):
    """The shared real browser (headless unless BOXAROO_LIVE_HEADED=1). Saves a
    screenshot and the page HTML to Logs/live-test-failures/ when the test fails."""
    yield _live_browser
    failed = getattr(request.node, "rep_call", None)
    if failed is not None and failed.failed:
        _save_failure_artifacts(_live_browser, request.node.name)


@pytest.fixture
def limit_pages(monkeypatch):
    """Returns limit(driver, max_pages): stop get_products after max_pages pages by
    making the driver report there is no next page. Patches the pagination entry
    point, which differs between versions of web_driver.py."""

    def limit(driver: WebDriver, max_pages: int) -> None:
        method_name = next(
            name
            for name in ("_advance_with_recovery", "_advance_to_next_page")
            if hasattr(driver, name)
        )
        pages_seen = {"count": 0}

        def advance(*_args, **_kwargs) -> bool:
            pages_seen["count"] += 1
            return pages_seen["count"] < max_pages

        monkeypatch.setattr(driver, method_name, advance)

    return limit
