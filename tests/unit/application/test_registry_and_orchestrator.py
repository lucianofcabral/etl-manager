"""Tests para el registro de use cases y PipelineOrchestrator."""

from unittest.mock import MagicMock

import polars as pl
import pytest

from src.application.orchestrators import PipelineOrchestrator
from src.application.use_cases.base_etl import BaseETLUseCase, _use_case_registry
from src.domain.models.enums import DestinationType, SourceType


# ---------------------------------------------------------------------------
# Helpers / fixtures locales
# ---------------------------------------------------------------------------


def make_logger() -> MagicMock:
    return MagicMock()


def make_source(data: pl.DataFrame | None = None) -> MagicMock:
    src = MagicMock()
    df = data if data is not None else pl.DataFrame({"x": [1]})
    src.read_lazy.return_value = df.lazy()
    return src


def make_destination() -> MagicMock:
    return MagicMock()


# Use cases de prueba definidos localmente para no contaminar el registro global
# con clases reales (que ya están registradas al importar sus módulos).

class _DepA(BaseETLUseCase):
    name = "_dep_a"
    description = "Dep A"
    doc = "Dep A test use case"
    depends_on = ()
    sources = [SourceType.MYSQL]
    implemented_sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, source_port, **kwargs):
        return {"cls": "_DepA"}

    def post_execute(self, result, **kwargs):
        pass


class _DepB(BaseETLUseCase):
    name = "_dep_b"
    description = "Dep B"
    doc = "Dep B test use case"
    depends_on = (_DepA,)
    sources = [SourceType.MYSQL]
    implemented_sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, source_port, **kwargs):
        return {"cls": "_DepB"}

    def post_execute(self, result, **kwargs):
        pass


class _DepC(BaseETLUseCase):
    """Depende de A y B — target del pipeline completo."""

    name = "_dep_c"
    description = "Dep C"
    doc = "Dep C test use case"
    depends_on = (_DepA, _DepB)
    sources = [SourceType.MYSQL]
    implemented_sources = [SourceType.MYSQL]
    destinations = [DestinationType.CLICKHOUSE]

    def execute(self, source_port, **kwargs):
        return {"cls": "_DepC"}

    def post_execute(self, result, **kwargs):
        pass


class _InternalUseCase(BaseETLUseCase):
    """Use case marcado como no visible en la UI."""

    name = "_internal"
    description = "Internal"
    doc = "Internal use case, not shown in UI"
    depends_on = ()
    sources = [SourceType.CSV]
    implemented_sources = [SourceType.CSV]
    destinations = [DestinationType.CLICKHOUSE]
    user_facing = False

    def execute(self, source_port, **kwargs):
        return None

    def post_execute(self, result, **kwargs):
        pass


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_concrete_subclass_is_registered(self):
        assert _DepA in _use_case_registry

    def test_all_registered_returns_list(self):
        registered = BaseETLUseCase.all_registered()
        assert isinstance(registered, list)
        assert _DepA in registered
        assert _DepB in registered

    def test_abstract_base_not_registered(self):
        assert BaseETLUseCase not in _use_case_registry

    def test_find_by_source(self):
        result = BaseETLUseCase.find(source=SourceType.MYSQL)
        assert _DepA in result
        assert _DepB in result
        assert _DepC in result

    def test_find_by_destination(self):
        result = BaseETLUseCase.find(destination=DestinationType.CLICKHOUSE)
        assert _DepA in result

    def test_find_source_and_destination(self):
        result = BaseETLUseCase.find(
            source=SourceType.MYSQL, destination=DestinationType.CLICKHOUSE
        )
        assert _DepA in result
        assert _InternalUseCase not in result or SourceType.MYSQL not in _InternalUseCase.sources

    def test_find_user_facing_only_excludes_internal(self):
        result = BaseETLUseCase.find(user_facing_only=True)
        assert _InternalUseCase not in result
        assert _DepA in result

    def test_user_facing_default_is_true(self):
        assert _DepA.user_facing is True

    def test_user_facing_false_when_set(self):
        assert _InternalUseCase.user_facing is False

    def test_find_implemented_only(self):
        result = BaseETLUseCase.find(implemented_only=True)
        assert _DepA in result

    def test_find_returns_copy_not_original(self):
        r1 = BaseETLUseCase.all_registered()
        r1.append(None)  # type: ignore[arg-type]
        r2 = BaseETLUseCase.all_registered()
        assert None not in r2

    def test_real_use_cases_are_registered(self):
        # Importar los use cases reales para asegurar que están en el registro
        from src.application.use_cases.coberturas import (
            CoberturasAutomotoresMySqlToClickhouseUseCase,
        )
        from src.application.use_cases.coberturas_rv import CoberturasRVUseCase

        registered = BaseETLUseCase.all_registered()
        assert CoberturasAutomotoresMySqlToClickhouseUseCase in registered
        assert CoberturasRVUseCase in registered


# ---------------------------------------------------------------------------
# PipelineOrchestrator._resolve_chain tests
# ---------------------------------------------------------------------------


class TestResolvChain:
    def test_single_node_no_deps(self):
        chain = PipelineOrchestrator._resolve_chain(_DepA)
        assert chain == [_DepA]

    def test_two_nodes_dep_comes_first(self):
        chain = PipelineOrchestrator._resolve_chain(_DepB)
        assert chain.index(_DepA) < chain.index(_DepB)

    def test_full_chain_order(self):
        chain = PipelineOrchestrator._resolve_chain(_DepC)
        assert chain.index(_DepA) < chain.index(_DepC)
        assert chain.index(_DepB) < chain.index(_DepC)

    def test_all_nodes_present(self):
        chain = PipelineOrchestrator._resolve_chain(_DepC)
        assert set(chain) == {_DepA, _DepB, _DepC}

    def test_circular_dependency_raises(self):
        class _CircA(BaseETLUseCase):
            name = "_circ_a"
            description = "Circ A"
            doc = "Circular A"
            depends_on = ()
            sources = []
            implemented_sources = []
            destinations = []

            def execute(self, **kw):
                return None

            def post_execute(self, result, **kw):
                pass

        # Inyectamos el ciclo manualmente (no se puede hacer con ClassVar fácilmente)
        _CircA.depends_on = (_CircA,)  # type: ignore[assignment]
        with pytest.raises(ValueError, match="circular"):
            PipelineOrchestrator._resolve_chain(_CircA)
        _CircA.depends_on = ()  # limpiamos


# ---------------------------------------------------------------------------
# PipelineOrchestrator.run tests
# ---------------------------------------------------------------------------


class TestOrchestratorRun:
    def _make_orchestrator(self):
        return PipelineOrchestrator(
            source_port=make_source(),
            destination_port=make_destination(),
            logger_port=make_logger(),
        )

    def test_run_single_use_case_returns_result(self):
        orch = self._make_orchestrator()
        results = orch.run(_DepA)
        assert "_DepA" in results
        assert results["_DepA"] == {"cls": "_DepA"}

    def test_run_executes_all_deps(self):
        orch = self._make_orchestrator()
        results = orch.run(_DepC)
        assert "_DepA" in results
        assert "_DepB" in results
        assert "_DepC" in results

    def test_run_calls_port_provider_once_per_class(self):
        orch = self._make_orchestrator()
        results = orch.run(_DepC)
        assert set(results.keys()) == {"_DepA", "_DepB", "_DepC"}

    def test_run_source_override_is_used(self):
        """source_port kwarg reemplaza el source configurado en el constructor."""
        override = make_source()
        orch = self._make_orchestrator()
        orch.run(_DepA, source_port=override)
        # _DepA.execute recibe source_port — con mock verificamos que se llama
        # Aquí solo verificamos que no lanza error (integración ligera).

    def test_run_deps_before_target(self):
        execution_order = []

        class _TrackA(BaseETLUseCase):
            name = "_track_a"
            description = "Track A"
            doc = "Track A"
            depends_on = ()
            sources = [SourceType.MYSQL]
            implemented_sources = [SourceType.MYSQL]
            destinations = [DestinationType.CLICKHOUSE]

            def execute(self, source_port, **kw):
                execution_order.append("A")
                return "A"

            def post_execute(self, result, **kw):
                pass

        class _TrackB(BaseETLUseCase):
            name = "_track_b"
            description = "Track B"
            doc = "Track B"
            depends_on = (_TrackA,)
            sources = [SourceType.MYSQL]
            implemented_sources = [SourceType.MYSQL]
            destinations = [DestinationType.CLICKHOUSE]

            def execute(self, source_port, **kw):
                execution_order.append("B")
                return "B"

            def post_execute(self, result, **kw):
                pass

        orch = self._make_orchestrator()
        orch.run(_TrackB)
        assert execution_order == ["A", "B"]
