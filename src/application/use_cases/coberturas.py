import polars as pl

from src.application.use_cases.base_dest_etl import ETLDestinationUseCase
from src.application.use_cases.base_etl import CompositeETLUseCase
from src.application.use_cases.base_source_etl import SourceETLUseCase
from src.domain.models.enums import DestinationType, SourceType
from src.domain.models.etl_definitions import CoberturasAut_EtlData
from src.domain.ports.endpoints_port import ISourcePort

_QUERY_COBERTURAS_AUT = """
    SELECT
        CodCobertura   AS cod_cobertura,
        OrCobertura    AS or_cobertura,
        CatCobertura   AS cat_cobertura,
        OrCatCobertura AS or_cat_cobertura,
        Rt             AS rt,
        Rp             AS rp,
        It             AS it,
        Ip             AS ip,
        At             AS at,
        Ap             AS ap
    FROM dims_coberturas_aut
"""


class CoberturasAut_MySQLSource(SourceETLUseCase):
    """Extrae coberturas de automotores desde MySQL."""

    source_type = SourceType.MYSQL
    input_schema = None  # se confía en el contrato SQL

    def extract(self, source_port: ISourcePort, **kwargs) -> pl.LazyFrame:
        return source_port.read_lazy(_QUERY_COBERTURAS_AUT)


class CoberturasAut_ClickhouseDest(ETLDestinationUseCase):
    """Carga coberturas de automotores en ClickHouse."""

    destination_type = DestinationType.CLICKHOUSE
    dest_input_schema = None  # el contrato intermedio ya lo garantiza

    def write(self, frame: pl.LazyFrame, **kwargs) -> dict:
        row_count = frame.select("cod_cobertura").collect().height
        self.destination_port.write_lazy(frame)
        return {"rows": row_count, "table": "coberturas_automotores"}


class CoberturasAutomotoresMySqlToClickhouseUseCase(CompositeETLUseCase):
    etl_data_class = CoberturasAut_EtlData
    source_etl_class = CoberturasAut_MySQLSource
    dest_etl_class = CoberturasAut_ClickhouseDest
    depends_on = ()

    def post_execute(self, result, **kwargs) -> None:
        if result:
            self.logger_port.info(
                f"[{self.process.etl_data.unique_name}] "
                f"{result['rows']} filas escritas en '{result['table']}'"
            )
