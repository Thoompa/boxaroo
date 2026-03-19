from isupermarket import ListSize
from woolworths import Woolworths
from file_handler import FileHandler
from datetime import date
from logger import Logger, LoggingLevel
from web_driver import WebDriver
import argparse

def main(headless=False, logging_level=LoggingLevel.INFO, default_list_size=ListSize.TESTING, proxy_server=None) -> None:
    logger = Logger(logging_level)
    list_size = default_list_size
    file_path = "Data/{0}".format(date.today())
    file_name = "woolworths-{0}-{1}.csv".format(date.today(), list_size.name)
    header = ["Product Name", "Price", "Unit Price", "Promotion"]
         
    file_handler = FileHandler(file_name, file_path, header, logger)
    web_driver = WebDriver(headless, proxy_server)
    
    woollies = Woolworths(file_handler, logger, web_driver)
    logger.log("Running Boxaroo with list size - {0}".format(list_size))
    woollies.get_data(list_size=list_size)
    
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Boxaroo Woolworths Scraper')
    parser.add_argument('--list_size', choices=['TESTING', 'SHORT', 'FULL'], default='TESTING', help='Size of the category list to scrape')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--logging_level', choices=['DEBUG', 'INFO', 'ERROR'], default='INFO', help='Logging level')
    parser.add_argument('--proxy_server', help='Proxy server URL')
    
    args = parser.parse_args()
    
    # Convert string to ListSize enum
    list_size_map = {
        'TESTING': ListSize.TESTING,
        'SHORT': ListSize.SHORT,
        'FULL': ListSize.FULL
    }
    
    # Convert string to LoggingLevel enum
    logging_level_map = {
        'DEBUG': LoggingLevel.DEBUG,
        'INFO': LoggingLevel.INFO,
        'ERROR': LoggingLevel.ERROR
    }
    
    main(
        headless=args.headless,
        logging_level=logging_level_map[args.logging_level],
        default_list_size=list_size_map[args.list_size],
        proxy_server=args.proxy_server
    )