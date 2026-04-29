from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, ClassVar

from src.application.decorators import logged_execution
from src.domain.exceptions import ETLConfigurationError
from src.domain.models.entities import EtlData, EtlProcess
from src.domain.models.enums import DestinationType, SourceType
from src.domain.ports.endpoints_port import IDestinationPort
from src.domain.ports.logger_port import ILoggerPort
from src.domain.ports.query_port import IQueryPort


class BaseETLUseCase(ABC):
    """Base para casos de uso ETL.

    Cada subclase define su propio metadato (name, description, doc, depends_on)
    como atributos de clase. El proceso ETL se construye automáticamente a partir
    de esos metadatos.

    `execute` y `post_execute` se envuelven automáticamente con logging al construir
    la instancia — las subclases no necesitan saber nada del logger.

    Atributos de clase para fuentes:
        sources: Todos los SourceType que este proceso podría soportar (intención).
        implemented_sources: Subconjunto de `sources` con implementación real lista
            para correr. La UI usa este atributo para habilitar/deshabilitar opciones.
    """

    name: ClassVar[str]
    description: ClassVar[str]
    doc: ClassVar[str]
    depends_on: ClassVar[tuple[type["BaseETLUseCase"], ...]] = ()
    sources: ClassVar[list[SourceType]] = []
    implemented_sources: ClassVar[list[SourceType]] = []
    destinations: ClassVar[list[DestinationType]] = []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        invalid = set(cls.implemented_sources) - set(cls.sources)
        if invalid:
            raise ETLConfigurationError(
                f"{cls.__name__}: implemented_sources contiene fuentes no declaradas "
                f"en sources: {invalid}. Agregálas a 'sources' primero."
            )

    def __init__(
        self,
        destination_port: IDestinationPort,
        logger_port: ILoggerPort,
    ) -> None:
        self.process = EtlProcess(etl_data=self.__class__.as_etl_data())
        self.destination_port = destination_port
        self.logger_port = logger_port
        # Wrap automático: los use cases concretos solo implementan la lógica.
        self.execute = logged_execution(logger_port)(self.execute)
        self.post_execute = logged_execution(logger_port)(self.post_execute)

    @classmethod
    def as_etl_data(cls) -> EtlData:
        """Construye el EtlData de este use case a partir de sus atributos de clase."""
        return EtlData(
            unique_name=cls.name,
            process_name=cls.description,
            doc=cls.doc,
            depends_on=[dep.as_etl_data() for dep in cls.depends_on],
        )

    @classmethod
    def available_sources(cls) -> list[SourceType]:
        """Fuentes con implementación real lista para correr."""
        return list(cls.implemented_sources)

    @classmethod
    def unimplemented_sources(cls) -> list[SourceType]:
        """Fuentes declaradas en sources pero aún sin implementación."""
        impl = set(cls.implemented_sources)
        return [s for s in cls.sources if s not in impl]

    @classmethod
    def is_source_available(cls, source: SourceType) -> bool:
        """True si la fuente dada está implementada y lista para correr."""
        return source in cls.implemented_sources

    def queries_iterator(self, queries: list[IQueryPort] | IQueryPort) -> Iterator[Any]:
        """Itera sobre los resultados de las queries dadas."""
        if not isinstance(queries, list):
            queries = [queries]
        for q in queries:
            yield q.get_query_result_to_dataframe()

    def pre_checks(self, queries: list[IQueryPort] | IQueryPort) -> bool:
        """Devuelve True si todos los resultados de queries son truthy."""
        return all(self.queries_iterator(queries))

    @abstractmethod
    def execute(self, *args, **kwargs: Any) -> Any:
        """Ejecuta el proceso ETL."""
        ...

    @abstractmethod
    def post_execute(self, result: Any, **kwargs: Any) -> None:
        """Acciones post-ejecución (logging, limpieza, notificaciones)."""
        ...
