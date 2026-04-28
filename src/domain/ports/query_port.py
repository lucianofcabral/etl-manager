from abc import ABC
from typing import Any

from polars import DataFrame

from src.domain.ports.endpoints_port import ISourcePortDB


class IQueryPort(ABC):
    """Define una consulta SQL lista para ejecutar sobre una fuente de base de datos."""

    source: ISourcePortDB
    query: str
    parameters: dict[str, Any] | None = None

    def get_query_result_to_dataframe(self) -> DataFrame:
        """Ejecuta la query sobre la fuente y devuelve el resultado como DataFrame."""
        return self.source.read_lazy(
            query=self.query, parameters=self.parameters
        ).collect()
