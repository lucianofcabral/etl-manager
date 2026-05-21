"""Utilidad para validar schemas mínimos de Polars en las fronteras ETL."""

import polars as pl

from src.domain.exceptions import ETLTransformError


def validate_minimum_schema(frame: pl.LazyFrame, schema: dict, context: str) -> None:
    """Valida que el frame contenga al menos las columnas del schema con los tipos correctos.

    Args:
        frame: LazyFrame a validar.
        schema: Diccionario {nombre_columna: tipo_polars} que el frame debe cumplir como mínimo.
        context: Nombre del contexto para mensajes de error (e.g. nombre de la clase).

    Raises:
        ETLTransformError: Si alguna columna requerida no existe o tiene tipo incorrecto.
    """
    actual = frame.collect_schema()
    errors: list[str] = []
    for col, expected_type in schema.items():
        if col not in actual:
            errors.append(f"columna requerida '{col}' no encontrada")
        elif actual[col] != expected_type:
            errors.append(
                f"columna '{col}': tipo esperado {expected_type}, encontrado {actual[col]}"
            )
    if errors:
        raise ETLTransformError(
            f"[{context}] Schema mínimo no cumplido:\n"
            + "\n".join(f"  · {e}" for e in errors)
        )
