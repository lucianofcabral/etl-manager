import polars as pl

from src.application.use_cases.base_etl import BaseETLUseCase
from src.domain.models.enums import DestinationType, SourceType
from src.domain.models.etl_definitions import CoberturasRVarias_EtlData
from src.domain.ports.endpoints_port import ISourcePort

_QUERY_COBERTURAS_RV = """
    SELECT
        `CodRama`      AS cod_rama,
        `CodCobertura` AS cod_cobertura,
        `Cobertura`    AS cobertura,
        `Pormilaje`    AS pormilaje,
        `Informe`      AS informe
    FROM dims_coberturas_rv
"""


class CoberturasRVUseCase(BaseETLUseCase):
    etl_data_class = CoberturasRVarias_EtlData
    depends_on = ()
    sources = [SourceType.MYSQL]
    implemented_sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def produce_frame(self, source_port: ISourcePort, **kwargs) -> pl.LazyFrame:
        return source_port.read_lazy(_QUERY_COBERTURAS_RV)

    def execute(self, source_port: ISourcePort, **kwargs):
        data = self.produce_frame(source_port, **kwargs)
        row_count = data.select("cod_cobertura").collect().height
        if row_count == 0:
            self.logger_port.info(
                f"[{self.process.etl_data.unique_name}] sin filas en origen, se omite escritura"
            )
            return {"rows": 0, "table": self.process.etl_data.unique_name}
        self.destination_port.write_lazy(data)
        return {"rows": row_count, "table": self.process.etl_data.unique_name}

    def post_execute(self, result, **kwargs) -> None:
        if result:
            self.logger_port.info(
                f"[{self.process.etl_data.unique_name}] "
                f"{result['rows']} filas escritas en '{result['table']}'"
            )
