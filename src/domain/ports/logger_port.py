from abc import ABC, abstractmethod
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class ILoggerPort(ABC):
    """Puerto de logger para loguear mensajes y errores."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del logger."""
        ...

    @abstractmethod
    def debug(self, message: str, **kwargs) -> None: ...

    @abstractmethod
    def info(self, message: str, **kwargs) -> None: ...

    @abstractmethod
    def warning(self, message: str, **kwargs) -> None: ...

    @abstractmethod
    def error(self, message: str, **kwargs) -> None: ...
