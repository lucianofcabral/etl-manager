# ⚡ ETL Manager

ETL pipeline manager con arquitectura hexagonal (Ports & Adapters).

**Stack:** Python 3.13+ · Polars LazyFrames · NiceGUI · ClickHouse

---

## Fuentes soportadas

| Tipo | Adaptador | Estado |
|------|-----------|--------|
| MySQL | `connectorx` | ✅ Implementado |
| PostgreSQL | `connectorx` | ✅ Implementado |
| SQLite | `connectorx` | ✅ Implementado |
| CSV | Polars `scan_csv` (lazy) | ✅ Implementado |
| Excel (.xlsx) | `fastexcel` | ✅ Implementado |
| Parquet | Polars `scan_parquet` (lazy) | ✅ Implementado |

## Destinos soportados

| Tipo | Adaptador | Estado |
|------|-----------|--------|
| ClickHouse | `clickhouse-connect` | ✅ Implementado |
| CSV | — | 🚧 Pendiente |
| Parquet | — | 🚧 Pendiente |

---

## Visión funcional

### Pantalla principal — Lista de procesos ETL

La UI muestra todos los procesos ETL registrados en el sistema. Por cada proceso se muestra:

- **Nombre** del proceso (`description`)
- **Documentación** (`doc`) en un tooltip o sección expandible
- **Dependencias**: qué otros procesos deben ejecutarse antes
- **Fuentes disponibles**: íconos o chips por cada `SourceType` declarado
- **Estado actual**: IDLE / RUNNING / SUCCESS / FAILED con color indicativo
- **Vista de datos** (DataFrame): previsualización del estado actual de la tabla destino, para evaluar si necesita actualización

El usuario puede seleccionar uno o varios procesos y lanzar la ejecución.

### Fuentes múltiples por proceso

Un proceso ETL puede declarar más de una fuente posible (ej: MySQL y CSV para el mismo dato). La UI ofrece todas las opciones disponibles al momento de ejecutar. Si el usuario elige una fuente no implementada en ese proceso, se muestra el mensaje **"NO IMPLEMENTADO"** sin lanzar error. Esto permite registrar la intención de implementación futura de manera explícita.

```python
# Ejemplo: un proceso con múltiples fuentes
class MiETL(BaseETLUseCase):
    sources = [SourceType.MYSQL, SourceType.CSV]  # ambas declaradas
    # execute() decide cuál usar según la fuente elegida
```

### Ejecución y feedback en tiempo real

Al correr uno o más procesos:

1. Se resuelven las dependencias automáticamente (topological sort)
2. Los procesos bloqueados esperan a que sus dependencias terminen
3. Se muestra un panel de log en tiempo real con los mensajes del `ILoggerPort`
4. Al finalizar (SUCCESS o FAILED), se emite una notificación visible

### Configuración de conexiones

Las credenciales se cargan desde un archivo `.env` con prefijo por tipo de fuente:

```env
# MySQL
MYSQL_USER=root
MYSQL_PASSWORD=secret
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=mi_db

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
...
```

---

## Arquitectura

```
src/
├── domain/
│   ├── models/        # EtlData, EtlProcess, StateMachine, enums
│   ├── ports/         # ILoggerPort, ISourcePort, IDestinationPort
│   ├── services/      # DependencyResolver (topological sort)
│   └── exceptions.py  # ETLError, ETLSourceError, ETLDestinationError, …
├── adapters/
│   ├── endpoints/
│   │   ├── sources/   # DbSource (MySQL/PG/SQLite), CsvSource, ExcelSource, ParquetSource
│   │   └── destinations/  # ClickHouseDestination
│   └── logging/       # FileLogger, ConsoleLogger, CompositeLogger
├── application/
│   ├── decorators.py  # logged_execution (wrapping automático)
│   └── use_cases/     # BaseETLUseCase + casos concretos
└── ui/                # NiceGUI (en desarrollo)
```

### Jerarquía de excepciones

```
ETLError
├── ETLSourceError        # falla al leer una fuente
├── ETLDestinationError   # falla al escribir en destino
├── ETLConfigurationError # credenciales / conexión inválidas
└── ETLTransformError     # error durante transformación de datos
```

Todos los adapters envuelven sus excepciones nativas en excepciones de dominio, de modo que la capa de aplicación nunca depende de errores de librerías externas.

### Loggers disponibles

| Clase | Descripción |
|-------|-------------|
| `FileLogger` | Escribe en archivo con formato `asctime - level - message` |
| `ConsoleLogger` | Escribe en stdout/stderr con colores ANSI opcionales |
| `CompositeLogger` | Delega a múltiples loggers simultáneamente |

```python
from src.adapters.logging import CompositeLogger, ConsoleLogger, FileLogger

logger = CompositeLogger(
    ConsoleLogger(name="etl"),
    FileLogger(filepath="logs/etl.log"),
)
```

---

## Ejecutar

```bash
# Instalar dependencias
pip install -e ".[dev]"
# o con uv:
uv sync

# Correr la app
python src/main.py

# Correr tests
uv run pytest tests/unit
```

## Registrar una nueva fuente

Se debe tener un archivo `.env` con el prefijo correcto antes de cada variable.  
Ver sección **Configuración de conexiones** más arriba.

