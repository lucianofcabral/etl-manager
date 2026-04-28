from abc import ABC, abstractmethod
from pathlib import Path

import polars as pl


class ISourcePort(ABC):
    """Contrato base para toda fuente de datos."""

    @abstractmethod
    def read_lazy(self, *args, **kwargs) -> pl.LazyFrame:
        """Lee datos y los devuelve como LazyFrame de Polars."""
        ...


class ISourcePortDB(ISourcePort):
    """Contrato para fuentes de datos relacionales (MySQL, ClickHouse, etc)."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Prueba la conexión a la base de datos."""
        ...


class ISourcePortFile(ISourcePort):
    """Contrato para fuentes de datos basadas en archivos (CSV, Excel, Parquet)."""

    @property
    @abstractmethod
    def file_path(self) -> Path:
        """Ruta del archivo fuente."""
        ...


class IDestinationPort(ABC):
    """Contrato para todo destino de datos."""

    @abstractmethod
    def write_lazy(self, data: pl.LazyFrame, **kwargs) -> None:
        """Escribe un LazyFrame de Polars en el destino."""
        ...
