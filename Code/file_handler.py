import csv
import os
from typing import Sequence

from Code.contracts import IFileHandler, ILogger


class FileHandler(IFileHandler):

    def __init__(
        self, file_name: str, file_path: str, header: Sequence[str], logger: ILogger
    ):
        self.file_name = file_name
        self.file_path = file_path
        self.header = header
        self.logger = logger
        self._create_file()

    def _create_file(self):
        file_path_name = os.path.join(self.file_path, self.file_name)
        try:
            # Create the folder if it doesn't exist
            os.makedirs(self.file_path, exist_ok=True)

            if os.path.exists(file_path_name):
                self.logger.log("Appending to existing file " + self.file_name)
                return

            with open(file_path_name, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(self.header)
            self.logger.log("Created file " + self.file_name)
        except Exception as e:
            self.logger.error(f"Error creating file {self.file_name}: {e}")
            raise

    def store_data(self, data):
        self.logger.log("Storing data of size " + str(len(data)) + "...")
        file_path_name = os.path.join(self.file_path, self.file_name)
        with open(file_path_name, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(data)
        self.logger.log(f"Successfully stored {len(data)} rows")
