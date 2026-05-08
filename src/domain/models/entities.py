import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import ClassVar

from src.domain.models.state_machine import InvalidTransition, StateMachine


class PipelineStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()


_etl_data_registry: dict[str, type["EtlData"]] = {}


@dataclass(kw_only=True)
class EtlData:
    """Metadatos de un proceso ETL.

    Las subclases concretas deben definir `_domain_name: ClassVar[str]` como
    identificador único del proceso, y `schema: ClassVar[dict | None]` como
    contrato del DataFrame de salida.

    Attributes:
        **unique_name**: Identificador único del proceso.
        **process_name**: Nombre del proceso.
        **doc**: Documentación del proceso.
        **depends_on**: Clases EtlData de las que depende este proceso (grafo estático).
    """

    # ClassVar fields are excluded from dataclass __init__ and __slots__
    schema: ClassVar[dict | None] = None
    depends_on: ClassVar[list[type["EtlData"]]] = []

    unique_name: str
    process_name: str
    doc: str

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        domain_name: str | None = cls.__dict__.get("_domain_name")
        if domain_name is not None:
            if domain_name in _etl_data_registry:
                raise ValueError(
                    f"Duplicate EtlData _domain_name: '{domain_name}' "
                    f"already registered by {_etl_data_registry[domain_name].__name__}"
                )
            _etl_data_registry[domain_name] = cls

    def __post_init__(self):
        if not self.unique_name or not self.process_name or not self.doc:
            raise ValueError("unique_name, process_name, and doc cannot be empty")
        self.unique_name = self.unique_name.strip()
        self.process_name = re.sub(r"\s+", " ", self.process_name).strip()
        self.doc = re.sub(r"\s+", " ", self.doc).strip()

    def __hash__(self):
        return hash(self.unique_name)


# --- Máquina de estados compartida para todos los EtlProcess ---


@dataclass(slots=True)
class EtlProcess:
    """Instancia de ejecución de un proceso ETL.

    Attributes:
        etl_data: Metadatos del proceso.
        dep_processes: Procesos de los que depende esta instancia (tracking en runtime).
        status: Estado actual del proceso.
        start_time: Timestamp cuando inicia (IDLE → RUNNING).
        end_time: Timestamp cuando termina (RUNNING → SUCCESS/FAILED).
        error: Mensaje de error si falla.
    """

    etl_data: EtlData
    dep_processes: list["EtlProcess"] = field(default_factory=list)
    _status: PipelineStatus = PipelineStatus.IDLE
    error: str | None = field(default=None, init=False)
    start_time: datetime | None = field(default=None, init=False)
    end_time: datetime | None = field(default=None, init=False)
    audit: list[str] = field(default_factory=list)

    @property
    def status(self) -> PipelineStatus:
        return self._status

    @property
    def duration(self) -> float | None:
        """Duración en segundos entre inicio y fin, o None si aún no terminó."""
        if (
            self.start_time
            and self.end_time
            and self.status in (PipelineStatus.SUCCESS, PipelineStatus.FAILED)
        ):
            return (self.end_time - self.start_time).total_seconds()
        return None

    def change_status(self, flag: bool) -> None:
        """Avanza el estado del pipeline según el resultado de la operación anterior."""
        prev = self.status
        try:
            self._status = _sm.handle(self, self.status, flag)
        except InvalidTransition as e:
            raise InvalidTransition(
                f"Transición no válida desde '{prev}' con flag={flag} "
                f"en '{self.etl_data.unique_name}'"
            ) from e
        self.audit.append(f"{datetime.now(timezone.utc)} - {prev} → {self._status}")

    def __hash__(self):
        return self.etl_data.__hash__()

    def __post_init__(self):
        self.audit.append(f"Objeto Creado | {self}")


_sm: StateMachine = StateMachine()


@_sm.transition(PipelineStatus.IDLE, True, PipelineStatus.RUNNING)
def _to_running(ctx: "EtlProcess") -> None:
    ctx.start_time = datetime.now()
    ctx.end_time = None


@_sm.transition(PipelineStatus.IDLE, False, PipelineStatus.FAILED)
@_sm.transition(PipelineStatus.RUNNING, True, PipelineStatus.SUCCESS)
@_sm.transition(PipelineStatus.RUNNING, False, PipelineStatus.FAILED)
@_sm.transition(PipelineStatus.SUCCESS, False, PipelineStatus.FAILED)
@_sm.transition(PipelineStatus.FAILED, False, PipelineStatus.FAILED)
def _to_terminal(ctx: "EtlProcess") -> None:
    ctx.end_time = datetime.now()


@_sm.transition(PipelineStatus.FAILED, True, PipelineStatus.IDLE)
@_sm.transition(PipelineStatus.SUCCESS, True, PipelineStatus.IDLE)
def _to_idle(ctx: "EtlProcess") -> None:
    ctx.start_time = None
    ctx.end_time = None
