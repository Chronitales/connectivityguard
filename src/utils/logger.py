import logging
from logging.handlers import RotatingFileHandler
import os
from typing import Optional
from ..models.config import LoggingConfig

class Logger:
    _instance: Optional['Logger'] = None

    def __init__(self, config: LoggingConfig):
        if Logger._instance is not None:
            raise RuntimeError("Logger has already been initialized")
            
        self.logger = logging.getLogger('ConnectivityGuard')
        self.logger.setLevel(getattr(logging, config.level.upper()))
        
        os.makedirs(os.path.dirname(config.file_path), exist_ok=True)
        
        file_handler = RotatingFileHandler(
            config.file_path,
            maxBytes=config.max_size_mb * 1024 * 1024,
            backupCount=config.backup_count
        )
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        Logger._instance = self

    @classmethod
    def get_instance(cls) -> logging.Logger:
        if cls._instance is None:
            raise RuntimeError("Logger has not been initialized")
        return cls._instance.logger

    @classmethod
    def initialize(cls, config: LoggingConfig) -> None:
        if cls._instance is None:
            cls(config)

def get_logger() -> logging.Logger:
    return Logger.get_instance()