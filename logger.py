from abc import ABC, abstractmethod
from datetime import date
from enum import Enum
from time import gmtime, strftime

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
        self.file_name = "Logs/Log-{0}.txt".format(date.today())
        self.logging_level = logging_level
        try:
            with open(self.file_name, "x") as file:
                pass  # Creates the file but does not write anything
        except FileExistsError:
            pass # File already exists
        
    def _write(self, m: str) -> None:
        now = strftime("%d/%m/%Y %I:%M:%S %p", gmtime())
        line = "{0} - {1}".format(now, m)
        
        with open(self.file_name, "a") as file:
            file.write(line + '\n')
        
    def debug(self, message: str) -> None:
        if self.logging_level.value <= LoggingLevel.DEBUG.value:
            print("DEBUG: " + message)
            
        self._write("DEBUG: " + message)
    
    def log(self, message: str) -> None:
        if self.logging_level.value <= LoggingLevel.INFO.value:
            print("INFO: " + message)
            
        self._write("INFO: " + message)
        
    def error(self, e: str) -> None:
        if self.logging_level.value <= LoggingLevel.ERROR.value:
            print("ERROR: " + e)
            
        self._write("ERROR: " + str(e))


# KAN-2
# turn Logger into a singleton
# create Logger object on load
# define public log, debug and error functions that use the Logger