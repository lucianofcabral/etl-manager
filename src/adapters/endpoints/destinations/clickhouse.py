from typing import Any

import polars as pl
from clickhouse_connect import get_client

from src.domain.exceptions import ETLDestinationError
from src.domain.ports.endpoints_port import IDestinationPort


class ClickHouseDestination(IDestinationPort):
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
        table: str,
        **kwargs: Any,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.table = table
        self.kwargs = kwargs

    def get_client(self):
        return get_client(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            database=self.database,
        )

    def write_lazy(self, data: pl.LazyFrame, **kwargs) -> None:
        try:
            frame = data.collect()
            kwargs.setdefault("table", self.table)
            with self.get_client() as client:
                client.insert_arrow(arrow_table=frame.to_arrow(), **kwargs)
        except Exception as e:
            raise ETLDestinationError(
                f"Error escribiendo en ClickHouse (database={self.database}, table={self.table}): {e}",
                cause=e,
            ) from e

    def read_lazy(self, query: str, **kwargs) -> pl.DataFrame:
        try:
            with self.get_client() as client:
                result = client.query_arrow(query, **kwargs)
        except Exception as e:
            raise ETLDestinationError(
                f"Error leyendo desde ClickHouse (database={self.database}): {e}",
                cause=e,
            ) from e

        data = pl.from_arrow(result)
        if isinstance(data, pl.DataFrame):
            return data
        elif isinstance(data, pl.Series):
            return data.to_frame()

        raise ETLDestinationError(
            f"Tipo de dato inesperado retornado por ClickHouse: {type(data)}"
        )
