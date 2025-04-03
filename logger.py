from abc import ABC, abstractmethod
from enum import Enum

class LoggingLevel(Enum):
    DEBUG = 1
    INFO = 2
    ERROR = 3

class ILogger(ABC):
    def __init__(self, logging_level: LoggingLevel):
        pass
    
    @abstractmethod
    def debug(self, message: str) -> None:
        pass
    
    @abstractmethod
    def log(self, message: str) -> None:
        pass
    
    @abstractmethod
    def error(self, e: str) -> None:
        pass
    

class Logger(ILogger):
    def __init__(self, logging_level: LoggingLevel):
        self.file_name = "Logs.txt"
        self.logging_level = logging_level
        try:
            with open(self.file_name, "x") as file:
                pass  # Creates the file but does not write anything
        except FileExistsError:
            pass # File already exists
        
    def debug(self, message: str) -> None:
        if self.logging_level >= LoggingLevel.DEBUG:
            print("DEBUG: " + message)
            
        with open(self.file_name, "a") as file:
            file.write("DEBUG: " + message)
    
    def log(self, message: str) -> None:
        if self.logging_level >= LoggingLevel.INFO:
            print("INFO: " + message)
            
        with open(self.file_name, "a") as file:
            file.write("INFO: " + message)
        
    def error(self, e: str) -> None:
        if self.logging_level >= LoggingLevel.ERROR:
            print("ERROR: " + e)
            
        with open(self.file_name, "a") as file:
            file.write("ERROR: " + e)