from src.application.use_cases.base_etl import BaseETLUseCase
from src.domain.models.enums import DestinationType, SourceType


class CoberturasMySqlToClickhouseUseCase(BaseETLUseCase):
    name = "coberturas"
    description = "ETL de coberturas desde MySQL hacia ClickHouse"
    doc = "Carga la dimensión de coberturas desde MySQL a ClickHouse"
    depends_on = ()
    sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, **kwargs):
        raise NotImplementedError

    def post_execute(self, result, **kwargs) -> None:
        raise NotImplementedError
