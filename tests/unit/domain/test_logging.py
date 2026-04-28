"""Tests for logged_execution decorator and BaseETLUseCase auto-wrapping."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.application.decorators import logged_execution
from src.application.use_cases.base_etl import BaseETLUseCase
from src.domain.ports.endpoints_port import IDestinationPort
from src.domain.ports.logger_port import ILoggerPort


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_logger() -> ILoggerPort:
    mock = MagicMock(spec=ILoggerPort)
    mock.name = "test_logger"
    return mock


def make_destination() -> IDestinationPort:
    return MagicMock(spec=IDestinationPort)


class ConcreteETL(BaseETLUseCase):
    name = "test_etl"
    description = "ETL de prueba"
    doc = "ETL usado en tests"
    depends_on = ()

    def execute(self, **kwargs: Any) -> str:
        return "resultado"

    def post_execute(self, result: Any, **kwargs: Any) -> None:
        pass


class FailingETL(BaseETLUseCase):
    name = "failing_etl"
    description = "ETL que falla"
    doc = "ETL que lanza excepción en execute"
    depends_on = ()

    def execute(self, **kwargs: Any) -> None:
        raise ValueError("algo salió mal")

    def post_execute(self, result: Any, **kwargs: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# logged_execution decorator
# ---------------------------------------------------------------------------


class TestLoggedExecution:
    def test_logs_start_and_end_on_success(self):
        logger = make_logger()

        @logged_execution(logger)
        def my_fn():
            return 42

        result = my_fn()
        assert result == 42
        assert logger.info.call_count == 2
        first_call = logger.info.call_args_list[0][0][0]
        second_call = logger.info.call_args_list[1][0][0]
        assert "my_fn" in first_call
        assert "my_fn" in second_call

    def test_logs_error_and_reraises_on_exception(self):
        logger = make_logger()

        @logged_execution(logger)
        def boom():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            boom()

        assert logger.error.call_count == 1
        error_msg = logger.error.call_args[0][0]
        assert "boom" in error_msg

    def test_preserves_function_name(self):
        logger = make_logger()

        @logged_execution(logger)
        def my_named_fn():
            pass

        assert my_named_fn.__name__ == "my_named_fn"

    def test_passes_return_value_through(self):
        logger = make_logger()

        @logged_execution(logger)
        def returns_dict():
            return {"key": "value"}

        assert returns_dict() == {"key": "value"}

    def test_passes_args_and_kwargs_through(self):
        logger = make_logger()
        received = {}

        @logged_execution(logger)
        def capture(a, b, c=None):
            received.update({"a": a, "b": b, "c": c})

        capture(1, 2, c=3)
        assert received == {"a": 1, "b": 2, "c": 3}


# ---------------------------------------------------------------------------
# BaseETLUseCase — auto-wrapping en __init__
# ---------------------------------------------------------------------------


class TestBaseETLUseCaseAutoLogging:
    def test_execute_logs_on_success(self):
        logger = make_logger()
        etl = ConcreteETL(destination_port=make_destination(), logger_port=logger)
        etl.execute()
        assert logger.info.call_count >= 2

    def test_execute_logs_error_on_exception(self):
        logger = make_logger()
        etl = FailingETL(destination_port=make_destination(), logger_port=logger)
        with pytest.raises(ValueError):
            etl.execute()
        assert logger.error.call_count == 1

    def test_post_execute_logs_on_success(self):
        logger = make_logger()
        etl = ConcreteETL(destination_port=make_destination(), logger_port=logger)
        etl.post_execute(result=None)
        assert logger.info.call_count >= 2

    def test_each_instance_uses_its_own_logger(self):
        logger_a = make_logger()
        logger_b = make_logger()
        etl_a = ConcreteETL(destination_port=make_destination(), logger_port=logger_a)
        etl_b = ConcreteETL(destination_port=make_destination(), logger_port=logger_b)
        etl_a.execute()
        assert logger_a.info.call_count >= 2
        assert logger_b.info.call_count == 0
