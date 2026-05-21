"""Base para use cases que manejan la frontera ETL/destino."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import polars as pl

from src.application.use_cases._schema_validation import validate_minimum_schema
from src.domain.models.enums import DestinationType
from src.domain.ports.endpoints_port import IDestinationPort


class ETLDestinationUseCase(ABC):
    """Base para use cases que manejan la frontera ETL/destino.

    Responsabilidades:
    - Validar ``dest_input_schema`` mínimo contra el frame recibido (si está declarado)
    - Aplicar transformación exclusiva para ese destino (``transform_frame``, identidad por defecto)
    - Escribir al destino (``write``, abstracto)

    ``execute`` orquesta los tres pasos y es llamado por el composite.

    Atributos de clase:
        dest_input_schema: Schema mínimo que debe tener el frame entrante. ``None`` deshabilita validación.
        destination_type: Tipo de destino que este use case maneja.
    """

    dest_input_schema: ClassVar[dict | None] = None
    destination_type: ClassVar[DestinationType]

    def __init__(self, destination_port: IDestinationPort) -> None:
        self.destination_port = destination_port

    def transform_frame(self, frame: pl.LazyFrame, **kwargs: Any) -> pl.LazyFrame:
        """Transforma el frame antes de escribir. Identidad por defecto; override para personalizar."""
        return frame

    @abstractmethod
    def write(self, frame: pl.LazyFrame, **kwargs: Any) -> Any:
        """Escribe el frame al destino y devuelve el resultado."""
        ...

    def execute(self, frame: pl.LazyFrame, **kwargs: Any) -> Any:
        """Flujo completo: validar dest_input_schema → transform_frame → write."""
        if self.__class__.dest_input_schema is not None:
            validate_minimum_schema(
                frame,
                self.__class__.dest_input_schema,
                f"{self.__class__.__name__}.dest_input_schema",
            )
        transformed = self.transform_frame(frame, **kwargs)
        return self.write(transformed, **kwargs)
