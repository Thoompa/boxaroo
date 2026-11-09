"""Per-page resource statistics and driver-start details for the scraper.

Everything here is best effort: a probe that fails leaves a blank value and is
never raised, so diagnostics cannot change which exception propagates or how
retries behave. The functions take the Selenium driver as an argument so they
can be tested with doubles. Failure captures live in `Code/failure_capture.py`.
"""

import shutil
import sys
from collections.abc import Callable, Iterable
from typing import Any

import psutil

SHM_PATH = "/dev/shm"

# Keys of the "Page stats:" line, in order. A key is always present; an
# unavailable value is left empty so lines from different runs stay comparable.
PAGE_STAT_KEYS = (
    "category",
    "page",
    "tiles_dom",
    "grid_tiles",
    "dom_nodes",
    "js_heap_used_mb",
    "js_heap_total_mb",
    "js_heap_limit_mb",
    "browser_rss_mb",
    "browser_procs",
    "sys_mem_avail_mb",
    "swap_used_mb",
    "shm_used_mb",
    "driver_uptime_s",
    "pages_this_driver",
    "read_s",
)
# The stats appended to a retry warning (what the page was is already in it).
RETRY_STAT_KEYS = tuple(
    key for key in PAGE_STAT_KEYS if key not in ("category", "page", "read_s")
)
SYSTEM_STAT_KEYS = ("sys_mem_avail_mb", "swap_used_mb", "shm_used_mb")

_MB = 1024 * 1024

# One cheap call per page: DOM size and the JS heap (performance.memory is a
# non-standard Chrome-only API, so each value may be null).
PAGE_PROBE_SCRIPT = """
var mem = performance.memory || {};
function val(v) { return typeof v === 'number' ? v : null; }
return {
    tiles_dom: document.getElementsByTagName('wc-product-tile').length,
    dom_nodes: document.getElementsByTagName('*').length,
    js_heap_used: val(mem.usedJSHeapSize),
    js_heap_total: val(mem.totalJSHeapSize),
    js_heap_limit: val(mem.jsHeapSizeLimit)
};
"""

DRIVER_INFO_SCRIPT = "return navigator.userAgent;"


# --- Pure helpers ---------------------------------------------------------


def _mb(value: float | int | None) -> float | None:
    return None if value is None else round(value / _MB, 1)


def format_stats(stats: dict[str, Any], keys: Iterable[str] = PAGE_STAT_KEYS) -> str:
    """Render stats as `key=value` pairs; a missing value is an empty `key=`."""
    parts = []
    for key in keys:
        value = stats.get(key)
        if isinstance(value, float):
            value = round(value, 1)
        parts.append(f"{key}={'' if value is None else value}")
    return " ".join(parts)


def first_line(text: str) -> str:
    lines = text.splitlines()
    return lines[0] if lines else ""


def _safe(fn: Callable[[], Any]) -> Any:
    """Return fn(), or None when it fails."""
    try:
        return fn()
    except Exception:
        return None


def is_unresponsive(exc: BaseException) -> bool:
    """True for a read timeout: the browser stopped answering commands.

    Every further command would wait out Selenium's 120 s timeout, so probing
    stops. Selenium's own TimeoutException (a wait that ran out) does not count.
    """
    return "readtimeout" in type(exc).__name__.lower() or (
        "timed out" in str(exc).lower()
    )


# --- System and browser stats ---------------------------------------------


def chromedriver_pid(driver: Any) -> int | None:
    """The chromedriver process id, which parents the browser processes."""
    return getattr(
        getattr(getattr(driver, "service", None), "process", None), "pid", None
    )


def collect_system_stats(
    psutil_module: Any = psutil,
    shm_path: str = SHM_PATH,
    platform_name: str | None = None,
) -> dict[str, float | None]:
    """Available memory, swap used and (Linux only) /dev/shm used, in MB."""
    platform_name = sys.platform if platform_name is None else platform_name
    stats: dict[str, float | None] = {key: None for key in SYSTEM_STAT_KEYS}
    stats["sys_mem_avail_mb"] = _mb(
        _safe(lambda: psutil_module.virtual_memory().available)
    )
    stats["swap_used_mb"] = _mb(_safe(lambda: psutil_module.swap_memory().used))
    if platform_name.startswith("linux"):
        stats["shm_used_mb"] = _mb(_safe(lambda: shutil.disk_usage(shm_path).used))
    return stats


def collect_browser_process_stats(
    pid: int | None, psutil_module: Any = psutil
) -> dict[str, float | int | None]:
    """Resident memory and count of chromedriver and all its descendants.

    RSS counts shared pages in every process, so the total overstates real use;
    it is still the right quantity to watch for growth.
    """
    stats: dict[str, float | int | None] = {
        "browser_rss_mb": None,
        "browser_procs": None,
    }
    if pid is None:
        return stats

    def measure() -> tuple[int, int]:
        root = psutil_module.Process(pid)
        processes = [root, *root.children(recursive=True)]
        total = 0
        counted = 0
        for process in processes:
            try:
                total += process.memory_info().rss
                counted += 1
            except Exception:
                continue  # exited between listing and reading
        return total, counted

    measured = _safe(measure)
    if measured is not None:
        stats["browser_rss_mb"] = _mb(measured[0])
        stats["browser_procs"] = measured[1]
    return stats


def collect_stats(
    driver: Any,
    *,
    category: str | None = None,
    page: int | None = None,
    grid_tiles: int | None = None,
    read_s: float | None = None,
    uptime_s: float | None = None,
    pages_this_driver: int | None = None,
    psutil_module: Any = psutil,
    shm_path: str = SHM_PATH,
    platform_name: str | None = None,
    probe_driver: bool = True,
) -> dict[str, Any]:
    """Gather every PAGE_STAT_KEYS value that can be had; the rest are None.

    With probe_driver False the browser is not asked anything (it is hung), so
    only the process and system stats are read. `driver_unresponsive` records
    whether the browser stopped answering.
    """
    stats: dict[str, Any] = {key: None for key in PAGE_STAT_KEYS}
    stats.update(
        category=category,
        page=page,
        grid_tiles=grid_tiles,
        read_s=read_s,
        driver_uptime_s=uptime_s,
        pages_this_driver=pages_this_driver,
    )
    stats["driver_unresponsive"] = not probe_driver
    probe = None
    if probe_driver:
        try:
            probe = driver.execute_script(PAGE_PROBE_SCRIPT)
        except Exception as probe_exc:
            stats["driver_unresponsive"] = is_unresponsive(probe_exc)
    if isinstance(probe, dict):
        stats["tiles_dom"] = probe.get("tiles_dom")
        stats["dom_nodes"] = probe.get("dom_nodes")
        stats["js_heap_used_mb"] = _mb(probe.get("js_heap_used"))
        stats["js_heap_total_mb"] = _mb(probe.get("js_heap_total"))
        stats["js_heap_limit_mb"] = _mb(probe.get("js_heap_limit"))
    stats.update(collect_browser_process_stats(chromedriver_pid(driver), psutil_module))
    stats.update(collect_system_stats(psutil_module, shm_path, platform_name))
    return stats


def describe_driver_start(
    driver: Any, arguments: Iterable[str], headless: bool, proxy_set: bool
) -> dict[str, Any]:
    """What a newly created driver is: versions, user agent and Chrome flags."""
    capabilities = _safe(lambda: driver.capabilities) or {}
    return {
        "chrome": capabilities.get("browserVersion"),
        "chromedriver": (capabilities.get("chrome") or {})
        .get("chromedriverVersion", "")
        .split(" ")[0]
        or None,
        "user_agent": _safe(lambda: driver.execute_script(DRIVER_INFO_SCRIPT)),
        "headless": headless,
        "proxy": proxy_set,
        "args": [
            "--proxy-server=<redacted>" if arg.startswith("--proxy-server=") else arg
            for arg in arguments
        ],
    }


def format_driver_start(info: dict[str, Any]) -> str:
    return (
        f"Driver started: chrome={info['chrome'] or ''} "
        f"chromedriver={info['chromedriver'] or ''} "
        f"user_agent={info['user_agent'] or ''} "
        f"headless={'on' if info['headless'] else 'off'} "
        f"proxy={'set' if info['proxy'] else 'none'} "
        f"args={' '.join(info['args'])}"
    )
