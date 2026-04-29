from src.domain.ports.logger_port import ILoggerPort


class CompositeLogger(ILoggerPort):
    """Delega los mensajes a múltiples loggers simultáneamente."""

    def __init__(self, *loggers: ILoggerPort, name: str = "CompositeLogger") -> None:
        if not loggers:
            raise ValueError("CompositeLogger requiere al menos un logger.")
        self._loggers = loggers
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def debug(self, message: str, **kwargs) -> None:
        for logger in self._loggers:
            logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        for logger in self._loggers:
            logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        for logger in self._loggers:
            logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        for logger in self._loggers:
            logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        for logger in self._loggers:
            if hasattr(logger, "critical"):
                logger.critical(message, **kwargs)
            else:
                logger.error(message, **kwargs)
