from pathlib import Path

import polars as pl

from src.domain.ports.endpoints_port import ISourcePortFile


class CsvSource(ISourcePortFile):
    def __init__(
        self,
        file_path: Path,
        separator: str = ",",
        decimal_comma: bool = True,
        **kwargs,
    ) -> None:
        self._file_path = file_path
        self.separator = separator
        self.decimal_comma = decimal_comma
        self.kwargs = kwargs

    @property
    def file_path(self) -> Path:
        return self._file_path

    def read_lazy(self) -> pl.LazyFrame:
        return pl.scan_csv(
            self.file_path,
            separator=self.separator,
            decimal_comma=self.decimal_comma,
            **self.kwargs,
        )


class ExcelSource(ISourcePortFile):
    def __init__(self, file_path: Path, **kwargs) -> None:
        self._file_path = file_path
        self.kwargs = kwargs

    @property
    def file_path(self) -> Path:
        return self._file_path

    def read_lazy(self) -> pl.LazyFrame:
        return pl.read_excel(self.file_path, **self.kwargs).lazy()


class ParquetSource(ISourcePortFile):
    def __init__(self, file_path: Path, **kwargs) -> None:
        self._file_path = file_path
        self.kwargs = kwargs

    @property
    def file_path(self) -> Path:
        return self._file_path

    def read_lazy(self) -> pl.LazyFrame:
        return pl.scan_parquet(self.file_path, **self.kwargs)
