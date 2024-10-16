import csv

def store_data(filename, data, header):
    # Check if the file already exists
    try:
        with open(filename, 'r') as file:
            # File exists, no need to create it
            pass
    except FileNotFoundError:
        # File doesn't exist, create it and write the header
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(header)

    # Append the data to the file
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(data)
    