"""Saves evidence of a browser failure: screenshot, page source and JSON metadata.

Everything is best effort: a probe that fails is recorded as a "failed: ..." note
and never raised, so a capture cannot change which exception propagates or how
retries behave. The capturer takes the Selenium driver, a clock and a filesystem
root as arguments so it can be tested with doubles.
"""

import json
import re
import time
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from Code.diagnostics import first_line, is_unresponsive

FAILURE_CAPTURE_ROOT = Path("Logs") / "failure-captures"
MAX_CAPTURES_PER_CATEGORY = 6
MAX_CAPTURES_PER_PAGE = 2
MAX_PAGE_SOURCE_BYTES = 2_000_000
BODY_TEXT_PREVIEW_CHARS = 500
MAX_RESOURCE_ENTRIES_LISTED = 20
MAX_CONSOLE_ERRORS = 20
MAX_CONSOLE_MESSAGE_CHARS = 300
UNRESPONSIVE_NOTE = "skipped: browser unresponsive"
# Total time one capture may spend on probes before it stops asking the browser.
PROBE_BUDGET_SECONDS = 60
# Chrome keeps at most this many resource timing entries by default.
RESOURCE_TIMING_BUFFER_SIZE = 250

CHALLENGE_MARKERS = (
    "access denied",
    "captcha",
    "unusual traffic",
    "verify you are human",
    "reference #",
    "akamai",
    "pardon our interruption",
    "blocked",
)

PAGE_STATE_SCRIPT = """
var text = (document.body && document.body.innerText) || '';
return {
    title: document.title,
    ready_state: document.readyState,
    tiles_total: document.querySelectorAll('wc-product-tile').length,
    tiles_in_grid: document.querySelectorAll(arguments[0]).length,
    body_text: text.slice(0, 200000)
};
"""

RESOURCE_TIMING_SCRIPT = """
return performance.getEntriesByType('resource').map(function (e) {
    return {
        name: e.name,
        status: e.responseStatus === undefined ? null : e.responseStatus,
        transfer_size: e.transferSize,
        duration_ms: Math.round(e.duration)
    };
});
"""


def find_challenge_markers(*texts: str | None) -> list[str]:
    """Return the bot-challenge phrases found (case-insensitively) in the texts."""
    haystack = "\n".join(text.lower() for text in texts if text)
    return [marker for marker in CHALLENGE_MARKERS if marker in haystack]


def summarize_resource_timing(
    entries: Iterable[dict[str, Any]], limit: int = MAX_RESOURCE_ENTRIES_LISTED
) -> dict[str, Any]:
    """Summarise resource timing entries, listing the ones that look failed.

    An entry is suspect when its status is 400 or more, or when it reports status
    0 with nothing transferred. Cross-origin resources served without
    Timing-Allow-Origin also report 0, so each entry carries its host.
    """
    entries = list(entries)
    suspect: list[dict[str, Any]] = []
    for entry in entries:
        status = entry.get("status")
        if not isinstance(status, (int, float)):
            continue
        no_transfer = not entry.get("transfer_size")
        if status >= 400 or (status == 0 and no_transfer):
            parsed = urlparse(str(entry.get("name", "")))
            suspect.append(
                {
                    "host": parsed.netloc,
                    "path": parsed.path,
                    "status": int(status),
                    "duration_ms": entry.get("duration_ms"),
                }
            )
    return {
        "total": len(entries),
        "suspect_total": len(suspect),
        "buffer_may_be_full": len(entries) >= RESOURCE_TIMING_BUFFER_SIZE,
        "suspect": suspect[:limit],
    }


def exception_summary(exc: BaseException) -> dict[str, str]:
    msg = getattr(exc, "msg", None) or str(exc) or repr(exc)
    return {"type": type(exc).__name__, "message": first_line(msg)}


def _failure_note(exc: BaseException) -> str:
    return f"failed: {type(exc).__name__}: {first_line(str(exc))}"


class FailureCapturer:
    """Saves a screenshot, page source and JSON metadata for a browser failure.

    One instance per category: it stops after `max_captures` so a long streak of
    failures cannot fill the disk.
    """

    def __init__(
        self,
        root: Path | None = None,
        clock: Callable[[], datetime] = datetime.now,
        max_captures: int = MAX_CAPTURES_PER_CATEGORY,
        max_source_bytes: int = MAX_PAGE_SOURCE_BYTES,
        max_per_page: int = MAX_CAPTURES_PER_PAGE,
    ):
        self.root = FAILURE_CAPTURE_ROOT if root is None else Path(root)
        self.clock = clock
        self.max_captures = max_captures
        self.max_source_bytes = max_source_bytes
        self.max_per_page = max_per_page
        self.captured = 0
        self._captured_by_page: dict[int, int] = {}

    @property
    def is_full(self) -> bool:
        return self.captured >= self.max_captures

    def capture(
        self,
        driver: Any,
        *,
        category: str,
        page: int,
        attempt: int,
        exc: BaseException,
        requested_url: str | None,
        grid_selector: str,
        stats: dict[str, Any] | None = None,
        driver_responsive: bool = True,
    ) -> str | None:
        """Write the capture and return its path stem, or None if capped or unwritable.

        Never raises.
        """
        if self.is_full or self._captured_by_page.get(page, 0) >= self.max_per_page:
            return None
        try:
            now = self.clock()
            directory = self.root / f"{now:%Y-%m-%d}"
            directory.mkdir(parents=True, exist_ok=True)
            safe_category = re.sub(r"[^A-Za-z0-9_-]", "_", category or "unknown")
            base = f"{safe_category}-p{page}-a{attempt}-{now:%H%M%S}"
            stem = directory / base
            suffix = 1
            while stem.with_suffix(".json").exists():
                suffix += 1
                stem = directory / f"{base}-{suffix}"
            self.captured += 1
            self._captured_by_page[page] = self._captured_by_page.get(page, 0) + 1

            metadata = self._probe(
                driver,
                stem,
                exc,
                requested_url,
                grid_selector,
                stats,
                driver_responsive and not is_unresponsive(exc),
            )
            stem.with_suffix(".json").write_text(
                json.dumps(metadata, indent=2, default=str), encoding="utf-8"
            )
            return str(stem)
        except Exception:
            return None

    def _probe(
        self,
        driver: Any,
        stem: Path,
        exc: BaseException,
        requested_url: str | None,
        grid_selector: str,
        stats: dict[str, Any] | None,
        responsive: bool,
    ) -> dict[str, Any]:
        started = time.monotonic()
        meta: dict[str, Any] = {
            "captured_at": self.clock().isoformat(timespec="seconds"),
            "exception": exception_summary(exc),
            "requested_url": requested_url,
        }

        def record(key: str, fn: Callable[[], Any]) -> Any:
            nonlocal responsive
            if responsive and time.monotonic() - started > PROBE_BUDGET_SECONDS:
                responsive = False
            if not responsive:
                meta[key] = UNRESPONSIVE_NOTE
                return None
            try:
                meta[key] = fn()
            except Exception as probe_exc:
                meta[key] = _failure_note(probe_exc)
                if is_unresponsive(probe_exc):
                    responsive = False
                return None
            return meta[key]

        record("current_url", lambda: driver.current_url)

        def save_screenshot() -> str:
            if driver.save_screenshot(str(stem.with_suffix(".png"))) is False:
                raise OSError("save_screenshot returned False")
            return "saved"

        record("screenshot", save_screenshot)

        page_source = None

        def save_source() -> str:
            nonlocal page_source
            page_source = driver.page_source or ""
            data = page_source.encode("utf-8", "replace")
            note = "saved"
            if len(data) > self.max_source_bytes:
                note = f"truncated from {len(data)} bytes to {self.max_source_bytes}"
                data = data[: self.max_source_bytes]
            stem.with_suffix(".html").write_bytes(data)
            return note

        record("page_source", save_source)

        state: dict[str, Any] = {}

        def read_state() -> str:
            result = driver.execute_script(PAGE_STATE_SCRIPT, grid_selector)
            if not isinstance(result, dict):
                raise ValueError("page state script returned no data")
            state.update(result)
            return "ok"

        state_note = record("page_state", read_state)
        meta["document_title"] = state.get("title") if state_note else None
        meta["ready_state"] = state.get("ready_state") if state_note else None
        meta["tiles_total"] = state.get("tiles_total") if state_note else None
        meta["tiles_in_grid"] = state.get("tiles_in_grid") if state_note else None
        body_text = state.get("body_text") or ""
        meta["body_text_preview"] = body_text[:BODY_TEXT_PREVIEW_CHARS]
        meta["challenge_markers"] = find_challenge_markers(state.get("title"), body_text)

        def read_resources() -> dict[str, Any]:
            entries = driver.execute_script(RESOURCE_TIMING_SCRIPT)
            if not isinstance(entries, list):
                raise ValueError("resource timing script returned no data")
            return summarize_resource_timing(entries)

        record("resources", read_resources)

        def read_console() -> list[dict[str, Any]]:
            return [
                {
                    "level": entry.get("level"),
                    "message": str(entry.get("message", ""))[
                        :MAX_CONSOLE_MESSAGE_CHARS
                    ],
                }
                for entry in driver.get_log("browser")
                if entry.get("level") == "SEVERE"
            ][-MAX_CONSOLE_ERRORS:]

        record("console_errors", read_console)
        meta["stats"] = stats
        return meta
