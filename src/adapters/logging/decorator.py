"""Re-exporta logged_execution desde la capa de aplicación para compatibilidad."""

from src.application.decorators import logged_execution

__all__ = ["logged_execution"]
