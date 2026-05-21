import polars as pl

from src.application.use_cases.base_dest_etl import ETLDestinationUseCase
from src.application.use_cases.base_etl import CompositeETLUseCase
from src.application.use_cases.base_source_etl import SourceETLUseCase
from src.domain.models.enums import DestinationType, SourceType
from src.domain.models.etl_definitions import Organizadores_EtlData
from src.domain.ports.endpoints_port import ISourcePort

_QUERY_ORGANIZADORES = """
    SELECT
        s.ININNA  AS cod_organizador,
        s.INNRDF  AS nro_persona,
        s.DFNOMB  AS nombre,
        s.DFDOMI  AS domicilio,
        s.DFCOPO  AS cp,
        s.DFCOPS  AS cp_sufijo,
        s.LOLOCA  AS localidad,
        s.LOPROC  AS cod_provincia,
        s.DFTIDO  AS tipo_doc,
        s.DFNRDO  AS nro_doc,
        s.DFCUIT  AS cuit,
        s.PRPROD  AS provincia,
        s.PRRPRO  AS cod_inder_provincia,
        s.INMATR  AS matricula,
        gr.GPGRUP AS cod_grupo,
        gr.GPNOGR AS grupo
    FROM SEHINT01 s
    LEFT JOIN SETGRJ rel ON s.ININNA = rel.GJINTE
    LEFT JOIN SETGRP gr  ON rel.GJGRUP = gr.GPGRUP
    WHERE s.ININTA = 3
      AND s.DFNOMB <> 'LIBRE'
"""


class Organizadores_MySQLSource(SourceETLUseCase):
    """Extrae organizadores desde MySQL."""

    source_type = SourceType.MYSQL
    input_schema = None

    def extract(self, source_port: ISourcePort, **kwargs) -> pl.LazyFrame:
        return source_port.read_lazy(_QUERY_ORGANIZADORES)

    def transform(self, frame: pl.LazyFrame, **kwargs) -> pl.LazyFrame:
        return (
            frame.with_columns(
                [
                    pl.col("nombre").str.to_titlecase().str.strip_chars(),
                    pl.col("grupo").str.to_titlecase().str.strip_chars(),
                ]
            )
            .unique()
        )


class Organizadores_ClickhouseDest(ETLDestinationUseCase):
    """Carga organizadores en ClickHouse."""

    destination_type = DestinationType.CLICKHOUSE
    dest_input_schema = None

    def write(self, frame: pl.LazyFrame, **kwargs) -> dict:
        row_count = frame.select("cod_organizador").collect().height
        self.destination_port.write_lazy(frame)
        return {"rows": row_count, "table": "organizadores"}


class OrganizadoresUseCase(CompositeETLUseCase):
    etl_data_class = Organizadores_EtlData
    source_etl_class = Organizadores_MySQLSource
    dest_etl_class = Organizadores_ClickhouseDest
    depends_on = ()

    def post_execute(self, result, **kwargs) -> None:
        if result:
            self.logger_port.info(
                f"[{self.process.etl_data.unique_name}] "
                f"{result['rows']} filas escritas en '{result['table']}'"
            )
