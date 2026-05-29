"""Command-line interface wiring for Boxaroo."""

import argparse

from Code.contracts import ListSize, LoggingLevel, Supermarket
from Code.list_size_help import build_list_size_help
from Code.main import main as run_main


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
        "--hard_driver_reset",
        action="store_true",
        help="Recreate the browser after a fixed number of pages to reduce long-run browser degradation.",
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
        hard_driver_reset=args.hard_driver_reset,
        proxy_server=args.proxy_server,
    )
