import pandas as pd
from woolworths import get_woolworths_data
from data_storage import store_data
from datetime import date
import logger

def main(split_files_by_category=False, headless=False, separate_csv_columns=False):
    data = get_woolworths_data(split_files_by_category, headless, separate_csv_columns)
    
    if not data:
        logger.error("No data - exiting")
        quit()
        
    
    if separate_csv_columns:
        df = pd.DataFrame(data, columns=["Product Name", "Price", "Price/Unit"])
        print(df)
        
        header = ["Product Name", "Price", "Price per Unit"]
    else:
        header = ["Data"]
        
    
    if split_files_by_category:
        for category in data:
            file_name = "woolworths-{0}-{1}.csv".format(category["name"], date.today())
            store_data(file_name, category["data"], header)
    else:
        file_name = "woolworths-{0}.csv".format(date.today())
        store_data(file_name, data, header)
        
if __name__ == "__main__":
    main()