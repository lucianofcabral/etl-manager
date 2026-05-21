"""Unit tests for OrganizadoresUseCase — all I/O mocked."""

from unittest.mock import MagicMock

import polars as pl
import pytest

from src.application.use_cases.organizadores import OrganizadoresUseCase
from src.domain.exceptions import ETLSourceError

ORG_COLUMNS = [
    "cod_organizador", "nro_persona", "nombre", "domicilio", "cp", "cp_sufijo",
    "localidad", "cod_provincia", "tipo_doc", "nro_doc", "cuit", "provincia",
    "cod_inder_provincia", "matricula", "cod_grupo", "grupo",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_source(data: pl.DataFrame) -> MagicMock:
    src = MagicMock()
    src.read_lazy.return_value = data.lazy()
    return src


def make_use_case() -> OrganizadoresUseCase:
    return OrganizadoresUseCase(
        destination_port=MagicMock(),
        logger_port=MagicMock(),
    )


def sample_org_df(n: int = 3) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "cod_organizador": pl.Series(list(range(1, n + 1)), dtype=pl.UInt32),
            "nro_persona": pl.Series(list(range(100, 100 + n)), dtype=pl.UInt32),
            "nombre": pl.Series([f"JUAN PEREZ {i}" for i in range(n)], dtype=pl.String),
            "domicilio": pl.Series([f"Calle {i}" for i in range(n)], dtype=pl.String),
            "cp": pl.Series([5000] * n, dtype=pl.UInt32),
            "cp_sufijo": pl.Series([0] * n, dtype=pl.UInt32),
            "localidad": pl.Series(["CORDOBA"] * n, dtype=pl.String),
            "cod_provincia": pl.Series(["CB"] * n, dtype=pl.String),
            "tipo_doc": pl.Series(["DNI"] * n, dtype=pl.String),
            "nro_doc": pl.Series(list(range(30_000_000, 30_000_000 + n)), dtype=pl.UInt32),
            "cuit": pl.Series([f"20-3000000{i}-9" for i in range(n)], dtype=pl.String),
            "provincia": pl.Series(["CORDOBA"] * n, dtype=pl.String),
            "cod_inder_provincia": pl.Series(["14"] * n, dtype=pl.String),
            "matricula": pl.Series(list(range(1000, 1000 + n)), dtype=pl.UInt32),
            "cod_grupo": pl.Series([1] * n, dtype=pl.UInt32),
            "grupo": pl.Series([f"GRUPO {i}" for i in range(n)], dtype=pl.String),
        }
    )


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------


class TestOrganizadoresExecute:
    def test_returns_row_count_and_table_name(self):
        uc = make_use_case()
        result = uc.execute(source_port=make_source(sample_org_df(4)))
        assert result["rows"] == 4
        assert result["table"] == "organizadores"

    def test_calls_source_with_sehint01_query(self):
        uc = make_use_case()
        uc.execute(source_port=make_source(sample_org_df()))
        query_arg = uc.destination_port.write_lazy.call_args  # destination was called
        src_call = make_source(sample_org_df())
        uc2 = make_use_case()
        uc2.execute(source_port=src_call)
        query = src_call.read_lazy.call_args[0][0]
        assert "SEHINT01" in query

    def test_calls_destination_write_lazy(self):
        uc = make_use_case()
        uc.execute(source_port=make_source(sample_org_df(2)))
        uc.destination_port.write_lazy.assert_called_once()

    def test_propagates_source_error(self):
        uc = make_use_case()
        src = MagicMock()
        src.read_lazy.side_effect = ETLSourceError("DB caída", cause=None)
        with pytest.raises(ETLSourceError):
            uc.execute(source_port=src)

    def test_destination_not_called_on_source_error(self):
        uc = make_use_case()
        src = MagicMock()
        src.read_lazy.side_effect = ETLSourceError("error", cause=None)
        with pytest.raises(ETLSourceError):
            uc.execute(source_port=src)
        uc.destination_port.write_lazy.assert_not_called()


# ---------------------------------------------------------------------------
# produce_frame
# ---------------------------------------------------------------------------


class TestOrganizadoresProduceFrame:
    def test_returns_lazy_frame(self):
        uc = make_use_case()
        result = uc.produce_frame(source_port=make_source(sample_org_df(3)))
        assert isinstance(result, pl.LazyFrame)

    def test_does_not_write_to_destination(self):
        uc = make_use_case()
        uc.produce_frame(source_port=make_source(sample_org_df(3)))
        uc.destination_port.write_lazy.assert_not_called()

    def test_frame_contains_expected_columns(self):
        uc = make_use_case()
        frame = uc.produce_frame(source_port=make_source(sample_org_df(2))).collect()
        assert set(ORG_COLUMNS).issubset(set(frame.columns))

    def test_nombre_is_titlecase(self):
        uc = make_use_case()
        frame = uc.produce_frame(source_port=make_source(sample_org_df(2))).collect()
        assert all(n == n.title() or n[0].isupper() for n in frame["nombre"].to_list())

    def test_unique_deduplicates_rows(self):
        """Rows duplicadas deben eliminarse."""
        df = sample_org_df(2)
        df_dup = pl.concat([df, df])  # 4 rows, but 2 unique
        uc = make_use_case()
        frame = uc.produce_frame(source_port=make_source(df_dup)).collect()
        assert frame.height == 2

    def test_frame_row_count_matches_source(self):
        uc = make_use_case()
        frame = uc.produce_frame(source_port=make_source(sample_org_df(5))).collect()
        assert frame.height == 5

    def test_can_be_used_as_join_input(self):
        uc = make_use_case()
        org = uc.produce_frame(source_port=make_source(sample_org_df(3)))
        primas = pl.DataFrame(
            {"cod_organizador": [1, 2, 3], "prima": [100.0, 200.0, 300.0]}
        ).lazy()
        joined = primas.join(org, on="cod_organizador", how="left").collect()
        assert joined.height == 3
        assert "nombre" in joined.columns


# ---------------------------------------------------------------------------
# post_execute
# ---------------------------------------------------------------------------


class TestOrganizadoresPostExecute:
    def test_logs_row_count(self):
        uc = make_use_case()
        uc.post_execute({"rows": 42, "table": "organizadores"})
        msgs = [c[0][0] for c in uc.logger_port.info.call_args_list]
        assert any("42" in m for m in msgs)

    def test_no_business_log_when_result_is_none(self):
        uc = make_use_case()
        uc.post_execute(None)
        msgs = [c[0][0] for c in uc.logger_port.info.call_args_list]
        assert not any("filas" in m for m in msgs)


# ---------------------------------------------------------------------------
# EtlData registration
# ---------------------------------------------------------------------------


class TestOrganizadoresEtlData:
    def test_domain_name(self):
        from src.domain.models.etl_definitions import Organizadores_EtlData
        d = Organizadores_EtlData()
        assert d.unique_name == "organizadores"

    def test_schema_has_expected_fields(self):
        from src.domain.models.etl_definitions import Organizadores_EtlData
        assert "cod_organizador" in Organizadores_EtlData.schema
        assert "nombre" in Organizadores_EtlData.schema
        assert "grupo" in Organizadores_EtlData.schema
