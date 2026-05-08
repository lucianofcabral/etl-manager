"""PipelineOrchestrator: ejecuta un use case y todas sus dependencias en orden."""

from collections import deque
from typing import Any

from src.domain.ports.endpoints_port import IDestinationPort, ISourcePort
from src.domain.ports.logger_port import ILoggerPort


class PipelineOrchestrator:
    """Resuelve y ejecuta el grafo de dependencias de un use case.

    Dado un use case objetivo, el orquestador:
    1. Recorre transitivamente todos los ``depends_on`` para construir el grafo
       completo de dependencias.
    2. Ordena topológicamente el grafo (las dependencias van primero).
    3. Instancia y ejecuta cada use case en orden, usando el mismo
       ``source_port`` y ``destination_port`` para toda la cadena.

    Args:
        source_port: Adapter de fuente configurado (e.g. ``DbSource`` desde ``.env``).
        destination_port: Adapter de destino configurado.
        logger_port: Logger compartido inyectado a todos los use cases.

    Example::

        mysql   = DbSource(envfile=Path(".env"), conf=DbSourceConfiguration.MYSQL)
        ch      = ClickhouseDestination(envfile=Path(".env"))
        logger  = ConsoleLogger()

        orchestrator = PipelineOrchestrator(mysql, ch, logger)

        # Ejecuta: CoberturasUseCase → OrganizadoresUseCase → PrimasAutomotoresUseCase
        results = orchestrator.run(PrimasAutomotoresUseCase)

        # Recarga desde CSV (el usuario elige el archivo):
        csv = CsvSource(file_path=Path("/datos/primas_2024.csv"))
        results = orchestrator.run(PrimasAutomotoresUseCase, source_port=csv)
    """

    def __init__(
        self,
        source_port: ISourcePort,
        destination_port: IDestinationPort,
        logger_port: ILoggerPort,
    ) -> None:
        self._source_port = source_port
        self._destination_port = destination_port
        self._logger_port = logger_port

    def run(
        self,
        target: "type[Any]",
        *,
        source_port: ISourcePort | None = None,
    ) -> dict[str, Any]:
        """Ejecuta el target y todas sus dependencias en orden topológico.

        Args:
            target: Clase del use case a ejecutar (con todas sus deps).
            source_port: Override de fuente para esta ejecución. Útil para
                fuentes basadas en archivos (CSV, Parquet, Excel) donde el
                path lo elige el usuario en runtime. Si no se pasa, usa el
                ``source_port`` configurado en el constructor.

        Returns:
            Dict ``{ClassName: resultado_de_execute}`` para cada use case
            ejecutado, en orden topológico.
        """
        effective_source = source_port if source_port is not None else self._source_port
        ordered = self._resolve_chain(target)
        results: dict[str, Any] = {}
        for cls in ordered:
            uc = cls(
                destination_port=self._destination_port,
                logger_port=self._logger_port,
            )
            result = uc.execute(source_port=effective_source)
            results[cls.__name__] = result
        return results

    @staticmethod
    def _resolve_chain(target: "type[Any]") -> "list[type[Any]]":
        """Devuelve los use cases en orden topológico (deps primero).

        Raises:
            ValueError: Si se detecta una dependencia circular.
        """
        # BFS para recolectar todos los nodos
        all_deps: dict[type, list[type]] = {}
        queue: deque[type] = deque([target])
        while queue:
            cls = queue.popleft()
            if cls in all_deps:
                continue
            deps = list(getattr(cls, "depends_on", ()))
            all_deps[cls] = deps
            queue.extend(deps)

        # Kahn's algorithm
        in_degree: dict[type, int] = {cls: 0 for cls in all_deps}
        graph: dict[type, list[type]] = {cls: [] for cls in all_deps}
        for cls, deps in all_deps.items():
            for dep in deps:
                graph[dep].append(cls)
                in_degree[cls] += 1

        ready: deque[type] = deque(cls for cls, deg in in_degree.items() if deg == 0)
        ordered: list[type] = []
        while ready:
            cls = ready.popleft()
            ordered.append(cls)
            for dependent in graph[cls]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    ready.append(dependent)

        if len(ordered) != len(all_deps):
            raise ValueError(
                f"Dependencia circular detectada en el grafo de '{target.__name__}'"
            )

        return ordered
