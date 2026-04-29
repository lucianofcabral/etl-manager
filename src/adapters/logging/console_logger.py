import sys

from src.domain.ports.logger_port import ILoggerPort

_RESET = "\033[0m"
_LEVEL_COLORS = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[35m",  # magenta
}


class ConsoleLogger(ILoggerPort):
    """Logger que escribe en stdout con colores ANSI."""

    def __init__(self, name: str = "ConsoleLogger", use_colors: bool = True) -> None:
        self._name = name
        self._use_colors = use_colors and sys.stdout.isatty()

    @property
    def name(self) -> str:
        return self._name

    def _format(self, level: str, message: str) -> str:
        if self._use_colors:
            color = _LEVEL_COLORS.get(level, "")
            return f"{color}[{level}]{_RESET} {message}"
        return f"[{level}] {message}"

    def debug(self, message: str, **kwargs) -> None:
        print(self._format("DEBUG", message), file=sys.stdout)

    def info(self, message: str, **kwargs) -> None:
        print(self._format("INFO", message), file=sys.stdout)

    def warning(self, message: str, **kwargs) -> None:
        print(self._format("WARNING", message), file=sys.stdout)

    def error(self, message: str, **kwargs) -> None:
        print(self._format("ERROR", message), file=sys.stderr)

    def critical(self, message: str, **kwargs) -> None:
        print(self._format("CRITICAL", message), file=sys.stderr)
