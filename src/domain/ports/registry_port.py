# src/domain/ports/registry_port.py
from abc import ABC, abstractmethod
from src.domain.models.entities import EtlData

class IRegistryPort(ABC):
    """Puerto para cargar el registro de ETLs desde una fuente (JSON, BD, etc)."""
    
    @abstractmethod
    def load_all(self) -> list[EtlData]:
        """Carga todos los ETLs registrados."""
        pass
    
    @abstractmethod
    def load_by_name(self, unique_name: str) -> EtlData:
        """Carga un ETL específico por nombre único."""
        pass