from isupermarket import ListSize
from woolworths import Woolworths
from file_handler import FileHandler
from datetime import date
from logger import Logger, LoggingLevel
from web_driver import WebDriver


def main(
    headless=False,
    logging_level=LoggingLevel.INFO,
    default_list_size=ListSize.TESTING,
    proxy_server=None,
    file_handler=None,
    logger=None,
    web_driver=None,
) -> None:
    # Allow dependency injection for unit testing
    logger = logger or Logger(logging_level)
    list_size = default_list_size
    file_path = "Data/{0}".format(date.today())
    file_name = "woolworths-{0}-{1}.csv".format(date.today(), list_size.name)
    header = ["Product Name", "Price", "Unit Price", "Promotion"]

    file_handler = file_handler or FileHandler(file_name, file_path, header, logger)
    web_driver = web_driver or WebDriver(headless, proxy_server)

    woollies = Woolworths(file_handler, logger, web_driver)
    logger.log("Running Boxaroo with list size - {0}".format(list_size))
    woollies.get_data(list_size=list_size)
