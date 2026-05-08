# Contexto para la próxima sesión — ETL Manager

## Objetivo de la app

ETL pipeline manager con UI en **NiceGUI**. Permite al usuario ver, configurar y ejecutar procesos ETL desde una interfaz gráfica. Stack: Python 3.13 · Polars (LazyFrames) · ClickHouse como destino principal · MySQL como fuente principal.

Arquitectura **hexagonal (Ports & Adapters)**:
- `domain/` — entidades, puertos (interfaces), servicios puros
- `adapters/` — implementaciones concretas (DbSource, CsvSource, ClickhouseDestination, loggers)
- `application/` — use cases, orquestador
- `ui/` — NiceGUI (en desarrollo, aún vacío en la práctica)

Comandos clave:
```bash
uv run pytest tests/unit    # 167 tests, todos verdes
uv run python src/main.py   # arrancar la app
```

---

## Estado actual del proyecto

### Implementado y funcionando

| Componente | Archivo | Descripción |
|---|---|---|
| `BaseETLUseCase` | `application/use_cases/base_etl.py` | Base con registro automático, `produce_frame`, `user_facing` |
| `PipelineOrchestrator` | `application/orchestrators/pipeline_orchestrator.py` | Resuelve deps topológicamente, ejecuta en orden |
| `CoberturasAutomotoresUseCase` | `application/use_cases/coberturas.py` | Implementado con `produce_frame` |
| `CoberturasRVUseCase` | `application/use_cases/coberturas_rv.py` | Implementado con skip-if-empty |
| `PrimasAutomotoresUseCase` | `application/use_cases/primas_automotores.py` | **Stub — `execute` lanza `NotImplementedError`** |
| `OrganizadoresUseCase` | `application/use_cases/organizadores.py` | **Stub — `execute` lanza `NotImplementedError`** |
| `EtlData` + registry | `domain/models/entities.py` | Auto-registro por `_domain_name` |
| `EtlDefinitions` | `domain/models/etl_definitions.py` | `CoberturasAut`, `CoberturasRV`, `DAF`, `PrimasAut` |
| `DbSource` | `adapters/endpoints/sources/connectorx_based.py` | Lee `.env` automáticamente |
| File sources | `adapters/endpoints/sources/file_based.py` | CSV, Excel, Parquet |
| Loggers | `adapters/logging/` | Console, File, Composite |
| State machine | `domain/models/state_machine.py` | IDLE→RUNNING→SUCCESS/FAILED |

### Pendiente / próximos pasos naturales

1. **Implementar `OrganizadoresUseCase.execute()`** — query + produce_frame + write
2. **Implementar `PrimasAutomotoresUseCase.execute()`** — fan-in de coberturas + organizadores usando `produce_frame`, tabla plana en ClickHouse
3. **UI NiceGUI** — lista de procesos, estado, ejecutar con selección de fuente
4. **`ClickhouseDestination`** — revisar si el adapter está completo (ver `adapters/endpoints/destinations/clickhouse.py`)

---

## Reglas de diseño que se acordaron

### Use cases
- **Un use case por transformación**, no por base de datos. La DB es configuración del adapter.
- `depends_on` usa **clases**, no instancias.
- `user_facing = False` para pasos internos que no se exponen en la UI.
- `implemented_sources` debe ser subconjunto de `sources` — si no, rompe al importar (`ETLConfigurationError`).
- `produce_frame()` es la transformación pura (no escribe). `execute()` llama `produce_frame` + escribe.
- Use cases que sirven de input a otros implementan `produce_frame`; el llamador lo consume en memoria para armar tablas planas (evitar JOINs en ClickHouse).

### Fuentes
- **DB (MySQL)**: credenciales desde `.env`, construido una vez al arrancar.
- **Archivos (CSV, Parquet, Excel)**: el usuario elige el path en runtime → se pasa como `source_port` override al orquestador.
- Por ahora **una sola instancia MySQL** y **una sola ClickHouse**. Escalar a múltiples DB es una tarea futura (cambio mínimo en el orquestador).

### Orquestador
```python
orch = PipelineOrchestrator(
    source_port=mysql,          # default para toda la cadena
    destination_port=clickhouse,
    logger_port=logger,
)
results = orch.run(PrimasAutomotoresUseCase)
# Override para archivo:
results = orch.run(PrimasAutomotoresUseCase, source_port=CsvSource(Path("...")))
```
- `run()` resuelve `depends_on` recursivamente → orden topológico (Kahn) → ejecuta en orden.
- Todos los use cases de la cadena usan el mismo `source_port` y `destination_port`.
- Detecta ciclos y lanza `ValueError`.

### Registro de use cases
```python
# Auto-registrado al definir la clase. Consultar con:
BaseETLUseCase.all_registered()
BaseETLUseCase.find(source=SourceType.MYSQL, user_facing_only=True)
```

---

## Estructura de archivos clave

```
src/
├── application/
│   ├── decorators.py               # logged_execution (wrap automático de execute/post_execute)
│   ├── orchestrators/
│   │   └── pipeline_orchestrator.py
│   └── use_cases/
│       ├── base_etl.py             # BaseETLUseCase + _use_case_registry
│       ├── coberturas.py           # ✅ implementado
│       ├── coberturas_rv.py        # ✅ implementado
│       ├── organizadores.py        # ⚠️ stub
│       └── primas_automotores.py   # ⚠️ stub
├── domain/
│   ├── models/
│   │   ├── entities.py             # EtlData, EtlProcess, PipelineStatus
│   │   ├── etl_definitions.py      # Clases concretas de EtlData
│   │   ├── enums.py                # SourceType, DestinationType
│   │   ├── schemas.py              # Schemas de Polars por proceso
│   │   └── state_machine.py        # Máquina de estados genérica
│   ├── ports/
│   │   ├── endpoints_port.py       # ISourcePort, IDestinationPort, ISourcePortDB, ISourcePortFile
│   │   └── logger_port.py          # ILoggerPort
│   └── services/
│       └── dependency_resolver.py  # resolve_etl_dependencies, dependencies_satisfied
├── adapters/
│   ├── endpoints/
│   │   ├── sources/
│   │   │   ├── connectorx_based.py # DbSource (MySQL/PG/SQLite) + DbSourceConfiguration
│   │   │   └── file_based.py       # CsvSource, ExcelSource, ParquetSource
│   │   └── destinations/
│   │       └── clickhouse.py       # ClickhouseDestination
│   └── logging/
│       ├── console_logger.py
│       ├── file_logger.py
│       └── composite_logger.py
docs/
└── developer-guide.md              # instrucciones para agregar nuevos procesos ETL
tests/
└── unit/
    ├── application/
    │   ├── test_coberturas.py
    │   └── test_registry_and_orchestrator.py
    └── domain/
        ├── test_available_sources.py
        ├── test_dependency_resolver.py
        ├── test_etl_process.py
        └── ...
```

---

## Convenciones de código

- Siempre `uv run pytest` — no `python -m pytest`
- Tests con `MagicMock` para todos los puertos (sin I/O real)
- Adapters envuelven sus excepciones nativas en `ETLError` (nunca exponemos errores de libs externas)
- `execute()` devuelve `dict` con al menos `{"rows": int, "table": str}`
- `post_execute()` hace logging del resultado; no lanza si `result` es `None`
