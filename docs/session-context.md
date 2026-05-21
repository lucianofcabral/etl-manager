# Contexto para la próxima sesión — ETL Manager

> **Última actualización:** 2026-05-21. Arquitectura composite implementada y funcionando. UI NiceGUI (dark) en marcha. 199 tests verdes.

## Objetivo de la app

ETL pipeline manager con UI en **NiceGUI**. Permite al usuario ver, configurar y ejecutar procesos ETL desde una interfaz gráfica. Stack: Python 3.13 · Polars (LazyFrames) · ClickHouse como destino principal · MySQL como fuente principal.

Arquitectura **hexagonal (Ports & Adapters)**:
- `domain/` — entidades, puertos (interfaces), servicios puros
- `adapters/` — implementaciones concretas (DbSource, CsvSource, ClickhouseDestination, loggers)
- `application/` — use cases, orquestador
- `ui/` — NiceGUI front-end. Dashboard con lista de procesos, tema oscuro forzado, ejecución desde la UI.

Comandos clave:
```bash
uv run pytest tests/unit    # 199 tests, todos verdes
uv run python -m src.main  # arrancar la app (puerto 8080)
```

---

## Arquitectura de use cases — Patrón Composite

### Las tres capas

Cada proceso ETL se implementa con **tres clases**:

```
SourceETLUseCase         ETLDestinationUseCase
(ABC puro, no registrado)(ABC puro, no registrado)
         │                        │
         └──────────┬─────────────┘
              CompositeETLUseCase
           (registrado en el registry)
```

### 1. `SourceETLUseCase` — frontera source/ETL

```python
class MiSource(SourceETLUseCase):
    source_type = SourceType.MYSQL
    input_schema = None  # o dict[str, PolarsType] para validación mínima

    def extract(self, source_port, **kwargs) -> pl.LazyFrame:
        return source_port.read_lazy("SELECT ...")

    def transform(self, frame, **kwargs) -> pl.LazyFrame:  # opcional, identidad por defecto
        return frame.with_columns(...)
```

Flujo interno de `produce_frame()`: `extract() → validar input_schema → transform()`

- `input_schema = None` → no valida (se confía en el SQL)
- `transform()` es la transformación **exclusiva** de esa fuente
- **No se registra** en el registry — es interna del composite

### 2. `ETLDestinationUseCase` — frontera ETL/destino

```python
class MiDest(ETLDestinationUseCase):
    destination_type = DestinationType.CLICKHOUSE
    dest_input_schema = None  # o dict[str, PolarsType] para validación mínima

    def write(self, frame, **kwargs) -> dict:
        self.destination_port.write_lazy(frame)
        return {"rows": frame.collect().height, "table": "mi_tabla"}

    def transform_frame(self, frame, **kwargs) -> pl.LazyFrame:  # opcional
        return frame
```

Flujo interno de `execute()`: `validar dest_input_schema → transform_frame() → write()`

- **No se registra** — es interna del composite

### 3. `CompositeETLUseCase` — orquestador registrado

```python
class MiETLUseCase(CompositeETLUseCase):
    etl_data_class = MiEtlData       # fuente de verdad del dominio
    source_etl_class = MiSource      # auto-popula sources y implemented_sources
    dest_etl_class = MiDest          # auto-popula destinations
    depends_on = (OtroUseCase,)      # clases, no instancias

    # execute() default: produce_frame → validar EtlData.schema → dest.execute()
    # Sobreescribir solo para flujos especiales (loops, fan-in, skip-if-empty)

    def post_execute(self, result, **kwargs) -> None:
        self.logger_port.info(f"{result}")
```

**`sources`, `implemented_sources`, `destinations` se auto-derivan** de `source_etl_class.source_type` y `dest_etl_class.destination_type` en `__init_subclass__`. No declarar manualmente.

### Flujo de validación — tres puntos de contrato (todos mínimos)

```
Source DB/File
    │
    ▼
SourceETLUseCase.extract()
    │
    ├─ [input_schema] → validación mínima (opcional, None = skip)
    │
SourceETLUseCase.transform()
    │
    ▼
CompositeETLUseCase._validate_etl_contract()
    │
    ├─ [EtlData.schema] → validación mínima (None = skip)
    │
    ▼
ETLDestinationUseCase
    │
    ├─ [dest_input_schema] → validación mínima (opcional, None = skip)
    │
ETLDestinationUseCase.transform_frame()
    │
ETLDestinationUseCase.write()
    │
    ▼
ClickHouse / destino
```

**Todos los contratos son MÍNIMOS**: columnas extra en el frame son permitidas.

---

## Registry y consultas desde UI

```python
# Todos los use cases visibles al usuario
BaseETLUseCase.find(user_facing_only=True)

# Solo con fuente implementada
BaseETLUseCase.find(implemented_only=True)

# Por tipo de fuente o destino
BaseETLUseCase.find(source=SourceType.MYSQL)
BaseETLUseCase.find(destination=DestinationType.CLICKHOUSE)

# Introspección de un use case concreto
MiETLUseCase.available_sources()       # → [SourceType.MYSQL]
MiETLUseCase.unimplemented_sources()   # → []
MiETLUseCase.is_source_available(SourceType.EXCEL)  # → False
```

Solo los `CompositeETLUseCase` concretos aparecen en el registry. `SourceETLUseCase` y `ETLDestinationUseCase` son invisibles para el sistema.

---

## Orquestador

```python
orch = PipelineOrchestrator(
    source_port=mysql,
    destination_port=clickhouse,
    logger_port=logger,
)
results = orch.run(PrimasAutomotoresUseCase)
# Override de fuente para un proceso:
results = orch.run(PrimasAutomotoresUseCase, source_port=ExcelSource(Path("...")))
```

- `run()` resuelve `depends_on` recursivamente → orden topológico (Kahn) → ejecuta en orden.
- `depends_on` vive en el **composite** (o en `EtlData.depends_on`), no en source/dest.
- Detecta ciclos y lanza `ValueError`.

---

## Use cases implementados

| Composite | Source | Dest | `execute` especial |
|---|---|---|---|
| `CoberturasAutomotoresMySqlToClickhouseUseCase` | `CoberturasAut_MySQLSource` | `CoberturasAut_ClickhouseDest` | No (default) |
| `CoberturasRVUseCase` | `CoberturasRV_MySQLSource` | `CoberturasRV_ClickhouseDest` | Sí — skip si frame vacío |
| `OrganizadoresUseCase` | `Organizadores_MySQLSource` | `Organizadores_ClickhouseDest` | No (default) |
| `PrimasAutomotoresUseCase` | `PrimasAut_MySQLSource` | `PrimasAut_ClickhouseDest` | Sí — loop mes a mes |

`PrimasAutomotoresUseCase.depends_on = (OrganizadoresUseCase, CoberturasAutomotoresMySqlToClickhouseUseCase)`

---

## Estructura de archivos clave

```
src/
├── application/
│   ├── decorators.py                    # logged_execution (wrap automático de execute/post_execute)
│   ├── orchestrators/
│   │   └── pipeline_orchestrator.py     # PipelineOrchestrator
│   └── use_cases/
│       ├── _schema_validation.py        # validate_minimum_schema() — usado por los 3 puntos
│       ├── base_etl.py                  # BaseETLUseCase + CompositeETLUseCase + _use_case_registry
│       ├── base_source_etl.py           # SourceETLUseCase (ABC, no registrado)
│       ├── base_dest_etl.py             # ETLDestinationUseCase (ABC, no registrado)
│       ├── coberturas.py                # ✅ CoberturasAutomotoresMySqlToClickhouseUseCase
│       ├── coberturas_rv.py             # ✅ CoberturasRVUseCase
│       ├── organizadores.py             # ✅ OrganizadoresUseCase
│       └── primas_automotores.py        # ✅ PrimasAutomotoresUseCase
├── ui/
│   ├── app.py                           # start_app() — ui.run(dark=True, port=8080)
│   └── pages/
│       └── dashboard.py                 # Cards por proceso, run dialog, ejecución async
├── domain/
│   ├── exceptions.py                    # ETLError, ETLConfigurationError, ETLTransformError
│   ├── models/
│   │   ├── entities.py                  # EtlData, EtlProcess, PipelineStatus
│   │   ├── etl_definitions.py           # Clases concretas de EtlData (con .schema)
│   │   ├── enums.py                     # SourceType, DestinationType
│   │   ├── schemas.py                   # Schemas Polars: coberturas_rv_etl_schema, etc.
│   │   └── state_machine.py             # Máquina de estados genérica
│   ├── ports/
│   │   ├── endpoints_port.py            # ISourcePort, IDestinationPort
│   │   ├── logger_port.py               # ILoggerPort
│   │   └── query_port.py                # IQueryPort (ABC con DataFrame)
│   └── services/
│       └── dependency_resolver.py       # resolve_etl_dependencies, dependencies_satisfied
├── adapters/
│   ├── endpoints/
│   │   ├── sources/
│   │   │   ├── connectorx_based.py      # DbSource (MySQL/PG/SQLite)
│   │   │   └── file_based.py            # CsvSource, ExcelSource, ParquetSource
│   │   └── destinations/
│   │       └── clickhouse.py            # ClickhouseDestination
│   └── logging/
│       ├── console_logger.py
│       ├── file_logger.py
│       ├── composite_logger.py
│       └── decorator.py                 # re-exporta logged_execution (compat)
infrastructure/                          # vacío — reservado
tests/
└── unit/
    ├── application/
    │   ├── test_coberturas.py
    │   ├── test_organizadores.py
    │   ├── test_primas_automotores.py
    │   └── test_registry_and_orchestrator.py
    ├── domain/
    │   ├── test_available_sources.py
    │   ├── test_dependency_resolver.py
    │   ├── test_etl_process.py
    │   ├── test_exceptions.py
    │   ├── test_logging.py
    │   └── test_state_machine.py
    └── adapters/
        └── test_loggers.py
```

---

## Reglas de diseño

- **Un composite por combinación source+destino** con transformación exclusiva en el source.
- Para la misma lógica de destino con dos fuentes distintas: dos `SourceETLUseCase` + dos composites, **reutilizando el mismo `ETLDestinationUseCase`**.
- `depends_on` usa **clases**, no instancias. Vive en el composite.
- `user_facing = False` para pasos internos no expuestos en la UI.
- `produce_frame()` en el composite delega a `_source_etl.produce_frame()` — útil para que otros use cases lo consuman como input (tablas desnormalizadas sin JOINs en ClickHouse).
- `_composite_base = True` en `CompositeETLUseCase` la excluye del registry (se chequea con `__dict__` para que subclases concretas sí se registren).

## Convenciones de código

- Siempre `uv run pytest` — no `python -m pytest`
- Tests con `MagicMock` para todos los puertos (sin I/O real)
- DataFrames de test deben usar dtypes Polars explícitos (e.g. `pl.Series(..., dtype=pl.UInt32)`) para que la validación de schema intermedio no falle
- Adapters envuelven excepciones nativas en `ETLError`
- `execute()` devuelve `dict` con al menos `{"rows": int, "table": str}` (o estructura similar)
- `post_execute()` hace logging del resultado; no lanza si `result` es `None`

## Próximos pasos naturales

1. **UI — file picker para fuentes CSV/Excel/Parquet** — el run dialog ya detecta el tipo; falta integrar `ui.upload` o `ui.input` para el path
2. **Activar contratos de schema** donde corresponda — actualmente todos en `None`, listos para llenarse
3. **Múltiples instancias MySQL** — cambio mínimo en el orquestador cuando se necesite
