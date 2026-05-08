# Guía del desarrollador — ETL Manager

## Cómo agregar un nuevo proceso ETL

### 1. Definir el `EtlData` (dominio)

Crea una clase en `src/domain/models/etl_definitions.py`. Es la fuente de verdad del proceso: su nombre único, descripción y schema de salida.

```python
class PrimasAut_EtlData(EtlData):
    _domain_name = "primas_automotores"          # identificador único — no puede repetirse
    schema = {"cod_poliza": pl.Utf8, ...}        # contrato del DataFrame de salida

    def __init__(self) -> None:
        super().__init__(
            unique_name=self._domain_name,
            process_name="Primas Automotores",
            doc="Ingesta de primas emitidas de autos a nivel suplemento/componente.",
        )
```

> Si el proceso es simple y todavía no tiene schema definido, podés omitir `EtlData` y usar el modo compat (ver sección 2b).

---

### 2. Crear el Use Case

Crea un archivo en `src/application/use_cases/`. El use case implementa la lógica ETL.

#### 2a. Con `EtlData` (recomendado)

```python
# src/application/use_cases/primas_automotores.py

class PrimasAutomotoresUseCase(BaseETLUseCase):
    etl_data_class = PrimasAut_EtlData          # fuente de verdad del dominio

    sources             = [SourceType.MYSQL, SourceType.CSV]
    implemented_sources = [SourceType.MYSQL]    # CSV pendiente de implementar
    destinations        = [DestinationType.CLICKHOUSE]

    depends_on = (CoberturasUseCase, OrganizadoresUseCase)  # clases, no instancias
    user_facing = True   # True = visible en la UI (default)

    def produce_frame(self, source_port, **kwargs) -> pl.LazyFrame:
        """Transformación pura. No escribe en destino."""
        coberturas = CoberturasUseCase(...).produce_frame(cob_port)
        primas     = source_port.read_lazy(_QUERY_PRIMAS)
        return primas.join(coberturas, on="cod_cobertura", how="left")

    def execute(self, source_port, **kwargs):
        data      = self.produce_frame(source_port)
        row_count = data.select("cod_poliza").collect().height
        self.destination_port.write_lazy(data)
        return {"rows": row_count, "table": self.process.etl_data.unique_name}

    def post_execute(self, result, **kwargs) -> None:
        if result:
            self.logger_port.info(f"{result['rows']} filas escritas en '{result['table']}'")
```

#### 2b. Modo compat (sin `EtlData`, para casos simples o legacy)

```python
class OrganizadoresUseCase(BaseETLUseCase):
    name        = "organizadores"
    description = "ETL dimensión organizadores MySQL → ClickHouse"
    doc         = "Carga la dimensión de organizadores con SCD Type 2."
    depends_on  = ()
    ...
```

---

### 3. Registro automático

**No hay nada que hacer.** Al definir la clase, `BaseETLUseCase.__init_subclass__` la registra automáticamente. Podés consultarla así:

```python
from src.application.use_cases.base_etl import BaseETLUseCase
from src.domain.models.enums import SourceType, DestinationType

# Todos los use cases concretos
BaseETLUseCase.all_registered()

# Con filtros (combinables)
BaseETLUseCase.find(source=SourceType.MYSQL)
BaseETLUseCase.find(destination=DestinationType.CLICKHOUSE)
BaseETLUseCase.find(user_facing_only=True)
BaseETLUseCase.find(implemented_only=True)      # tiene al menos un source implementado
BaseETLUseCase.find(source=SourceType.MYSQL, user_facing_only=True)
```

---

### 4. Atributos de clase de referencia

| Atributo | Tipo | Descripción |
|---|---|---|
| `etl_data_class` | `type[EtlData] \| None` | Fuente de verdad del proceso (recomendado) |
| `name` / `description` / `doc` | `str` | Modo compat si no hay `EtlData` |
| `sources` | `list[SourceType]` | Fuentes que el proceso *intenta* soportar |
| `implemented_sources` | `list[SourceType]` | Subconjunto de `sources` con impl. real lista |
| `destinations` | `list[DestinationType]` | Destinos soportados |
| `depends_on` | `tuple[type[BaseETLUseCase], ...]` | Deps que deben correr antes |
| `user_facing` | `bool` | `True` = visible en UI (default). `False` = paso interno |

---

### 5. `produce_frame` vs `execute`

| Método | Escribe en destino | Puede llamarlo otro use case |
|---|---|---|
| `produce_frame(source_port)` | ❌ | ✅ — retorna `LazyFrame` para composición |
| `execute(source_port)` | ✅ | No (es el punto de entrada completo) |

Usa `produce_frame` para que otros use cases puedan consumir tu transformación como paso intermedio (tabla plana en ClickHouse, evitando JOINs en destino).

---

### 6. Configurar fuentes (Sources)

#### Base de datos (MySQL, PostgreSQL)

Las credenciales se leen automáticamente del `.env`:

```python
from src.adapters.endpoints.sources.connectorx_based import DbSource, DbSourceConfiguration
from pathlib import Path

mysql = DbSource(envfile=Path(".env"), conf=DbSourceConfiguration.MYSQL)
```

Variables `.env` esperadas (prefijo `MYSQL_`):
```
MYSQL__USER=root
MYSQL__PASSWORD=secret
MYSQL__HOST=localhost
MYSQL__PORT=3306
MYSQL__DATABASE=mi_base
```

#### Archivos (CSV, Excel, Parquet)

El path lo elige el usuario en runtime:

```python
from src.adapters.endpoints.sources.file_based import CsvSource, ExcelSource, ParquetSource

csv     = CsvSource(file_path=Path("/datos/primas.csv"), separator=";")
excel   = ExcelSource(file_path=Path("/datos/org.xlsx"))
parquet = ParquetSource(file_path=Path("/datos/snapshot.parquet"))
```

---

### 7. Ejecutar con el Orquestador

El orquestador resuelve automáticamente el grafo de `depends_on` y ejecuta en orden topológico.

```python
from src.application.orchestrators import PipelineOrchestrator

# Construir una vez al arrancar
orch = PipelineOrchestrator(
    source_port=mysql,          # fuente por defecto (DB)
    destination_port=clickhouse,
    logger_port=logger,
)

# Ejecutar (corre deps primero, luego el target)
results = orch.run(PrimasAutomotoresUseCase)
# → {"CoberturasUseCase": {...}, "OrganizadoresUseCase": {...}, "PrimasAutomotoresUseCase": {...}}

# Recarga desde archivo (override de source en runtime)
results = orch.run(PrimasAutomotoresUseCase, source_port=csv)
```

---

### 8. Checklist al agregar un nuevo proceso

- [ ] `EtlData` definido en `etl_definitions.py` con `_domain_name` único y `schema`
- [ ] Use case en `src/application/use_cases/` con `etl_data_class`, `sources`, `destinations`
- [ ] `implemented_sources` ⊆ `sources` (si no, rompe al importar)
- [ ] `depends_on` apunta a clases, no instancias
- [ ] `user_facing = False` si es un paso interno no expuesto en la UI
- [ ] `produce_frame` implementado si otros use cases van a consumirlo
- [ ] Tests en `tests/unit/application/`
