"""Jerarquía de excepciones de dominio para ETL Manager."""

from __future__ import annotations


class ETLError(Exception):
    """Excepción base para todos los errores del dominio ETL."""

    def __init__(self, message: str, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause


class ETLSourceError(ETLError):
    """Error al leer datos de una fuente (base de datos, archivo, etc.)."""


class ETLDestinationError(ETLError):
    """Error al escribir datos en un destino."""


class ETLConfigurationError(ETLError):
    """Error de configuración: credenciales inválidas, env vars ausentes, etc."""


class ETLTransformError(ETLError):
    """Error durante la transformación de datos."""
