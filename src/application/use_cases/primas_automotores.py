import datetime
from datetime import date, timedelta

import polars as pl

from src.application.use_cases.base_dest_etl import ETLDestinationUseCase
from src.application.use_cases.base_etl import CompositeETLUseCase
from src.application.use_cases.base_source_etl import SourceETLUseCase
from src.application.use_cases.coberturas import CoberturasAutomotoresMySqlToClickhouseUseCase
from src.application.use_cases.organizadores import OrganizadoresUseCase
from src.domain.models.enums import DestinationType, SourceType
from src.domain.models.etl_definitions import PrimasAut_EtlData
from src.domain.ports.endpoints_port import ISourcePort

_QUERY_PRIMAS_AUT = """
    SELECT
        FEmision              AS femision,
        FVigDesde             AS fvigdesde,
        FVigHasta             AS fvighasta,
        Op                    AS op,
        Comp                  AS componente,
        Supl                  AS suplemento,
        CodRama               AS cod_rama,
        Poliza                AS poliza,
        SaComponente          AS aa_componente,
        Cap                   AS cap,
        Var                   AS var,
        Air                   AS air,
        Origen                AS origen,
        AnioComponente        AS anio_componente,
        CodCoberturaAut       AS cod_cobertura_aut,
        CodTipoVeh            AS cod_tipo_veh,
        CodUsoVeh             AS cod_uso_veh,
        PrimaTarifaSupl       AS prima_tarifa_suplemento,
        BonPrimaSupl          AS bon_prima_suplemento,
        PremioSupl            AS premio_suplemento,
        PremioCobradoSupl     AS premio_cobrado_suplemento,
        CodOrganizador        AS cod_organizador,
        CodProductor          AS cod_productor,
        PrimaTarifaComp       AS prima_tarifa_componente,
        PrimaRcTarifaComp     AS prima_rc_tarifa_componente,
        PrimaCascoTarifaComp  AS prima_casco_tarifa_componente,
        PrimaNetaComp         AS prima_neta_componente,
        PrimaRcNetaComp       AS prima_rc_neta_componente,
        PrimaCascoNetaComp    AS prima_casco_neta_componente
    FROM primas_automotores
    WHERE YEAR(FEmision) = {year} AND MONTH(FEmision) = {month}
"""


class PrimasAut_MySQLSource(SourceETLUseCase):
    """Extrae primas de automotores desde MySQL para un mes/año específico."""

    source_type = SourceType.MYSQL
    input_schema = None

    def extract(self, source_port: ISourcePort, query: str = "", **kwargs) -> pl.LazyFrame:
        return source_port.read_lazy(query)


class PrimasAut_ClickhouseDest(ETLDestinationUseCase):
    """Carga primas de automotores en ClickHouse."""

    destination_type = DestinationType.CLICKHOUSE
    dest_input_schema = None

    def write(self, frame: pl.LazyFrame, **kwargs) -> None:
        self.destination_port.write_lazy(frame)


class PrimasAutomotoresUseCase(CompositeETLUseCase):
    etl_data_class = PrimasAut_EtlData
    source_etl_class = PrimasAut_MySQLSource
    dest_etl_class = PrimasAut_ClickhouseDest
    depends_on = (OrganizadoresUseCase, CoberturasAutomotoresMySqlToClickhouseUseCase)

    def execute(self, source_port: ISourcePort, year: int | None = None, **kwargs):
        """Carga primas automotores mes a mes desde enero del año dado.

        Args:
            source_port: Puerto de lectura hacia MySQL.
            year: Año a procesar. Por defecto el año en curso.

        Returns:
            Dict con ``total_rows``, ``months_processed`` y ``year``.
        """
        if year is None:
            year = datetime.date.today().year

        a, m = year, 1
        total_rows = 0
        months_processed = 0

        while True:
            query = _QUERY_PRIMAS_AUT.format(year=a, month=m)
            frame = self._source_etl.produce_frame(source_port, query=query)
            month_data: pl.DataFrame = frame.collect()

            if month_data.is_empty():
                break

            self._validate_etl_contract(month_data.lazy())
            self._dest_etl.execute(month_data.lazy())
            total_rows += month_data.height
            months_processed += 1

            next_date: date = date(a, m, 5) + timedelta(days=30)
            a, m = next_date.year, next_date.month

        return {
            "total_rows": total_rows,
            "months_processed": months_processed,
            "year": year,
        }

    def post_execute(self, result, **kwargs) -> None:
        if result:
            self.logger_port.info(
                f"[{self.process.etl_data.unique_name}] "
                f"Año {result['year']}: "
                f"{result['total_rows']} filas en {result['months_processed']} mes(es)"
            )
