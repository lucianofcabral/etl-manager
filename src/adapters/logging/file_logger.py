import logging

from src.domain.ports.logger_port import ILoggerPort


class FileLogger(ILoggerPort):
    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __init__(self, filepath: str):
        self.logger = logging.getLogger(self.name)
        handler = logging.FileHandler(filepath)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def debug(self, message: str, **kwargs) -> None:
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs) -> None:
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs) -> None:
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs) -> None:
        self.logger.critical(message, extra=kwargs)
