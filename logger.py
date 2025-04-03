from abc import ABC, abstractmethod
from enum import Enum

class LoggingLevel(Enum):
    DEBUG = 1
    INFO = 2
    ERROR = 3

class ILogger(ABC):
    
    @abstractmethod
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
        self.file_name = "Logs/Logs.txt"
        self.logging_level = logging_level
        try:
            with open(self.file_name, "x") as file:
                pass  # Creates the file but does not write anything
        except FileExistsError:
            pass # File already exists
        
    def debug(self, message: str) -> None:
        if self.logging_level.value >= LoggingLevel.DEBUG.value:
            print("DEBUG: " + message)
            
        with open(self.file_name, "a") as file:
            file.write("DEBUG: " + message + '\n')
    
    def log(self, message: str) -> None:
        if self.logging_level.value >= LoggingLevel.INFO.value:
            print("INFO: " + message)
            
        with open(self.file_name, "a") as file:
            file.write("INFO: " + message + '\n')
        
    def error(self, e: str) -> None:
        if self.logging_level.value >= LoggingLevel.ERROR.value:
            print("ERROR: " + e)
            
        with open(self.file_name, "a") as file:
            file.write("ERROR: " + str(e) + '\n')