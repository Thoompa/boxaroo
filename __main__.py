import argparse

from Code.contracts import ListSize, LoggingLevel, Supermarket
from Code.main import main, build_list_size_help


def _build_supermarket_help() -> str:
    supported_supermarkets = ", ".join(market.value for market in Supermarket)
    return (
        "Supermarket adapter key to run "
        f"(supported supermarkets: {supported_supermarkets})."
    )


if __name__ == "__main__":
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

    args = parser.parse_args()

    # Convert string to ListSize enum
    list_size_map = {
        "TESTING": ListSize.TESTING,
        "SHORT": ListSize.SHORT,
        "MEDIUM": ListSize.MEDIUM,
        "LONG": ListSize.LONG,
        "FULL": ListSize.FULL,
    }

    # Convert string to LoggingLevel enum
    logging_level_map = {
        "DEBUG": LoggingLevel.DEBUG,
        "INFO": LoggingLevel.INFO,
        "WARNING": LoggingLevel.WARNING,
        "ERROR": LoggingLevel.ERROR,
    }

    main(
        headless=args.headless,
        logging_level=logging_level_map[args.logging_level],
        default_list_size=list_size_map[args.list_size],
        supermarket=args.supermarket,
        refresh_category_lists=args.refresh_category_lists,
        proxy_server=args.proxy_server,
    )
