"""Tests para ConsoleLogger y CompositeLogger."""

import sys
from io import StringIO
from unittest.mock import MagicMock

import pytest

from src.adapters.logging.composite_logger import CompositeLogger
from src.adapters.logging.console_logger import ConsoleLogger
from src.domain.ports.logger_port import ILoggerPort


def make_mock_logger(name: str = "mock") -> ILoggerPort:
    mock = MagicMock(spec=ILoggerPort)
    mock.name = name
    return mock


# ---------------------------------------------------------------------------
# ConsoleLogger
# ---------------------------------------------------------------------------


class TestConsoleLogger:
    def test_name_property(self):
        logger = ConsoleLogger(name="mi_logger")
        assert logger.name == "mi_logger"

    def test_default_name(self):
        logger = ConsoleLogger()
        assert logger.name == "ConsoleLogger"

    def test_info_writes_to_stdout(self, capsys):
        logger = ConsoleLogger(use_colors=False)
        logger.info("mensaje info")
        captured = capsys.readouterr()
        assert "mensaje info" in captured.out
        assert "[INFO]" in captured.out

    def test_debug_writes_to_stdout(self, capsys):
        logger = ConsoleLogger(use_colors=False)
        logger.debug("mensaje debug")
        captured = capsys.readouterr()
        assert "mensaje debug" in captured.out
        assert "[DEBUG]" in captured.out

    def test_warning_writes_to_stdout(self, capsys):
        logger = ConsoleLogger(use_colors=False)
        logger.warning("aviso")
        captured = capsys.readouterr()
        assert "aviso" in captured.out
        assert "[WARNING]" in captured.out

    def test_error_writes_to_stderr(self, capsys):
        logger = ConsoleLogger(use_colors=False)
        logger.error("error grave")
        captured = capsys.readouterr()
        assert "error grave" in captured.err
        assert "[ERROR]" in captured.err

    def test_critical_writes_to_stderr(self, capsys):
        logger = ConsoleLogger(use_colors=False)
        logger.critical("fallo crítico")
        captured = capsys.readouterr()
        assert "fallo crítico" in captured.err
        assert "[CRITICAL]" in captured.err

    def test_implements_logger_port(self):
        logger = ConsoleLogger()
        assert isinstance(logger, ILoggerPort)


# ---------------------------------------------------------------------------
# CompositeLogger
# ---------------------------------------------------------------------------


class TestCompositeLogger:
    def test_requires_at_least_one_logger(self):
        with pytest.raises(ValueError):
            CompositeLogger()

    def test_name_property(self):
        mock = make_mock_logger()
        composite = CompositeLogger(mock, name="mi_composite")
        assert composite.name == "mi_composite"

    def test_default_name(self):
        mock = make_mock_logger()
        composite = CompositeLogger(mock)
        assert composite.name == "CompositeLogger"

    def test_info_delegates_to_all_loggers(self):
        a, b = make_mock_logger("a"), make_mock_logger("b")
        composite = CompositeLogger(a, b)
        composite.info("hola")
        a.info.assert_called_once_with("hola")
        b.info.assert_called_once_with("hola")

    def test_debug_delegates_to_all_loggers(self):
        a, b = make_mock_logger("a"), make_mock_logger("b")
        composite = CompositeLogger(a, b)
        composite.debug("debug msg")
        a.debug.assert_called_once_with("debug msg")
        b.debug.assert_called_once_with("debug msg")

    def test_warning_delegates_to_all_loggers(self):
        a, b = make_mock_logger("a"), make_mock_logger("b")
        composite = CompositeLogger(a, b)
        composite.warning("warn")
        a.warning.assert_called_once_with("warn")
        b.warning.assert_called_once_with("warn")

    def test_error_delegates_to_all_loggers(self):
        a, b = make_mock_logger("a"), make_mock_logger("b")
        composite = CompositeLogger(a, b)
        composite.error("error")
        a.error.assert_called_once_with("error")
        b.error.assert_called_once_with("error")

    def test_critical_delegates_to_loggers_with_critical(self):
        a = MagicMock(spec=ILoggerPort)
        a.name = "a"
        a.critical = MagicMock()
        composite = CompositeLogger(a, name="c")
        composite.critical("crítico")
        a.critical.assert_called_once_with("crítico")

    def test_critical_falls_back_to_error_when_no_critical(self):
        a = make_mock_logger("a")
        del a.critical  # simula logger sin critical
        composite = CompositeLogger(a, name="c")
        composite.critical("crítico sin método")
        a.error.assert_called_once_with("crítico sin método")

    def test_kwargs_forwarded(self):
        a = make_mock_logger("a")
        composite = CompositeLogger(a)
        composite.info("msg", extra="dato")
        a.info.assert_called_once_with("msg", extra="dato")

    def test_implements_logger_port(self):
        mock = make_mock_logger()
        composite = CompositeLogger(mock)
        assert isinstance(composite, ILoggerPort)


# ---------------------------------------------------------------------------
# logged_execution — mensaje de error incluye tipo de excepción
# ---------------------------------------------------------------------------


class TestLoggedExecutionErrorMessage:
    def test_error_message_includes_exception_type(self):
        from src.application.decorators import logged_execution

        logger = make_mock_logger()

        @logged_execution(logger)
        def falla():
            raise ValueError("detalle del error")

        with pytest.raises(ValueError):
            falla()

        error_msg = logger.error.call_args[0][0]
        assert "ValueError" in error_msg
        assert "detalle del error" in error_msg
