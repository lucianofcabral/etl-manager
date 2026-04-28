from enum import auto, Enum


class SourceType(Enum):
    MYSQL = auto()
    POSTGRESQL = auto()
    SQLITE = auto()
    CSV = auto()
    EXCEL = auto()
    PARQUET = auto()


class DestinationType(Enum):
    CLICKHOUSE = auto()
    CSV = auto()
    PARQUET = auto()
