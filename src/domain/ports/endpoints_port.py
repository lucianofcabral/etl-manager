from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol

import polars as pl


class ISourcePort(ABC):
    """Contrato que deben cumplir todas las fuentes de datos que sean bases de datos (MySQL, ClickHouse, etc)."""

    @abstractmethod
    def read_lazy(self, *args, **kwargs) -> pl.LazyFrame:
        """Debe leer un dataframe y devolverlo como LazyFrame de Polars."""
        ...


class ISourcePortDB(ABC):
    """Contrato que deben cumplir todas las fuentes de datos que sean bases de datos (MySQL, ClickHouse, etc)."""

    @abstractmethod
    def read_lazy(self, *args, **kwargs) -> pl.LazyFrame:
        """Debe leer un dataframe y devolverlo como LazyFrame de Polars."""
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Debe probar la conexión a la base de datos y devolver True si es exitosa, False si no."""
        ...


class ISourcePortFile(ABC):
    """Contrato que deben cumplir todas las fuentes de datos que sean archivos (CSV, Excel, Parquet, etc)."""

    @property
    def file_path(self) -> Path:
        """Debe devolver la ruta del archivo."""
        ...

    @abstractmethod
    def read_lazy(self, *args, **kwargs) -> pl.LazyFrame:
        """Debe leer un dataframe y devolverlo como LazyFrame de Polars."""


class IDestinationPort(Protocol):
    """Contrato que deben cumplir todos los destinos de datos (DB, CSV, Parquet, etc)."""

    def write_lazy(self, data: pl.LazyFrame) -> None:
        """Debe escribir un LazyFrame de Polars en el destino."""
        ...
