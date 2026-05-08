"""Unit tests for PrimasAutomotoresUseCase — all I/O mocked."""

from unittest.mock import MagicMock, call

import polars as pl
import pytest

from src.application.use_cases.primas_automotores import PrimasAutomotoresUseCase
from src.domain.exceptions import ETLSourceError

PRIMAS_COLUMNS = [
    "femision", "fvigdesde", "fvighasta", "op", "componente", "suplemento",
    "cod_rama", "poliza", "aa_componente", "cap", "var", "air", "origen",
    "anio_componente", "cod_cobertura_aut", "cod_tipo_veh", "cod_uso_veh",
    "prima_tarifa_suplemento", "bon_prima_suplemento", "premio_suplemento",
    "premio_cobrado_suplemento", "cod_organizador", "cod_productor",
    "prima_tarifa_componente", "prima_rc_tarifa_componente",
    "prima_casco_tarifa_componente", "prima_neta_componente",
    "prima_rc_neta_componente", "prima_casco_neta_componente",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_use_case() -> PrimasAutomotoresUseCase:
    return PrimasAutomotoresUseCase(
        destination_port=MagicMock(),
        logger_port=MagicMock(),
    )


def sample_primas_df(n: int = 2) -> pl.DataFrame:
    from datetime import date
    return pl.DataFrame(
        {
            "femision": [date(2025, 1, 15)] * n,
            "fvigdesde": [date(2025, 1, 1)] * n,
            "fvighasta": [date(2026, 1, 1)] * n,
            "op": list(range(1, n + 1)),
            "componente": [1] * n,
            "suplemento": [0] * n,
            "cod_rama": [10] * n,
            "poliza": list(range(1000, 1000 + n)),
            "aa_componente": [50000.0] * n,
            "cap": [0] * n,
            "var": [0] * n,
            "air": [5] * n,
            "origen": ["N"] * n,
            "anio_componente": [2020] * n,
            "cod_cobertura_aut": ["A"] * n,
            "cod_tipo_veh": [1] * n,
            "cod_uso_veh": [1] * n,
            "prima_tarifa_suplemento": [1500.0] * n,
            "bon_prima_suplemento": [0.0] * n,
            "premio_suplemento": [1500.0] * n,
            "premio_cobrado_suplemento": [1500.0] * n,
            "cod_organizador": [10] * n,
            "cod_productor": [20] * n,
            "prima_tarifa_componente": [1500.0] * n,
            "prima_rc_tarifa_componente": [300.0] * n,
            "prima_casco_tarifa_componente": [1200.0] * n,
            "prima_neta_componente": [1400.0] * n,
            "prima_rc_neta_componente": [280.0] * n,
            "prima_casco_neta_componente": [1120.0] * n,
        }
    )


def make_source_multi_month(*month_dfs: pl.DataFrame) -> MagicMock:
    """Source that returns each df in sequence, then empty."""
    src = MagicMock()
    empty = pl.DataFrame({c: [] for c in PRIMAS_COLUMNS})
    side_effects = [df.lazy() for df in month_dfs] + [empty.lazy()]
    src.read_lazy.side_effect = side_effects
    return src


# ---------------------------------------------------------------------------
# execute — basic
# ---------------------------------------------------------------------------


class TestPrimasAutomotoresExecute:
    def test_returns_dict_with_expected_keys(self):
        uc = make_use_case()
        src = make_source_multi_month(sample_primas_df(3))
        result = uc.execute(source_port=src, year=2025)
        assert set(result.keys()) == {"total_rows", "months_processed", "year"}

    def test_correct_year_in_result(self):
        uc = make_use_case()
        src = make_source_multi_month(sample_primas_df())
        result = uc.execute(source_port=src, year=2024)
        assert result["year"] == 2024

    def test_counts_rows_across_months(self):
        uc = make_use_case()
        src = make_source_multi_month(sample_primas_df(3), sample_primas_df(5))
        result = uc.execute(source_port=src, year=2025)
        assert result["total_rows"] == 8
        assert result["months_processed"] == 2

    def test_stops_on_first_empty_month(self):
        uc = make_use_case()
        src = make_source_multi_month(sample_primas_df(2))
        result = uc.execute(source_port=src, year=2025)
        assert result["months_processed"] == 1

    def test_zero_rows_when_first_month_empty(self):
        uc = make_use_case()
        empty = pl.DataFrame({c: [] for c in PRIMAS_COLUMNS})
        src = MagicMock()
        src.read_lazy.return_value = empty.lazy()
        result = uc.execute(source_port=src, year=2025)
        assert result["total_rows"] == 0
        assert result["months_processed"] == 0

    def test_destination_not_called_when_no_data(self):
        uc = make_use_case()
        empty = pl.DataFrame({c: [] for c in PRIMAS_COLUMNS})
        src = MagicMock()
        src.read_lazy.return_value = empty.lazy()
        uc.execute(source_port=src, year=2025)
        uc.destination_port.write_lazy.assert_not_called()

    def test_destination_called_once_per_non_empty_month(self):
        uc = make_use_case()
        src = make_source_multi_month(sample_primas_df(2), sample_primas_df(3))
        uc.execute(source_port=src, year=2025)
        assert uc.destination_port.write_lazy.call_count == 2

    def test_query_includes_year_and_month(self):
        uc = make_use_case()
        src = make_source_multi_month(sample_primas_df())
        uc.execute(source_port=src, year=2023)
        first_query = src.read_lazy.call_args_list[0][0][0]
        assert "2023" in first_query
        assert "1" in first_query  # month = 1

    def test_propagates_source_error(self):
        uc = make_use_case()
        src = MagicMock()
        src.read_lazy.side_effect = ETLSourceError("timeout", cause=None)
        with pytest.raises(ETLSourceError):
            uc.execute(source_port=src, year=2025)

    def test_destination_not_called_on_source_error(self):
        uc = make_use_case()
        src = MagicMock()
        src.read_lazy.side_effect = ETLSourceError("error", cause=None)
        with pytest.raises(ETLSourceError):
            uc.execute(source_port=src, year=2025)
        uc.destination_port.write_lazy.assert_not_called()


# ---------------------------------------------------------------------------
# execute — month advancement
# ---------------------------------------------------------------------------


class TestPrimasMonthAdvancement:
    def test_advances_month_correctly(self):
        """Verifica que el segundo query use el mes siguiente."""
        uc = make_use_case()
        src = make_source_multi_month(sample_primas_df(), sample_primas_df())
        uc.execute(source_port=src, year=2025)
        queries = [c[0][0] for c in src.read_lazy.call_args_list]
        # Query 0: month 1, Query 1: month 2, Query 2: (empty, stops)
        assert "MONTH(FEmision) = 1" in queries[0] or "month=1" in queries[0].lower() or "= 1" in queries[0]
        assert "= 2" in queries[1]  # month 2

    def test_crosses_year_boundary(self):
        """12 meses de datos + uno vacío → 12 meses procesados."""
        uc = make_use_case()
        monthly_data = [sample_primas_df(1) for _ in range(12)]
        src = make_source_multi_month(*monthly_data)
        result = uc.execute(source_port=src, year=2025)
        assert result["months_processed"] == 12
        assert result["total_rows"] == 12


# ---------------------------------------------------------------------------
# post_execute
# ---------------------------------------------------------------------------


class TestPrimasPostExecute:
    def test_logs_year_and_row_count(self):
        uc = make_use_case()
        uc.post_execute({"total_rows": 1000, "months_processed": 5, "year": 2025})
        msgs = [c[0][0] for c in uc.logger_port.info.call_args_list]
        assert any("1000" in m for m in msgs)
        assert any("2025" in m for m in msgs)

    def test_no_business_log_when_result_is_none(self):
        uc = make_use_case()
        uc.post_execute(None)
        msgs = [c[0][0] for c in uc.logger_port.info.call_args_list]
        assert not any("filas" in m for m in msgs)


# ---------------------------------------------------------------------------
# EtlData registration
# ---------------------------------------------------------------------------


class TestPrimasEtlData:
    def test_domain_name(self):
        from src.domain.models.etl_definitions import PrimasAut_EtlData
        d = PrimasAut_EtlData()
        assert d.unique_name == "primas_automotores_x_componente"

    def test_schema_has_key_fields(self):
        from src.domain.models.etl_definitions import PrimasAut_EtlData
        schema = PrimasAut_EtlData.schema
        assert "femision" in schema
        assert "op" in schema
        assert "cod_cobertura_aut" in schema
        assert "prima_neta_componente" in schema
