"""Tests for the topological dependency resolver."""

import pytest

from src.domain.models.entities import EtlData, EtlProcess, PipelineStatus
from src.domain.services.dependency_resolver import (
    dependencies_satisfied,
    resolve_etl_dependencies,
)


def etl(name: str) -> EtlData:
    return EtlData(unique_name=name, process_name=name, doc=name)


def process(etl_data: EtlData, status: PipelineStatus = PipelineStatus.IDLE) -> EtlProcess:
    p = EtlProcess(etl_data=etl_data)
    if status == PipelineStatus.RUNNING:
        p.change_status(True)
    elif status == PipelineStatus.SUCCESS:
        p.change_status(True)
        p.change_status(True)
    elif status == PipelineStatus.FAILED:
        p.change_status(False)
    return p


class TestResolveDependencies:
    def test_no_deps_returns_single_item(self):
        a = etl("a")
        result = resolve_etl_dependencies({a: []})
        assert result == [a]

    def test_linear_chain_respects_order(self):
        a, b, c = etl("a"), etl("b"), etl("c")
        # c depends on b, b depends on a  →  expected order: a, b, c
        result = resolve_etl_dependencies({a: [], b: [a], c: [b]})
        assert result.index(a) < result.index(b) < result.index(c)

    def test_independent_nodes_all_present(self):
        a, b = etl("a"), etl("b")
        result = resolve_etl_dependencies({a: [], b: []})
        assert set(result) == {a, b}

    def test_diamond_dependency(self):
        #   a
        #  / \
        # b   c
        #  \ /
        #   d
        a, b, c, d = etl("a"), etl("b"), etl("c"), etl("d")
        result = resolve_etl_dependencies({a: [], b: [a], c: [a], d: [b, c]})
        assert result.index(a) < result.index(b)
        assert result.index(a) < result.index(c)
        assert result.index(b) < result.index(d)
        assert result.index(c) < result.index(d)

    def test_circular_dependency_raises(self):
        a, b = etl("a"), etl("b")
        with pytest.raises(ValueError, match="[Cc]ircular"):
            resolve_etl_dependencies({a: [b], b: [a]})

    def test_returns_all_nodes_including_implicit_deps(self):
        # If a dep appears as a value but not as a key, it still must be in result
        a, b = etl("a"), etl("b")
        result = resolve_etl_dependencies({b: [a]})
        assert a in result
        assert b in result

    def test_empty_graph_returns_empty(self):
        result = resolve_etl_dependencies({})
        assert result == []

    def test_multiple_roots(self):
        a, b, c = etl("a"), etl("b"), etl("c")
        # a and b are roots; c depends on both
        result = resolve_etl_dependencies({a: [], b: [], c: [a, b]})
        assert result.index(a) < result.index(c)
        assert result.index(b) < result.index(c)


# ---------------------------------------------------------------------------
# dependencies_satisfied
# ---------------------------------------------------------------------------


class TestDependenciesSatisfied:
    def test_no_deps_always_satisfied(self):
        p = EtlProcess(etl_data=etl("a"))
        assert dependencies_satisfied(p) is True

    def test_dep_in_success_is_satisfied(self):
        dep_proc = process(etl("dep"), status=PipelineStatus.SUCCESS)
        p = EtlProcess(etl_data=etl("main"), dep_processes=[dep_proc])
        assert dependencies_satisfied(p) is True

    def test_dep_still_running_not_satisfied(self):
        dep_proc = process(etl("dep"), status=PipelineStatus.RUNNING)
        p = EtlProcess(etl_data=etl("main"), dep_processes=[dep_proc])
        assert dependencies_satisfied(p) is False

    def test_dep_failed_not_satisfied(self):
        dep_proc = process(etl("dep"), status=PipelineStatus.FAILED)
        p = EtlProcess(etl_data=etl("main"), dep_processes=[dep_proc])
        assert dependencies_satisfied(p) is False

    def test_dep_idle_not_satisfied(self):
        dep_proc = process(etl("dep"), status=PipelineStatus.IDLE)
        p = EtlProcess(etl_data=etl("main"), dep_processes=[dep_proc])
        assert dependencies_satisfied(p) is False

    def test_dep_absent_means_empty_dep_processes(self):
        p = EtlProcess(etl_data=etl("main"))
        assert dependencies_satisfied(p) is True

    def test_all_deps_must_succeed(self):
        pa = process(etl("a"), status=PipelineStatus.SUCCESS)
        pb = process(etl("b"), status=PipelineStatus.IDLE)
        p = EtlProcess(etl_data=etl("main"), dep_processes=[pa, pb])
        assert dependencies_satisfied(p) is False

    def test_all_deps_success_satisfied(self):
        pa = process(etl("a"), status=PipelineStatus.SUCCESS)
        pb = process(etl("b"), status=PipelineStatus.SUCCESS)
        p = EtlProcess(etl_data=etl("main"), dep_processes=[pa, pb])
        assert dependencies_satisfied(p) is True

    def test_extra_dep_processes_ignored_when_all_success(self):
        pa = process(etl("dep"), status=PipelineStatus.SUCCESS)
        pb = process(etl("extra"), status=PipelineStatus.SUCCESS)
        p = EtlProcess(etl_data=etl("main"), dep_processes=[pa, pb])
        assert dependencies_satisfied(p) is True
