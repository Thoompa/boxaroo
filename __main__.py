import pandas as pd
from woolworths import Woolworths
from file_handler import FileHandler
from datetime import date
from logger import Logger

def main(headless=False, separate_csv_columns=False):
    logger = Logger()
    file_name = "woolworths-{0}.csv".format(date.today())
    header = ["Data"] if not separate_csv_columns else ["Product Name", "Price", "Price per Unit"]
         
    file_handler = FileHandler(file_name, header, logger)
    
    woollies = Woolworths(file_handler, logger, headless, separate_csv_columns)
    woollies.get_data()
    
    # if not data:
    #     logger.error("No data - exiting")
    #     quit()
        
    
        
    
    # if split_files_by_category:
    #     for category in data:
    #         file_name = "woolworths-{0}-{1}.csv".format(category["name"], date.today())
    #         store_data(file_name, category["data"], header)
    # else:
        
if __name__ == "__main__":
    main()