from collections import defaultdict, deque

from src.domain.models.entities import EtlData


def resolve_etl_dependencies(
    dependencies: dict[EtlData, list[EtlData]],
) -> list[EtlData]:
    """Devuelve una lista ordenada de ETLs según sus dependencias.

    Args:
        dependencies: Diccionario donde la clave es un str y el valor es una lista de str de los que depende."""
    incoming_count: dict[EtlData, int] = defaultdict(int)
    graph: dict[EtlData, list[EtlData]] = defaultdict(list)

    for node, deps in dependencies.items():
        incoming_count.setdefault(node, 0)
        for dep in deps:
            graph[dep].append(node)
            incoming_count[node] += 1
            incoming_count.setdefault(dep, 0)

    queue = deque(node for node, count in incoming_count.items() if count == 0)
    ordered: list[EtlData] = []

    while queue:
        node = queue.popleft()
        ordered.append(node)
        for neighbor in graph[node]:
            incoming_count[neighbor] -= 1
            if incoming_count[neighbor] == 0:
                queue.append(neighbor)

    if len(ordered) != len(incoming_count):
        raise ValueError("Circular dependency detected")

    return ordered
