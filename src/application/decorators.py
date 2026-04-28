"""Utilities for cross-cutting concerns in the application layer."""

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from src.domain.ports.logger_port import ILoggerPort

P = ParamSpec("P")
R = TypeVar("R")


def logged_execution(logger: ILoggerPort) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Envuelve una función con logging de inicio, fin y error.

    Solo depende de ILoggerPort — ninguna infraestructura concreta.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            logger.info(f"[{func.__qualname__}] iniciando")
            try:
                result = func(*args, **kwargs)
                logger.info(f"[{func.__qualname__}] finalizado")
                return result
            except Exception as e:
                logger.error(f"[{func.__qualname__}] error: {e}")
                raise

        return wrapper

    return decorator
