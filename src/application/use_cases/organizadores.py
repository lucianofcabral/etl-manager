from src.application.use_cases.base_etl import BaseETLUseCase
from src.domain.models.enums import DestinationType, SourceType


class OrganizadoresUseCase(BaseETLUseCase):
    name = "organizadores"
    description = "ETL de dimensión organizadores desde MySQL hacia ClickHouse"
    doc = "Carga la dimensión de organizadores de SEHINT01 a ClickHouse con SCD Type 2"
    depends_on = ()
    sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, **kwargs):
        raise NotImplementedError

    def post_execute(self, result, **kwargs) -> None:
        raise NotImplementedError
