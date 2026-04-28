"""Tests for EtlData and EtlProcess domain entities."""

import pytest

from src.domain.models.entities import EtlData, EtlProcess, PipelineStatus


# ---------------------------------------------------------------------------
# EtlData
# ---------------------------------------------------------------------------


def make_etl_data(name: str = "etl_a", depends_on: list | None = None) -> EtlData:
    return EtlData(
        unique_name=name,
        process_name=f"Proceso {name}",
        doc=f"Documentación de {name}",
        depends_on=depends_on or [],
    )


class TestEtlData:
    def test_creation_ok(self):
        d = make_etl_data("foo")
        assert d.unique_name == "foo"
        assert d.depends_on == []

    def test_strips_whitespace_on_unique_name(self):
        d = make_etl_data("  foo  ")
        assert d.unique_name == "foo"

    def test_collapses_spaces_in_process_name(self):
        d = EtlData(unique_name="x", process_name="Nombre   con   espacios", doc="doc")
        assert d.process_name == "Nombre con espacios"

    def test_raises_if_unique_name_empty(self):
        with pytest.raises(ValueError):
            EtlData(unique_name="", process_name="p", doc="d")

    def test_raises_if_process_name_empty(self):
        with pytest.raises(ValueError):
            EtlData(unique_name="x", process_name="", doc="d")

    def test_raises_if_doc_empty(self):
        with pytest.raises(ValueError):
            EtlData(unique_name="x", process_name="p", doc="")

    def test_hash_based_on_unique_name(self):
        a = make_etl_data("foo")
        b = make_etl_data("foo")
        assert hash(a) == hash(b)

    def test_usable_as_dict_key(self):
        a = make_etl_data("foo")
        d = {a: "val"}
        assert d[a] == "val"

    def test_depends_on_accepts_etl_data_instances(self):
        dep = make_etl_data("dep")
        parent = make_etl_data("parent", depends_on=[dep])
        assert parent.depends_on[0].unique_name == "dep"


# ---------------------------------------------------------------------------
# EtlProcess — estado inicial
# ---------------------------------------------------------------------------


class TestEtlProcessInitial:
    def test_starts_idle(self):
        p = EtlProcess(etl_data=make_etl_data())
        assert p.status == PipelineStatus.IDLE

    def test_no_times_at_start(self):
        p = EtlProcess(etl_data=make_etl_data())
        assert p.start_time is None
        assert p.end_time is None

    def test_duration_none_at_start(self):
        p = EtlProcess(etl_data=make_etl_data())
        assert p.duration is None

    def test_audit_has_creation_entry(self):
        p = EtlProcess(etl_data=make_etl_data())
        assert len(p.audit) == 1
        assert "Objeto Creado" in p.audit[0]

    def test_hash_delegates_to_etl_data(self):
        d = make_etl_data("foo")
        p = EtlProcess(etl_data=d)
        assert hash(p) == hash(d)


# ---------------------------------------------------------------------------
# EtlProcess — transiciones válidas
# ---------------------------------------------------------------------------


class TestEtlProcessTransitions:
    def test_idle_true_goes_running(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)
        assert p.status == PipelineStatus.RUNNING

    def test_idle_true_sets_start_time(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)
        assert p.start_time is not None
        assert p.end_time is None

    def test_idle_false_goes_failed(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(False)
        assert p.status == PipelineStatus.FAILED

    def test_running_true_goes_success(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)  # IDLE → RUNNING
        p.change_status(True)  # RUNNING → SUCCESS
        assert p.status == PipelineStatus.SUCCESS

    def test_running_true_sets_end_time(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)
        p.change_status(True)
        assert p.end_time is not None

    def test_running_false_goes_failed(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)  # IDLE → RUNNING
        p.change_status(False)  # RUNNING → FAILED
        assert p.status == PipelineStatus.FAILED

    def test_success_true_goes_idle(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)  # → RUNNING
        p.change_status(True)  # → SUCCESS
        p.change_status(True)  # → IDLE
        assert p.status == PipelineStatus.IDLE

    def test_success_true_resets_times(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)
        p.change_status(True)
        p.change_status(True)  # → IDLE
        assert p.start_time is None
        assert p.end_time is None

    def test_failed_true_goes_idle(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(False)  # → FAILED
        p.change_status(True)  # → IDLE
        assert p.status == PipelineStatus.IDLE

    def test_failed_false_stays_failed(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(False)
        p.change_status(False)
        assert p.status == PipelineStatus.FAILED

    def test_audit_records_each_transition(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)  # IDLE → RUNNING
        p.change_status(True)  # RUNNING → SUCCESS
        # 1 entry from __post_init__ + 2 transitions
        assert len(p.audit) == 3
        assert "IDLE" in p.audit[1]
        assert "RUNNING" in p.audit[1]

    def test_duration_available_after_success(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)
        p.change_status(True)
        assert p.duration is not None
        assert p.duration >= 0.0

    def test_duration_available_after_failure(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)  # → RUNNING
        p.change_status(False)  # → FAILED
        assert p.duration is not None

    def test_duration_none_while_running(self):
        p = EtlProcess(etl_data=make_etl_data())
        p.change_status(True)
        assert p.duration is None
