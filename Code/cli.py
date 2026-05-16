"""Command-line interface wiring for Boxaroo."""

import argparse
import json
import os

from Code.contracts import ListSize, LoggingLevel, Supermarket
from Code.main import main as run_main


def _load_list_product_totals() -> dict[str, int]:
    cache_path = os.path.join(
        "Data", "category_lists", "woolworths-category-lists.json"
    )
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        totals = cached.get("list_product_totals", {})
        if not isinstance(totals, dict):
            return {}
        return {
            str(k).lower(): int(v)
            for k, v in totals.items()
            if isinstance(v, int) and v >= 0
        }
    except Exception:
        return {}


def _format_eta(total_products: int | None) -> str:
    if total_products is None:
        return "n/a"

    seconds = round(total_products / 4)
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if remaining_seconds > 0 or not parts:
        parts.append(f"{remaining_seconds}s")

    return "~" + " ".join(parts)


def build_list_size_help() -> str:
    totals = _load_list_product_totals()

    return (
        "Size of category list to scrape. "
        "Estimated runtime by list (4 products/sec): "
        f"TESTING {_format_eta(totals.get('testing'))}, "
        f"SHORT {_format_eta(totals.get('short'))}, "
        f"MEDIUM {_format_eta(totals.get('medium'))}, "
        f"LONG {_format_eta(totals.get('long'))}, "
        f"FULL {_format_eta(totals.get('full'))}."
    )


def _build_supermarket_help() -> str:
    supported_supermarkets = ", ".join(market.value for market in Supermarket)
    return (
        "Supermarket adapter key to run "
        f"(supported supermarkets: {supported_supermarkets})."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Boxaroo Woolworths scraper. Scrape product data for selected category list sizes and write results to CSV."
    )
    parser.add_argument(
        "--list_size",
        choices=["TESTING", "SHORT", "MEDIUM", "LONG", "FULL"],
        default="FULL",
        help=build_list_size_help(),
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no visible window).",
    )
    parser.add_argument(
        "--logging_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity. DEBUG includes detailed scraper internals.",
    )
    parser.add_argument(
        "--refresh_category_lists",
        action="store_true",
        help="Force refresh of cached category lists and list product totals from the website.",
    )
    parser.add_argument(
        "--proxy_server", help="Proxy server URL (for example http://host:port)."
    )
    parser.add_argument(
        "--supermarket",
        choices=[market.value for market in Supermarket],
        default=Supermarket.WOOLWORTHS.value,
        help=_build_supermarket_help(),
    )
    return parser


def _parse_list_size(value: str) -> ListSize:
    return ListSize[value]


def _parse_logging_level(value: str) -> LoggingLevel:
    return LoggingLevel[value]


def _parse_supermarket(value: str) -> Supermarket:
    return Supermarket(value)


def run(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    run_main(
        headless=args.headless,
        logging_level=_parse_logging_level(args.logging_level),
        default_list_size=_parse_list_size(args.list_size),
        supermarket=_parse_supermarket(args.supermarket),
        refresh_category_lists=args.refresh_category_lists,
        proxy_server=args.proxy_server,
    )
