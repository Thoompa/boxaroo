"""Orchestration boundary for supermarket scraping.

Ownership for the coordinator layer:
- Ask a supermarket adapter for the selected categories for the current run.
- Iterate categories and invoke category-level scraping one category at a time.
- Apply cross-category policies such as progress reporting, retry policy, and
  failure handling.

Non-ownership:
- Application composition and WebDriver lifecycle remain in main.py.
- Supermarket-specific navigation, DOM extraction, cache refresh mechanics, and
  product parsing remain inside the supermarket adapter and its collaborators.

"""

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

from Code.file_handler import IFileHandler
from Code.contracts import CategoryStatus, ISuperMarket, ListSize
from Code.logger import ILogger


@dataclass
class RunSummary:
    """Outcome of one coordinator run, used for the log line and exit code."""

    categories_attempted: int = 0
    categories_succeeded: int = 0
    categories_partial: int = 0
    categories_failed: int = 0
    products_found: int = 0
    products_scraped: int = 0
    incomplete_products: int = 0

    @property
    def ok(self) -> bool:
        return self.categories_partial == 0 and self.categories_failed == 0


class ScrapeCoordinator:
    """Runtime orchestration entry point for category-level scraping."""

    def __init__(
        self,
        supermarket: ISuperMarket,
        logger: ILogger,
        file_handler: IFileHandler,
    ) -> None:
        self.supermarket = supermarket
        self.logger = logger
        self.file_handler = file_handler

    def run(
        self,
        list_size: ListSize = ListSize.FULL,
        category: str | None = None,
        refresh_category_lists: bool = False,
    ) -> RunSummary:
        start_time = perf_counter()
        self.logger.log(f"Scraping {type(self.supermarket).__name__} categories")
        categories = self.supermarket.get_categories(
            list_size,
            category=category,
            refresh_category_lists=refresh_category_lists,
        )

        summary = RunSummary(categories_attempted=len(categories))

        for category in categories:
            self._scrape_category(category, summary)

        elapsed_seconds = perf_counter() - start_time

        if summary.ok:
            self.logger.log(f"Successfully scraped {summary.products_scraped} products")
        else:
            self.logger.warning(
                f"Run finished with problems: scraped {summary.products_scraped} "
                f"products, {summary.categories_partial} partial and "
                f"{summary.categories_failed} failed categories"
            )
        self.logger.log(
            "Run summary: "
            f"categories_attempted={summary.categories_attempted} "
            f"categories_succeeded={summary.categories_succeeded} "
            f"categories_partial={summary.categories_partial} "
            f"categories_failed={summary.categories_failed} "
            f"products_found={summary.products_found} "
            f"products_scraped={summary.products_scraped} "
            f"incomplete_products={summary.incomplete_products} "
            f"took={elapsed_seconds:.2f}s"
        )
        return summary

    def _scrape_category(self, category: str, summary: RunSummary) -> None:
        rows_written = 0

        def store_page(rows: list[list[str]]) -> None:
            nonlocal rows_written
            self.file_handler.store_data(rows)
            rows_written += len(rows)

        started_at = _now()
        try:
            category_data = self.supermarket.get_category_data(
                category, on_rows=store_page
            )
        except Exception as exc:
            self.logger.error(
                f"Failed to scrape category '{category}': {type(exc).__name__}: {exc}"
            )
            self._finish_category(
                summary,
                category,
                status=(
                    CategoryStatus.PARTIAL if rows_written else CategoryStatus.FAILED
                ),
                error=f"{type(exc).__name__}: {exc}",
                rows_written=rows_written,
                started_at=started_at,
            )
            return

        if not isinstance(category_data, dict):
            self.logger.error(
                f"Invalid category data for '{category}': expected dict, got "
                f"{type(category_data).__name__}; value={category_data!r}"
            )
            self._finish_category(
                summary,
                category,
                status=CategoryStatus.FAILED,
                error="invalid category data",
                rows_written=rows_written,
                started_at=started_at,
            )
            return

        products = category_data.get("products")
        if not isinstance(products, list):
            self.logger.error(
                f"Invalid category data for '{category}': expected 'products' "
                f"to be a list, got {type(products).__name__}; value={products!r}; "
                f"category_data={category_data!r}"
            )
            self._finish_category(
                summary,
                category,
                status=CategoryStatus.FAILED,
                error="invalid category data",
                rows_written=rows_written,
                started_at=started_at,
            )
            return

        category_total = category_data.get("total", 0)
        category_incomplete = category_data.get("incomplete", 0)
        if isinstance(category_total, int) and category_total > 0:
            summary.products_found += category_total
            if len(products) == 0:
                self.logger.warning(
                    f"Category {category} returned found={category_total} but scraped=0"
                )
        if isinstance(category_incomplete, int):
            summary.incomplete_products += category_incomplete

        self._finish_category(
            summary,
            category,
            status=CategoryStatus(category_data.get("status", CategoryStatus.COMPLETE)),
            error=category_data.get("error"),
            rows_written=rows_written,
            started_at=started_at,
            expected_total=category_total if isinstance(category_total, int) else None,
            pages_committed=category_data.get("pages_committed"),
        )

    def _finish_category(
        self,
        summary: RunSummary,
        category: str,
        *,
        status: CategoryStatus,
        error: str | None,
        rows_written: int,
        started_at: str,
        expected_total: int | None = None,
        pages_committed: int | None = None,
    ) -> None:
        summary.products_scraped += rows_written
        if status is CategoryStatus.COMPLETE:
            summary.categories_succeeded += 1
        elif status is CategoryStatus.PARTIAL:
            summary.categories_partial += 1
        else:
            summary.categories_failed += 1

        if status is not CategoryStatus.COMPLETE:
            self.logger.error(
                f"Category {category} {status.value.upper()}: saved {rows_written} "
                f"rows ({error})"
            )

        try:
            self.file_handler.write_status(
                category,
                {
                    "state": status.value,
                    "rows_written": rows_written,
                    "pages_committed": pages_committed,
                    "expected_total": expected_total,
                    "error": error,
                    "started_at": started_at,
                    "finished_at": _now(),
                },
            )
        except Exception as exc:
            self.logger.error(f"Could not write status for {category}: {exc}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
