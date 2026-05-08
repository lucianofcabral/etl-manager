"""Unit tests for coberturas use cases — all I/O mocked."""

from unittest.mock import MagicMock, call

import polars as pl
import pytest

from src.application.use_cases.coberturas import (
    CoberturasAutomotoresMySqlToClickhouseUseCase,
)
from src.application.use_cases.coberturas_rv import CoberturasRVUseCase
from src.domain.exceptions import ETLSourceError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_source(data: pl.DataFrame) -> MagicMock:
    """Builds a mock ISourcePort that returns `data` as a LazyFrame."""
    src = MagicMock()
    src.read_lazy.return_value = data.lazy()
    return src


def make_destination() -> MagicMock:
    return MagicMock()


def make_logger() -> MagicMock:
    return MagicMock()


def make_aut_use_case():
    return CoberturasAutomotoresMySqlToClickhouseUseCase(
        destination_port=make_destination(),
        logger_port=make_logger(),
    )


def make_rv_use_case():
    return CoberturasRVUseCase(
        destination_port=make_destination(),
        logger_port=make_logger(),
    )


# ---------------------------------------------------------------------------
# Sample DataFrames
# ---------------------------------------------------------------------------

AUT_COLUMNS = [
    "cod_cobertura", "or_cobertura", "cat_cobertura", "or_cat_cobertura",
    "rt", "rp", "it", "ip", "at", "ap",
]

RV_COLUMNS = ["cod_rama", "cod_cobertura", "cobertura", "pormilaje", "informe"]


def sample_aut_df(n: int = 3) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "cod_cobertura": [f"C{i:02}" for i in range(n)],
            "or_cobertura": list(range(n)),
            "cat_cobertura": ["CAT"] * n,
            "or_cat_cobertura": list(range(n)),
            "rt": [1] * n,
            "rp": [0] * n,
            "it": [1] * n,
            "ip": [0] * n,
            "at": [0] * n,
            "ap": [1] * n,
        }
    )


def sample_rv_df(n: int = 3) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "cod_rama": list(range(n)),
            "cod_cobertura": list(range(100, 100 + n)),
            "cobertura": [f"Cob {i}" for i in range(n)],
            "pormilaje": [1.5] * n,
            "informe": ["SI"] * n,
        }
    )


# ---------------------------------------------------------------------------
# CoberturasAutomotoresMySqlToClickhouseUseCase
# ---------------------------------------------------------------------------


class TestCoberturasAutExecute:
    def test_returns_row_count_and_table_name(self):
        uc = make_aut_use_case()
        src = make_source(sample_aut_df(5))
        result = uc.execute(source_port=src)
        assert result["rows"] == 5
        assert result["table"] == "coberturas_automotores"

    def test_calls_source_with_query(self):
        uc = make_aut_use_case()
        src = make_source(sample_aut_df())
        uc.execute(source_port=src)
        src.read_lazy.assert_called_once()
        query_arg = src.read_lazy.call_args[0][0]
        assert "dims_coberturas_aut" in query_arg

    def test_calls_destination_write_lazy(self):
        uc = make_aut_use_case()
        src = make_source(sample_aut_df(2))
        uc.execute(source_port=src)
        uc.destination_port.write_lazy.assert_called_once()

    def test_propagates_source_error(self):
        uc = make_aut_use_case()
        src = MagicMock()
        src.read_lazy.side_effect = ETLSourceError("DB caída", cause=None)
        with pytest.raises(ETLSourceError):
            uc.execute(source_port=src)

    def test_destination_not_called_on_source_error(self):
        uc = make_aut_use_case()
        src = MagicMock()
        src.read_lazy.side_effect = ETLSourceError("error", cause=None)
        with pytest.raises(ETLSourceError):
            uc.execute(source_port=src)
        uc.destination_port.write_lazy.assert_not_called()


class TestCoberturasAutPostExecute:
    def test_logs_row_count(self):
        uc = make_aut_use_case()
        uc.post_execute({"rows": 10, "table": "coberturas_automotores"})
        all_msgs = [c[0][0] for c in uc.logger_port.info.call_args_list]
        assert any("10" in m for m in all_msgs)

    def test_does_not_log_business_message_when_result_is_none(self):
        uc = make_aut_use_case()
        uc.post_execute(None)
        all_msgs = [c[0][0] for c in uc.logger_port.info.call_args_list]
        # logged_execution adds "iniciando"/"finalizado" — make sure no row-count msg
        assert not any("filas" in m for m in all_msgs)


# ---------------------------------------------------------------------------
# CoberturasRVUseCase
# ---------------------------------------------------------------------------


class TestCoberturasRVExecute:
    def test_returns_row_count_and_table_name(self):
        uc = make_rv_use_case()
        src = make_source(sample_rv_df(4))
        result = uc.execute(source_port=src)
        assert result["rows"] == 4
        assert result["table"] == "coberturas_ramas_varias"

    def test_calls_source_with_coberturas_rv_query(self):
        uc = make_rv_use_case()
        src = make_source(sample_rv_df())
        uc.execute(source_port=src)
        query_arg = src.read_lazy.call_args[0][0]
        assert "dims_coberturas_rv" in query_arg

    def test_calls_destination_when_data_present(self):
        uc = make_rv_use_case()
        src = make_source(sample_rv_df(2))
        uc.execute(source_port=src)
        uc.destination_port.write_lazy.assert_called_once()

    def test_skips_destination_when_empty(self):
        uc = make_rv_use_case()
        src = make_source(pl.DataFrame({c: [] for c in RV_COLUMNS}))
        result = uc.execute(source_port=src)
        uc.destination_port.write_lazy.assert_not_called()
        assert result["rows"] == 0

    def test_logs_skip_when_empty(self):
        uc = make_rv_use_case()
        src = make_source(pl.DataFrame({c: [] for c in RV_COLUMNS}))
        uc.execute(source_port=src)
        all_msgs = [c[0][0] for c in uc.logger_port.info.call_args_list]
        assert any("omite" in m for m in all_msgs)

    def test_propagates_source_error(self):
        uc = make_rv_use_case()
        src = MagicMock()
        src.read_lazy.side_effect = ETLSourceError("timeout", cause=None)
        with pytest.raises(ETLSourceError):
            uc.execute(source_port=src)


class TestCoberturasRVPostExecute:
    def test_logs_row_count(self):
        uc = make_rv_use_case()
        uc.post_execute({"rows": 7, "table": "coberturas_ramas_varias"})
        all_msgs = [c[0][0] for c in uc.logger_port.info.call_args_list]
        assert any("7" in m for m in all_msgs)

    def test_does_not_log_business_message_when_result_is_none(self):
        uc = make_rv_use_case()
        uc.post_execute(None)
        all_msgs = [c[0][0] for c in uc.logger_port.info.call_args_list]
        assert not any("filas" in m for m in all_msgs)


# ---------------------------------------------------------------------------
# produce_frame — CoberturasAutomotores
# ---------------------------------------------------------------------------


class TestCoberturasAutProduceFrame:
    def test_returns_lazy_frame(self):
        uc = make_aut_use_case()
        src = make_source(sample_aut_df(3))
        result = uc.produce_frame(source_port=src)
        assert isinstance(result, pl.LazyFrame)

    def test_does_not_write_to_destination(self):
        uc = make_aut_use_case()
        src = make_source(sample_aut_df(3))
        uc.produce_frame(source_port=src)
        uc.destination_port.write_lazy.assert_not_called()

    def test_frame_contains_expected_columns(self):
        uc = make_aut_use_case()
        src = make_source(sample_aut_df(2))
        frame = uc.produce_frame(source_port=src).collect()
        assert set(AUT_COLUMNS).issubset(set(frame.columns))

    def test_frame_row_count_matches_source(self):
        uc = make_aut_use_case()
        src = make_source(sample_aut_df(7))
        frame = uc.produce_frame(source_port=src).collect()
        assert frame.height == 7

    def test_calls_source_read_lazy(self):
        uc = make_aut_use_case()
        src = make_source(sample_aut_df())
        uc.produce_frame(source_port=src)
        src.read_lazy.assert_called_once()

    def test_can_be_used_as_input_to_join(self):
        """produce_frame puede consumirse como input de otro proceso (fan-in)."""
        uc = make_aut_use_case()
        src = make_source(sample_aut_df(3))
        coberturas = uc.produce_frame(source_port=src)
        extra = pl.DataFrame({"cod_cobertura": [f"C{i:02}" for i in range(3)], "extra": [1, 2, 3]}).lazy()
        joined = extra.join(coberturas, on="cod_cobertura", how="left").collect()
        assert joined.height == 3
        assert "rt" in joined.columns


# ---------------------------------------------------------------------------
# produce_frame — CoberturasRV
# ---------------------------------------------------------------------------


class TestCoberturasRVProduceFrame:
    def test_returns_lazy_frame(self):
        uc = make_rv_use_case()
        src = make_source(sample_rv_df(3))
        result = uc.produce_frame(source_port=src)
        assert isinstance(result, pl.LazyFrame)

    def test_does_not_write_to_destination(self):
        uc = make_rv_use_case()
        src = make_source(sample_rv_df(3))
        uc.produce_frame(source_port=src)
        uc.destination_port.write_lazy.assert_not_called()

    def test_frame_contains_expected_columns(self):
        uc = make_rv_use_case()
        src = make_source(sample_rv_df(2))
        frame = uc.produce_frame(source_port=src).collect()
        assert set(RV_COLUMNS).issubset(set(frame.columns))

    def test_returns_frame_even_when_empty(self):
        """produce_frame no hace skip-if-empty — eso es responsabilidad de execute()."""
        uc = make_rv_use_case()
        src = make_source(pl.DataFrame({c: [] for c in RV_COLUMNS}))
        frame = uc.produce_frame(source_port=src).collect()
        assert frame.height == 0
        uc.destination_port.write_lazy.assert_not_called()


# ---------------------------------------------------------------------------
# EtlData registration
# ---------------------------------------------------------------------------


class TestEtlDataRegistration:
    def test_coberturas_aut_has_correct_name(self):
        from src.domain.models.etl_definitions import CoberturasAut_EtlData
        d = CoberturasAut_EtlData()
        assert d.unique_name == "coberturas_automotores"

    def test_coberturas_rv_has_correct_name(self):
        from src.domain.models.etl_definitions import CoberturasRVarias_EtlData
        d = CoberturasRVarias_EtlData()
        assert d.unique_name == "coberturas_ramas_varias"

    def test_coberturas_aut_schema_has_expected_columns(self):
        from src.domain.models.etl_definitions import CoberturasAut_EtlData
        assert "cod_cobertura" in CoberturasAut_EtlData.schema
        assert "rt" in CoberturasAut_EtlData.schema
