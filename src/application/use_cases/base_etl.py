from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, ClassVar

import polars as pl

from src.application.decorators import logged_execution
from src.domain.exceptions import ETLConfigurationError
from src.domain.models.entities import EtlData, EtlProcess
from src.domain.models.enums import DestinationType, SourceType
from src.domain.ports.endpoints_port import IDestinationPort, ISourcePort
from src.domain.ports.logger_port import ILoggerPort
from src.domain.ports.query_port import IQueryPort

_use_case_registry: list[type["BaseETLUseCase"]] = []


class BaseETLUseCase(ABC):
    """Base para casos de uso ETL.

    Cada subclase define su dominio a través de `etl_data_class`, una subclase
    concreta de `EtlData` que encapsula identidad, documentación y schema canónico
    de salida. Alternativamente puede definir `name`/`description`/`doc`/`depends_on`
    directamente (modo compat, usado en tests y casos legacy).

    `execute` y `post_execute` se envuelven automáticamente con logging al construir
    la instancia — las subclases no necesitan saber nada del logger.

    Atributos de clase para fuentes:
        sources: Todos los SourceType que este proceso podría soportar (intención).
        implemented_sources: Subconjunto de `sources` con implementación real lista
            para correr. La UI usa este atributo para habilitar/deshabilitar opciones.
        user_facing: Si True (default), el use case es visible en la UI.
            Poner en False para pasos internos que no deben exponerse directamente.
    """

    etl_data_class: ClassVar[type[EtlData] | None] = None

    # Compat: usados cuando etl_data_class no está definido
    name: ClassVar[str]
    description: ClassVar[str]
    doc: ClassVar[str]
    depends_on: ClassVar[tuple[type["BaseETLUseCase"], ...]] = ()

    sources: ClassVar[list[SourceType]] = []
    implemented_sources: ClassVar[list[SourceType]] = []
    destinations: ClassVar[list[DestinationType]] = []
    user_facing: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        invalid = set(cls.implemented_sources) - set(cls.sources)
        if invalid:
            raise ETLConfigurationError(
                f"{cls.__name__}: implemented_sources contiene fuentes no declaradas "
                f"en sources: {invalid}. Agregálas a 'sources' primero."
            )
        # Registramos todas las subclases; las abstractas se filtran al consultar.
        _use_case_registry.append(cls)

    # ------------------------------------------------------------------
    # Métodos de clase para consultar el registro
    # ------------------------------------------------------------------

    @classmethod
    def all_registered(cls) -> list[type["BaseETLUseCase"]]:
        """Todas las subclases concretas registradas (sin clases abstractas)."""
        return [uc for uc in _use_case_registry if not uc.__abstractmethods__]

    @classmethod
    def find(
        cls,
        *,
        source: SourceType | None = None,
        destination: DestinationType | None = None,
        user_facing_only: bool = False,
        implemented_only: bool = False,
    ) -> list[type["BaseETLUseCase"]]:
        """Consulta el registro con filtros opcionales.

        Args:
            source: Filtra use cases que declaren esta fuente en ``sources``.
            destination: Filtra use cases que declaren este destino en ``destinations``.
            user_facing_only: Si True, excluye los marcados con ``user_facing = False``.
            implemented_only: Si True, solo incluye use cases que tengan al menos
                una fuente en ``implemented_sources``.
        """
        result = cls.all_registered()
        if source is not None:
            result = [uc for uc in result if source in uc.sources]
        if destination is not None:
            result = [uc for uc in result if destination in uc.destinations]
        if user_facing_only:
            result = [uc for uc in result if uc.user_facing]
        if implemented_only:
            result = [uc for uc in result if uc.implemented_sources]
        return result

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
        """Devuelve el EtlData de este use case.

        Si `etl_data_class` está definido, lo instancia (fuente de verdad del dominio).
        En caso contrario cae al modo compat usando `name`/`description`/`doc`.
        """
        if cls.etl_data_class is not None:
            return cls.etl_data_class()
        return EtlData(
            unique_name=cls.name,
            process_name=cls.description,
            doc=cls.doc,
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

    def produce_frame(self, source_port: ISourcePort, **kwargs: Any) -> pl.LazyFrame:
        """Lee y transforma datos, devolviendo un LazyFrame sin escribir en destino.

        Implementar este método es la forma preferida de definir la transformación.
        `execute()` lo puede llamar internamente para luego escribir el resultado.
        Otros use cases también pueden llamarlo para obtener datos intermedios
        y construir tablas planas desnormalizadas sin pasar por el destino.

        Por defecto lanza NotImplementedError; las subclases que deseen exponer
        este hook deben sobreescribirlo.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} no implementa produce_frame(). "
            "Sobreescribí este método para exponer la transformación pura."
        )

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
