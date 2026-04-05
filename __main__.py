from isupermarket import ListSize
from logger import LoggingLevel
import argparse
from cli import main


## main is now imported from cli.py


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Boxaroo Woolworths")
    parser.add_argument(
        "--list_size",
        choices=["TESTING", "SHORT", "FULL"],
        default="FULL",
        help="Size of the category list to scrape",
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run browser in headless mode"
    )
    parser.add_argument(
        "--logging_level",
        choices=["DEBUG", "INFO", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    parser.add_argument(
        "--refresh_category_lists",
        action="store_true",
        help="Force refresh of cached category lists from website",
    )
    parser.add_argument("--proxy_server", help="Proxy server URL")

    args = parser.parse_args()

    # Convert string to ListSize enum
    list_size_map = {
        "TESTING": ListSize.TESTING,
        "SHORT": ListSize.SHORT,
        "FULL": ListSize.FULL,
    }

    # Convert string to LoggingLevel enum
    logging_level_map = {
        "DEBUG": LoggingLevel.DEBUG,
        "INFO": LoggingLevel.INFO,
        "ERROR": LoggingLevel.ERROR,
    }

    main(
        headless=args.headless,
        logging_level=logging_level_map[args.logging_level],
        default_list_size=list_size_map[args.list_size],
        refresh_category_lists=args.refresh_category_lists,
        proxy_server=args.proxy_server,
    )
