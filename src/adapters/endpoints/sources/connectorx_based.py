import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import jinja2
import polars as pl
from dotenv import load_dotenv

from src.domain.ports.endpoints_port import ISourcePortDB


class DbSourceConfiguration(dict[str, Any], Enum):
    POSTGRESQL = {
        "name": "postgresql",
        "prefix": "POSTGRESQL_",
        "default_credentials": {
            "user": "postgres",
            "password": "",
            "host": "localhost",
            "port": 5432,
            "database": "test",
        },
        "uri_template": "postgresql://{user}:{password}@{host}:{port}/{database}",
    }
    MYSQL = {
        "name": "mysql",
        "prefix": "MYSQL_",
        "default_credentials": {
            "user": "root",
            "password": "",
            "host": "localhost",
            "port": 3306,
            "database": "test",
        },
        "uri_template": "mysql://{user}:{password}@{host}:{port}/{database}",
    }
    SQLITE = {
        "name": "sqlite",
        "prefix": "SQLITE_",
        "default_credentials": {
            "database": "db.sqlite",
        },
        "uri_template": "sqlite:///{database}",
    }


@dataclass(slots=True)
class DbSource(ISourcePortDB):
    envfile: Path
    conf: DbSourceConfiguration = field(init=True)
    _default_credentials: dict[str, Any] = field(
        init=False, default_factory=dict[str, Any]
    )
    prefix_env: str = field(init=False, default_factory=str)
    name: str = field(init=False, default_factory=str)
    user: str = field(init=False, default_factory=str)
    password: str = field(init=False, default_factory=str)
    host: str = field(init=False, default_factory=str)
    port: int = field(init=False, default_factory=int)
    database: str = field(init=False, default_factory=str)

    def __post_init__(self):
        self.prefix_env = self.conf.value["prefix"]
        self.name = self.conf.value["name"]
        self._default_credentials = self.conf.value["default_credentials"]

        load_dotenv(self.envfile)
        self.user = os.getenv(
            f"{self.prefix_env}_USER", self._default_credentials.get("user", "")
        )
        self.password = os.getenv(
            f"{self.prefix_env}_PASSWORD", self._default_credentials.get("password", "")
        )
        self.host = os.getenv(
            f"{self.prefix_env}_HOST", self._default_credentials.get("host", "")
        )
        self.port = int(
            os.getenv(
                f"{self.prefix_env}_PORT",
                self._default_credentials.get("port", 0),
            )
        )

        self.database = os.getenv(
            f"{self.prefix_env}_DATABASE", self._default_credentials.get("database", "")
        )

        self.__uri = jinja2.Template(self.conf.value["uri_template"]).render(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    def __repr__(self) -> str:
        return f"DbSource(name={self.name}, database={self.database})"

    def __build_uri(self) -> str:
        return self.__uri

    def read_lazy(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> pl.LazyFrame:
        """Lee datos de la base de datos con el query dado y devuelve un LazyFrame."""
        return pl.read_database_uri(
            query=query,
            uri=self.__build_uri(),
            execute_options={"parameters": parameters or {}},
            engine="connectorx",
        ).lazy()

    def test_connection(self) -> bool:
        """Prueba la conexión a la base de datos."""
        try:
            pl.read_database_uri(
                query="SELECT 1", uri=self.__build_uri(), engine="connectorx"
            )
            return True
        except Exception as e:
            print(f"Error de conexión: {e}")
            return False


class DbSourceFactory:
    @staticmethod
    def create(envfile: Path, conf: DbSourceConfiguration) -> DbSource:
        return DbSource(envfile=envfile, conf=conf)
