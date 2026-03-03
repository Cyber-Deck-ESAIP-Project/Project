import logging
import os
from datetime import datetime

class Logger:
    _instance = None

    def __init__(self):
        # Allow Pyre2 to recognize self.logger
        self.logger = logging.getLogger("CyberDeck")

    def __new__(cls, log_dir="logs", log_level=logging.DEBUG):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._init_logger(log_dir, log_level)
        return cls._instance

    def _init_logger(self, log_dir, log_level):
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = os.path.join(
            log_dir, f"cyberdeck_{datetime.now().strftime('%Y%m%d')}.log"
        )

        self.logger = logging.getLogger("CyberDeck")
        self.logger.setLevel(log_level)

        # Clear existing handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Create handlers
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler(log_file)
        c_handler.setLevel(log_level)
        f_handler.setLevel(log_level)

        # Create formatters and add it to handlers
        log_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        c_handler.setFormatter(log_format)
        f_handler.setFormatter(log_format)

        # Add handlers to the logger
        self.logger.addHandler(c_handler)
        self.logger.addHandler(f_handler)

    def get_logger(self):
        return self.logger

# Global convenience method
def get_logger():
    return Logger().get_logger()
