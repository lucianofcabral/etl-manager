import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto


class PipelineStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()


class InvalidTransaction(Exception): ...


# type Action[C] = Callable[[C], None]


@dataclass(slots=True, kw_only=True)
class EtlData:
    """Metadatos de un proceso ETL.

    Attributes:
        unique_name: Identificador único del proceso.
        process_name: Nombre del proceso.
        doc: Documentación del proceso.
        dependes_on: Lista de procesos de los que depende.
    """

    unique_name: str
    process_name: str
    doc: str
    dependes_on: list["EtlProcess"] = field(default_factory=list)

    def __post_init__(self):
        if not self.unique_name or not self.process_name or not self.doc:
            raise ValueError("unique_name, process_name, and doc cannot be empty")
        self.unique_name = self.unique_name.strip()
        self.process_name = re.sub(r"\s+", " ", self.process_name).strip()
        self.doc = re.sub(r"\s+", " ", self.doc).strip()

    def __hash__(self):
        return hash(self.unique_name)


@dataclass(slots=True)
class EtlProcess:
    """Instancia de ejecución de un proceso ETL.

    Attributes:
        etl_data: Metadatos del proceso.
        status: Estado actual del proceso.
        start_time: Timestamp cuando inicia (IDLE → RUNNING).
        end_time: Timestamp cuando termina (RUNNING → SUCCESS/FAILED).
        error: Mensaje de error si falla.
    """

    etl_data: EtlData
    _status: PipelineStatus = PipelineStatus.IDLE
    error: str | None = field(default=None, init=False)
    start_time: datetime | None = field(default=None, init=False)
    end_time: datetime | None = field(default=None, init=False)
    audit: list[str] = field(default_factory=list[str])
    _LOOK_UP_TABLE: dict[
        tuple[PipelineStatus, bool],
        PipelineStatus,
    ] = field(
        default_factory=lambda: {
            (PipelineStatus.IDLE, True): PipelineStatus.RUNNING,
            (PipelineStatus.IDLE, False): PipelineStatus.FAILED,
            (PipelineStatus.RUNNING, True): PipelineStatus.SUCCESS,
            (PipelineStatus.RUNNING, False): PipelineStatus.FAILED,
            (PipelineStatus.FAILED, True): PipelineStatus.IDLE,
            (PipelineStatus.FAILED, False): PipelineStatus.FAILED,
            (PipelineStatus.SUCCESS, True): PipelineStatus.IDLE,
            (PipelineStatus.SUCCESS, False): PipelineStatus.FAILED,
        },
        init=False,
        repr=False,
        compare=False,
    )

    @property
    def status(self) -> PipelineStatus:
        """Obtiene el estado actual."""
        return self._status

    @status.setter
    def status(self, new_status: PipelineStatus, flag: bool) -> None:
        """Establece el estado según estado anterior y una flag.

        Args:
            new_status: Nuevo estado del proceso.
        """

        self._status = new_status

    @property
    def duration(self) -> float | None:
        """Duración del proceso en segundos, o None si no está terminado.

        Returns:
            Segundos entre start_time y end_time, o None.
        """
        if (
            self.start_time
            and self.end_time
            and self.status in (PipelineStatus.SUCCESS, PipelineStatus.FAILED)
        ):
            return (self.end_time - self.start_time).total_seconds()
        return None

    def handle_status(self, flag: bool) -> None:
        try:
            new_status = self._LOOK_UP_TABLE[(self.status, flag)]

            match new_status:
                case PipelineStatus.IDLE:
                    self.start_time = None
                    self.start_time = None
                case PipelineStatus.RUNNING:
                    self.start_time = datetime.now()
                    self.end_time = None
                case PipelineStatus.FAILED | PipelineStatus.SUCCESS:
                    self.end_time = datetime.now()

            self.status = new_status
            self.audit.append(
                f"{datetime.now(timezone.utc)} - {PipelineStatus.IDLE} to {PipelineStatus.RUNNING}"
            )

        except KeyError as e:
            raise InvalidTransaction(
                "DEBUG: Transacción no válida, Revisar la look_up_table en domain.models.entities: "
                f"\n\tfrom status '{self.status}' with flag '{flag}'"
                f"\n\tEtlProcess '{self}'"
                f"\n\tEtlData '{self}'"
            ) from e

    def __hash__(self):
        return self.etl_data.__hash__()

    def __post_init__(self):
        self.audit.append(f"Objeto Creado | {self}")
