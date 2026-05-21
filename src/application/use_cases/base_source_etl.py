"""Base para use cases que manejan la frontera source/ETL."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import polars as pl

from src.application.use_cases._schema_validation import validate_minimum_schema
from src.domain.models.enums import SourceType
from src.domain.ports.endpoints_port import ISourcePort


class SourceETLUseCase(ABC):
    """Base para use cases que manejan la frontera source/ETL.

    Responsabilidades:
    - Leer datos crudos del source (``extract``, abstracto)
    - Validar ``input_schema`` mínimo contra los datos crudos (si está declarado)
    - Aplicar transformación exclusiva de esa fuente (``transform``, identidad por defecto)

    ``produce_frame`` orquesta los tres pasos y es el punto de entrada del composite.

    Atributos de clase:
        input_schema: Schema mínimo que debe entregar el source. ``None`` deshabilita validación.
        source_type: Tipo de fuente que este use case maneja.
    """

    input_schema: ClassVar[dict | None] = None
    source_type: ClassVar[SourceType]

    @abstractmethod
    def extract(self, source_port: ISourcePort, **kwargs: Any) -> pl.LazyFrame:
        """Lee datos crudos del source. Sin transformaciones."""
        ...

    def transform(self, frame: pl.LazyFrame, **kwargs: Any) -> pl.LazyFrame:
        """Transforma los datos crudos. Identidad por defecto; override para personalizar."""
        return frame

    def produce_frame(self, source_port: ISourcePort, **kwargs: Any) -> pl.LazyFrame:
        """Flujo completo: extract → validar input_schema → transform."""
        raw = self.extract(source_port, **kwargs)
        if self.__class__.input_schema is not None:
            validate_minimum_schema(
                raw,
                self.__class__.input_schema,
                f"{self.__class__.__name__}.input_schema",
            )
        return self.transform(raw, **kwargs)
