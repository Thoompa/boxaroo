import csv
from abc import ABC, abstractmethod
import os
from typing import Iterable

from logger import ILogger


class IFileHandler(ABC):
    
    @abstractmethod
    def __init__(self, file_name: str, file_path: str, header: str, logger: ILogger):
        pass
    
    @abstractmethod
    def store_data(self, data: Iterable[Iterable[any]]) -> None:
        pass
    

class FileHandler(IFileHandler):
    
    def __init__(self, file_name: str, file_path: str, header: str, logger: ILogger):
        self.file_name = file_name
        self.file_path = file_path
        self.header = header
        self.logger = logger
        self._create_file()
        
    def _create_file(self):
        # Always create/recreate the file with header
        try:
            # Create the folder if it doesn't exist
            os.makedirs(self.file_path, exist_ok=True)
            
            # Always write the header (this will overwrite any existing file)
            with open(self.file_path + '/' + self.file_name, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(self.header)
                self.logger.log("Created file " + self.file_name)
        except Exception as e:
            self.logger.error(f"Error creating file {self.file_name}: {e}")

    def store_data(self, data):
        self.logger.log("Storing data of size " + str(len(data)) + "...")
        with open(self.file_path + '/' + self.file_name, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data)
        