"""Tests para la jerarquía de excepciones de dominio."""

import pytest

from src.domain.exceptions import (
    ETLConfigurationError,
    ETLDestinationError,
    ETLError,
    ETLSourceError,
    ETLTransformError,
)


class TestETLErrorHierarchy:
    def test_etl_source_error_is_etl_error(self):
        assert issubclass(ETLSourceError, ETLError)

    def test_etl_destination_error_is_etl_error(self):
        assert issubclass(ETLDestinationError, ETLError)

    def test_etl_configuration_error_is_etl_error(self):
        assert issubclass(ETLConfigurationError, ETLError)

    def test_etl_transform_error_is_etl_error(self):
        assert issubclass(ETLTransformError, ETLError)

    def test_all_are_exceptions(self):
        for cls in (ETLError, ETLSourceError, ETLDestinationError, ETLConfigurationError, ETLTransformError):
            assert issubclass(cls, Exception)


class TestETLErrorMessage:
    def test_message_is_preserved(self):
        err = ETLError("algo falló")
        assert str(err) == "algo falló"

    def test_cause_is_stored(self):
        original = ValueError("causa original")
        err = ETLError("wrapper", cause=original)
        assert err.cause is original

    def test_cause_chaining_via_dunder(self):
        original = RuntimeError("raíz")
        err = ETLSourceError("error de fuente", cause=original)
        assert err.__cause__ is original

    def test_no_cause_by_default(self):
        err = ETLError("sin causa")
        assert err.cause is None
        assert err.__cause__ is None

    def test_can_be_raised_and_caught(self):
        with pytest.raises(ETLError):
            raise ETLSourceError("falla al leer")

    def test_subclass_can_be_caught_as_base(self):
        with pytest.raises(ETLError):
            raise ETLDestinationError("falla al escribir")

    def test_raise_from_preserves_chain(self):
        original = ConnectionError("timeout")
        with pytest.raises(ETLConfigurationError) as exc_info:
            try:
                raise original
            except ConnectionError as e:
                raise ETLConfigurationError("no se pudo conectar", cause=e) from e
        assert exc_info.value.__cause__ is original
