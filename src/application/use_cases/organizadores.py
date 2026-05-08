import polars as pl

from src.application.use_cases.base_etl import BaseETLUseCase
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


class OrganizadoresUseCase(BaseETLUseCase):
    etl_data_class = Organizadores_EtlData
    depends_on = ()
    sources = [SourceType.MYSQL, SourceType.EXCEL]
    implemented_sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def produce_frame(self, source_port: ISourcePort, **kwargs) -> pl.LazyFrame:
        return (
            source_port.read_lazy(_QUERY_ORGANIZADORES)
            .with_columns(
                [
                    pl.col("nombre").str.to_titlecase().str.strip_chars(),
                    pl.col("grupo").str.to_titlecase().str.strip_chars(),
                ]
            )
            .unique()
        )

    def execute(self, source_port: ISourcePort, **kwargs):
        data = self.produce_frame(source_port, **kwargs)
        row_count = data.select("cod_organizador").collect().height
        self.destination_port.write_lazy(data)
        return {"rows": row_count, "table": self.process.etl_data.unique_name}

    def post_execute(self, result, **kwargs) -> None:
        if result:
            self.logger_port.info(
                f"[{self.process.etl_data.unique_name}] "
                f"{result['rows']} filas escritas en '{result['table']}'"
            )
