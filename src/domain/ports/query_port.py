from abc import ABC
from typing import Any

from polars import DataFrame

from src.domain.ports.endpoints_port import ISourcePort


class IQueryPort(ABC):
    """Interfaz para definir una consulta SQL."""

    source: ISourcePort
    query: str
    parameters: dict[str, Any] | None = None

    def get_query_result_to_dataframe(self) -> DataFrame:
        """Devuelve el resultado de ejecutar la query como un Dataframe de Polars."""
        return self.source.read_lazy(
            query=self.query, parameters=self.parameters
        ).collect()
