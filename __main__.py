from isupermarket import ListSize
from woolworths import Woolworths
from file_handler import FileHandler
from datetime import date
from logger import Logger, LoggingLevel
from web_driver import WebDriver

def main(headless=False, logging_level=LoggingLevel.INFO) -> None:
    logger = Logger(logging_level)
    list_size = ListSize.FULL
    file_path = "Data/{0}".format(date.today())
    file_name = "woolworths-{0}-{1}.csv".format(date.today(), list_size.name)
    header = ["Data"]
         
    file_handler = FileHandler(file_name, file_path, header, logger)
    web_driver = WebDriver(headless)
    
    woollies = Woolworths(file_handler, logger, web_driver)
    logger.log("Running Boxaroo with list size - {0}".format(list_size))
    woollies.get_data(list_size=list_size)
    
        
if __name__ == "__main__":
    main(logging_level=LoggingLevel.DEBUG)
    # main()