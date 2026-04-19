from abc import ABC, abstractmethod
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

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

    def log_execution(self):
        """Decorador que loguea inicio, fin, duración y errores."""

        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                name = func.__name__
                self.info(f"Iniciando {name}")
                try:
                    result = func(*args, **kwargs)
                    self.info(f"Finalizó {name}")
                    return result
                except Exception as e:
                    self.error(f"Error en {name}: {e}")
                    raise

            return wrapper

        return decorator
