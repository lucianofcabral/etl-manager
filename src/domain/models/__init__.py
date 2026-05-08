"""Domain models."""

from src.domain.models.entities import EtlData, EtlProcess, PipelineStatus
from src.domain.models.enums import DestinationType, SourceType
from src.domain.models.etl_definitions import (
    CoberturasRVarias_EtlData,
    DAF_EtlData,
    PrimasAut_EtlData,
)
from src.domain.models.state_machine import InvalidTransition, StateMachine

__all__ = [
    "EtlData",
    "EtlProcess",
    "PipelineStatus",
    "DestinationType",
    "SourceType",
    "InvalidTransition",
    "StateMachine",
    "CoberturasRVarias_EtlData",
    "DAF_EtlData",
    "PrimasAut_EtlData",
]
