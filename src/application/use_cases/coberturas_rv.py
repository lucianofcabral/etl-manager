import polars as pl

from src.application.use_cases.base_dest_etl import ETLDestinationUseCase
from src.application.use_cases.base_etl import CompositeETLUseCase
from src.application.use_cases.base_source_etl import SourceETLUseCase
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


class CoberturasRV_MySQLSource(SourceETLUseCase):
    """Extrae coberturas de ramas varias desde MySQL."""

    source_type = SourceType.MYSQL
    input_schema = None

    def extract(self, source_port: ISourcePort, **kwargs) -> pl.LazyFrame:
        return source_port.read_lazy(_QUERY_COBERTURAS_RV)


class CoberturasRV_ClickhouseDest(ETLDestinationUseCase):
    """Carga coberturas de ramas varias en ClickHouse."""

    destination_type = DestinationType.CLICKHOUSE
    dest_input_schema = None

    def write(self, frame: pl.LazyFrame, **kwargs) -> dict:
        row_count = frame.select("cod_cobertura").collect().height
        self.destination_port.write_lazy(frame)
        return {"rows": row_count, "table": "coberturas_ramas_varias"}


class CoberturasRVUseCase(CompositeETLUseCase):
    etl_data_class = CoberturasRVarias_EtlData
    source_etl_class = CoberturasRV_MySQLSource
    dest_etl_class = CoberturasRV_ClickhouseDest
    depends_on = ()

    def execute(self, source_port: ISourcePort, **kwargs):
        frame = self._source_etl.produce_frame(source_port, **kwargs)
        data = frame.collect()
        if data.is_empty():
            self.logger_port.info(
                f"[{self.process.etl_data.unique_name}] sin filas en origen, se omite escritura"
            )
            return {"rows": 0, "table": self.process.etl_data.unique_name}
        self._validate_etl_contract(data.lazy())
        return self._dest_etl.execute(data.lazy(), **kwargs)

    def post_execute(self, result, **kwargs) -> None:
        if result:
            self.logger_port.info(
                f"[{self.process.etl_data.unique_name}] "
                f"{result['rows']} filas escritas en '{result['table']}'"
            )
