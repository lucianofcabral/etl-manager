from src.application.use_cases.base_etl import BaseETLUseCase
from src.domain.models.enums import DestinationType, SourceType


class CoberturasAutomotoresMySqlToClickhouseUseCase(BaseETLUseCase):
    name = "coberturas_automotores"
    description = "ETL de coberturas de automotores desde MySQL hacia ClickHouse"
    doc = (
        "Carga la dimensión de coberturas desde MySQL a ClickHouse. "
        "También puede levantarse desde un CSV de respaldo si la base origen no está disponible."
    )
    depends_on = ()
    sources = [SourceType.MYSQL]
    implemented_sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, **kwargs):
        raise NotImplementedError

    def post_execute(self, result, **kwargs) -> None:
        raise NotImplementedError
