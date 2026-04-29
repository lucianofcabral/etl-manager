"""Tests para available_sources, unimplemented_sources e is_source_available."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.application.use_cases.base_etl import BaseETLUseCase
from src.domain.exceptions import ETLConfigurationError
from src.domain.models.enums import DestinationType, SourceType
from src.domain.ports.endpoints_port import IDestinationPort
from src.domain.ports.logger_port import ILoggerPort

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_deps():
    return MagicMock(spec=IDestinationPort), MagicMock(spec=ILoggerPort)


class NoSourcesETL(BaseETLUseCase):
    name = "no_sources"
    description = "ETL sin fuentes declaradas"
    doc = "Para tests"
    sources = []
    implemented_sources = []
    destinations = []

    def execute(self, **kwargs: Any): ...
    def post_execute(self, result: Any, **kwargs: Any) -> None: ...


class SingleSourceNotImplETL(BaseETLUseCase):
    name = "single_not_impl"
    description = "ETL con una fuente no implementada"
    doc = "Para tests"
    sources = [SourceType.MYSQL]
    implemented_sources = []
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, **kwargs: Any): ...
    def post_execute(self, result: Any, **kwargs: Any) -> None: ...


class SingleSourceImplETL(BaseETLUseCase):
    name = "single_impl"
    description = "ETL con una fuente implementada"
    doc = "Para tests"
    sources = [SourceType.MYSQL]
    implemented_sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, **kwargs: Any): ...
    def post_execute(self, result: Any, **kwargs: Any) -> None: ...


class MultiSourcePartialImplETL(BaseETLUseCase):
    name = "multi_partial"
    description = "ETL con varias fuentes, solo una implementada"
    doc = "Para tests"
    sources = [SourceType.MYSQL, SourceType.CSV, SourceType.EXCEL]
    implemented_sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, **kwargs: Any): ...
    def post_execute(self, result: Any, **kwargs: Any) -> None: ...


class MultiSourceAllImplETL(BaseETLUseCase):
    name = "multi_all_impl"
    description = "ETL con todas las fuentes implementadas"
    doc = "Para tests"
    sources = [SourceType.MYSQL, SourceType.CSV]
    implemented_sources = [SourceType.MYSQL, SourceType.CSV]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, **kwargs: Any): ...
    def post_execute(self, result: Any, **kwargs: Any) -> None: ...


# ---------------------------------------------------------------------------
# __init_subclass__ — validación de consistencia
# ---------------------------------------------------------------------------


class TestInitSubclassValidation:
    def test_implemented_subset_of_sources_is_valid(self):
        # No debe lanzar al definir la clase
        class ValidETL(BaseETLUseCase):
            name = "valid"
            description = "valid"
            doc = "valid"
            sources = [SourceType.MYSQL, SourceType.CSV]
            implemented_sources = [SourceType.MYSQL]
            destinations = []

            def execute(self, **kwargs: Any): ...
            def post_execute(self, result: Any, **kwargs: Any) -> None: ...

    def test_implemented_not_in_sources_raises_at_class_definition(self):
        with pytest.raises(ETLConfigurationError, match="implemented_sources"):

            class InvalidETL(BaseETLUseCase):
                name = "invalid"
                description = "invalid"
                doc = "invalid"
                sources = [SourceType.MYSQL]
                implemented_sources = [SourceType.CSV]  # CSV no está en sources
                destinations = []

                def execute(self, **kwargs: Any): ...
                def post_execute(self, result: Any, **kwargs: Any) -> None: ...

    def test_empty_implemented_with_empty_sources_is_valid(self):
        class EmptyETL(BaseETLUseCase):
            name = "empty"
            description = "empty"
            doc = "empty"
            sources = []
            implemented_sources = []
            destinations = []

            def execute(self, **kwargs: Any): ...
            def post_execute(self, result: Any, **kwargs: Any) -> None: ...


# ---------------------------------------------------------------------------
# available_sources
# ---------------------------------------------------------------------------


class TestAvailableSources:
    def test_empty_when_no_sources(self):
        assert NoSourcesETL.available_sources() == []

    def test_empty_when_none_implemented(self):
        assert SingleSourceNotImplETL.available_sources() == []

    def test_returns_implemented_sources(self):
        assert SingleSourceImplETL.available_sources() == [SourceType.MYSQL]

    def test_returns_only_implemented_subset(self):
        result = MultiSourcePartialImplETL.available_sources()
        assert result == [SourceType.MYSQL]
        assert SourceType.CSV not in result
        assert SourceType.EXCEL not in result

    def test_returns_all_when_all_implemented(self):
        result = MultiSourceAllImplETL.available_sources()
        assert set(result) == {SourceType.MYSQL, SourceType.CSV}


# ---------------------------------------------------------------------------
# unimplemented_sources
# ---------------------------------------------------------------------------


class TestUnimplementedSources:
    def test_empty_when_no_sources(self):
        assert NoSourcesETL.unimplemented_sources() == []

    def test_all_unimplemented_when_none_implemented(self):
        result = SingleSourceNotImplETL.unimplemented_sources()
        assert result == [SourceType.MYSQL]

    def test_empty_when_all_implemented(self):
        assert SingleSourceImplETL.unimplemented_sources() == []

    def test_complement_of_implemented(self):
        result = MultiSourcePartialImplETL.unimplemented_sources()
        assert set(result) == {SourceType.CSV, SourceType.EXCEL}

    def test_all_sources_covered(self):
        # available + unimplemented == sources
        avail = set(MultiSourcePartialImplETL.available_sources())
        not_impl = set(MultiSourcePartialImplETL.unimplemented_sources())
        declared = set(MultiSourcePartialImplETL.sources)
        assert avail | not_impl == declared
        assert avail & not_impl == set()


# ---------------------------------------------------------------------------
# is_source_available
# ---------------------------------------------------------------------------


class TestIsSourceAvailable:
    def test_false_for_undeclared_source(self):
        assert not NoSourcesETL.is_source_available(SourceType.MYSQL)

    def test_false_for_declared_but_unimplemented(self):
        assert not SingleSourceNotImplETL.is_source_available(SourceType.MYSQL)

    def test_true_for_implemented_source(self):
        assert SingleSourceImplETL.is_source_available(SourceType.MYSQL)

    def test_true_only_for_implemented_in_partial(self):
        assert MultiSourcePartialImplETL.is_source_available(SourceType.MYSQL)
        assert not MultiSourcePartialImplETL.is_source_available(SourceType.CSV)
        assert not MultiSourcePartialImplETL.is_source_available(SourceType.EXCEL)


# ---------------------------------------------------------------------------
# Casos de uso reales — smoke test de consistencia
# ---------------------------------------------------------------------------


class TestRealUseCasesConsistency:
    def test_coberturas_sources_superset_of_implemented(self):
        from src.application.use_cases.coberturas import (
            CoberturasAutomotoresMySqlToClickhouseUseCase,
        )

        impl = set(CoberturasAutomotoresMySqlToClickhouseUseCase.implemented_sources)
        declared = set(CoberturasAutomotoresMySqlToClickhouseUseCase.sources)
        assert impl <= declared

    def test_organizadores_sources_superset_of_implemented(self):
        from src.application.use_cases.organizadores import OrganizadoresUseCase

        impl = set(OrganizadoresUseCase.implemented_sources)
        declared = set(OrganizadoresUseCase.sources)
        assert impl <= declared

    def test_primas_sources_superset_of_implemented(self):
        from src.application.use_cases.primas_automotores import (
            PrimasAutomotoresUseCase,
        )

        impl = set(PrimasAutomotoresUseCase.implemented_sources)
        declared = set(PrimasAutomotoresUseCase.sources)
        assert impl <= declared

    def test_primas_declares_multiple_sources(self):
        from src.application.use_cases.primas_automotores import (
            PrimasAutomotoresUseCase,
        )

        assert len(PrimasAutomotoresUseCase.sources) > 1
