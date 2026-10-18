import csv
import json
import os
from typing import Any, Sequence

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

    def write_status(self, category: str, status: dict[str, Any]) -> None:
        """Record how a category finished in a JSON file beside the CSV.

        The CSV header is fixed (the viewer depends on it), so run status lives
        in "<csv name>.status.json". The file is replaced atomically.
        """
        status_path = os.path.join(self.file_path, self.file_name + ".status.json")
        document: dict[str, Any] = {"schema_version": 1, "categories": {}}
        if os.path.exists(status_path):
            try:
                with open(status_path, encoding="utf-8") as file:
                    loaded = json.load(file)
                if isinstance(loaded.get("categories"), dict):
                    document = loaded
            except (OSError, ValueError, AttributeError):
                self.logger.warning(f"Ignoring unreadable status file {status_path}")
        document["categories"][category] = status

        temp_path = status_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(document, file, indent=2)
        os.replace(temp_path, status_path)
