import csv

class FileHandler:
    def __init__(self, file_name, header, logger) -> None:
        self.file_name = file_name
        self.header = header
        self.logger = logger
        self.create_file()
        
    def create_file(self):
        # Check if the file already exists
        try:
            with open(self.file_name, 'r') as file:
                # File exists, no need to create it
                self.logger.log("File " + self.file_name + " already exists")
        except FileNotFoundError:
            # File doesn't exist, create it and write the header
            with open(self.file_name, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(self.header)

    def store_data(self, data):
        self.logger.log("Storing data of size " + str(len(data)) + "...")
        with open(self.file_name, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data)
        