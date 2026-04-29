from src.application.use_cases.base_etl import BaseETLUseCase
from src.domain.models.enums import DestinationType, SourceType


class OrganizadoresUseCase(BaseETLUseCase):
    name = "organizadores"
    description = "ETL de dimensión organizadores desde MySQL hacia ClickHouse"
    doc = (
        "Carga la dimensión de organizadores de SEHINT01 a ClickHouse con SCD Type 2. "
        "Puede levantarse desde MySQL (fuente principal) o desde Excel como respaldo manual."
    )
    depends_on = ()
    sources = [SourceType.MYSQL, SourceType.EXCEL]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, **kwargs):
        raise NotImplementedError

    def post_execute(self, result, **kwargs) -> None:
        raise NotImplementedError
