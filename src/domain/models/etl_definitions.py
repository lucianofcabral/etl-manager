"""Definiciones concretas de dominio ETL.

Cada clase une la identidad del proceso (unique_name, doc) con su contrato
de salida (schema). Son la fuente de verdad del dominio: cualquier use case
que produzca esos datos debe conformar el schema declarado aquí.
"""

from src.domain.models.entities import EtlData
from src.domain.models.schemas import (
    dim_coberturas_aut_schema,
    dim_coberturas_ramas_varias_schema,
    dimdaf_schema,
    organizadores_schema,
    primas_automotores_schema,
)


class CoberturasRVarias_EtlData(EtlData):
    """Dimensión de coberturas de ramas varias."""

    _domain_name = "coberturas_ramas_varias"
    schema = dim_coberturas_ramas_varias_schema

    def __init__(self) -> None:
        super().__init__(
            unique_name=self._domain_name,
            process_name="Coberturas Ramas Varias",
            doc="Carga la dimensión de coberturas de ramas varias.",
        )


class CoberturasAut_EtlData(EtlData):
    """Dimensión de coberturas de automotores."""

    _domain_name = "coberturas_automotores"
    schema = dim_coberturas_aut_schema

    def __init__(self) -> None:
        super().__init__(
            unique_name=self._domain_name,
            process_name="Coberturas Automotores",
            doc="Carga la dimensión de coberturas de automotores.",
        )


class DAF_EtlData(EtlData):
    """Dimensión de personas DAF."""

    _domain_name = "daf"
    schema = dimdaf_schema

    def __init__(self) -> None:
        super().__init__(
            unique_name=self._domain_name,
            process_name="Dimensión de Personas DAF",
            doc="Carga la dimensión de personas DAF.",
        )


class Organizadores_EtlData(EtlData):
    """Dimensión de organizadores."""

    _domain_name = "organizadores"
    schema = organizadores_schema

    def __init__(self) -> None:
        super().__init__(
            unique_name=self._domain_name,
            process_name="Organizadores",
            doc="Carga la dimensión de organizadores desde SEHINT01.",
        )


class PrimasAut_EtlData(EtlData):
    """Tabla de primas de automotores por componente."""

    _domain_name = "primas_automotores_x_componente"
    schema = primas_automotores_schema

    def __init__(self) -> None:
        super().__init__(
            unique_name=self._domain_name,
            process_name="Primas Automotores",
            doc=(
                "Ingesta de primas emitidas de automotores a nivel de "
                "suplemento/componente desde MySQL hacia ClickHouse."
            ),
        )
