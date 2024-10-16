import pandas as pd
from woolworths import get_woolworths_data

def main():
    data = get_woolworths_data()
    if data:
        df = pd.DataFrame(data, columns=["Product Name", "Price", "Price/Unit"])
        print(df)

main()