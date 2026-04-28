from src.application.use_cases.base_etl import BaseETLUseCase
from src.application.use_cases.coberturas import CoberturasMySqlToClickhouseUseCase
from src.application.use_cases.organizadores import OrganizadoresUseCase
from src.domain.models.enums import DestinationType, SourceType


class PrimasAutomotoresUseCase(BaseETLUseCase):
    name = "primas_automotores"
    description = "ETL de primas automotores desde MySQL hacia ClickHouse"
    doc = (
        "Procesa primas automotrices mes a mes, fusiona con organizadores y "
        "coberturas, y carga en ClickHouse"
    )
    depends_on = (OrganizadoresUseCase, CoberturasMySqlToClickhouseUseCase)
    sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, **kwargs):
        raise NotImplementedError

    def post_execute(self, result, **kwargs) -> None:
        raise NotImplementedError
