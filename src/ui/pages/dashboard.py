"""Dashboard principal: lista de procesos ETL con ejecución desde la UI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nicegui import run, ui

# Importar use cases concretos para poblar el registry
import src.application.use_cases.coberturas  # noqa: F401
import src.application.use_cases.coberturas_rv  # noqa: F401
import src.application.use_cases.organizadores  # noqa: F401
import src.application.use_cases.primas_automotores  # noqa: F401
from src.application.use_cases.base_etl import BaseETLUseCase
from src.domain.models.enums import SourceType

if TYPE_CHECKING:
    pass

# Paleta de colores por tipo de fuente
_SOURCE_COLOR: dict[SourceType, str] = {
    SourceType.MYSQL: "blue-7",
    SourceType.POSTGRESQL: "teal-7",
    SourceType.SQLITE: "grey-6",
    SourceType.CSV: "green-7",
    SourceType.EXCEL: "orange-7",
    SourceType.PARQUET: "purple-7",
}

# Tipos de fuente que se conectan via .env (sin picker de archivo)
_DB_SOURCE_TYPES = {SourceType.MYSQL, SourceType.POSTGRESQL, SourceType.SQLITE}


def setup() -> None:
    @ui.page("/")
    def index() -> None:
        _render_header()
        _render_dashboard()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


def _render_header() -> None:
    with ui.header().classes("items-center justify-between bg-grey-10 q-px-xl shadow-3"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("sync_alt", size="md").classes("text-primary")
            ui.label("ETL Manager").classes("text-h5 text-weight-bold")
        ui.label("v0.1.0").classes("text-caption text-grey-6")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def _render_dashboard() -> None:
    use_cases = BaseETLUseCase.find(user_facing_only=True)

    with ui.column().classes("w-full max-w-6xl mx-auto q-pa-xl gap-4"):
        with ui.row().classes("items-center gap-2 q-mb-xs"):
            ui.label("Procesos ETL").classes("text-h6 text-weight-medium")
            ui.badge(str(len(use_cases)), color="primary")

        if not use_cases:
            with ui.card().classes("w-full q-pa-lg text-center bg-grey-9"):
                ui.label("No hay procesos registrados.").classes("text-grey-5")
            return

        with ui.grid(columns=2).classes("w-full gap-4"):
            for uc_class in use_cases:
                _process_card(uc_class)


# ---------------------------------------------------------------------------
# Process card
# ---------------------------------------------------------------------------


def _process_card(uc_class: type[BaseETLUseCase]) -> None:
    etl_data = uc_class.as_etl_data()
    impl_sources = uc_class.implemented_sources
    deps = uc_class.depends_on
    is_runnable = bool(impl_sources)

    with ui.card().classes("w-full bg-grey-9 rounded-borders"):
        with ui.card_section():
            # Título + badge de estado
            with ui.row().classes("items-start justify-between w-full no-wrap"):
                ui.label(etl_data.process_name).classes(
                    "text-subtitle1 text-weight-bold text-white"
                )
                if is_runnable:
                    ui.badge("Listo", color="positive").props("outline")
                else:
                    ui.badge("Sin impl.", color="grey").props("outline")

            # Descripción
            ui.label(etl_data.doc).classes("text-caption text-grey-5 q-mt-xs")

        ui.separator().classes("bg-grey-8")

        with ui.card_section().classes("q-py-sm"):
            # Chips de fuentes
            if impl_sources:
                with ui.row().classes("gap-1 q-mb-sm"):
                    for src in impl_sources:
                        color = _SOURCE_COLOR.get(src, "grey-7")
                        ui.chip(
                            src.name.replace("_", " ").title(),
                            icon="storage",
                            color=color,
                            text_color="white",
                        ).props("dense outline")

            # Dependencias
            if deps:
                dep_names = " → ".join(d.as_etl_data().process_name for d in deps)
                with ui.row().classes("items-center gap-1"):
                    ui.icon("account_tree", size="xs").classes("text-grey-6")
                    ui.label(f"Requiere: {dep_names}").classes(
                        "text-caption text-grey-6"
                    )

        ui.separator().classes("bg-grey-8")

        with ui.card_actions().props("align=right"):
            btn = ui.button(
                "Ejecutar",
                icon="play_arrow",
                on_click=lambda uc=uc_class: _open_run_dialog(uc),
            ).props("flat dense")
            if is_runnable:
                btn.classes("text-positive")
            else:
                btn.props(add="disable").classes("text-grey-7")


# ---------------------------------------------------------------------------
# Run dialog
# ---------------------------------------------------------------------------


def _open_run_dialog(uc_class: type[BaseETLUseCase]) -> None:
    etl_data = uc_class.as_etl_data()
    impl_sources = uc_class.implemented_sources
    source_names = [s.name for s in impl_sources]
    selected: dict[str, str] = {"source": source_names[0] if source_names else ""}

    with ui.dialog() as dialog, ui.card().classes("bg-grey-9 q-pa-md").style(
        "min-width: 440px"
    ):
        # Cabecera del diálogo
        with ui.row().classes("items-center gap-2 q-mb-sm"):
            ui.icon("play_circle", size="md").classes("text-positive")
            ui.label(etl_data.process_name).classes(
                "text-subtitle1 text-weight-bold text-white"
            )
        ui.separator().classes("bg-grey-8 q-mb-md")

        # Selección de fuente
        ui.label("Fuente de datos").classes("text-caption text-grey-5 q-mb-xs")
        if len(source_names) > 1:
            ui.select(
                options=source_names,
                value=selected["source"],
                on_change=lambda e: selected.update({"source": e.value}),
            ).classes("w-full q-mb-md").props("dark outlined dense")
        else:
            with ui.row().classes("items-center gap-2 q-mb-md"):
                src_type = impl_sources[0] if impl_sources else None
                color = _SOURCE_COLOR.get(src_type, "grey-7") if src_type else "grey-7"
                ui.chip(
                    selected["source"].replace("_", " ").title(),
                    icon="storage",
                    color=color,
                    text_color="white",
                ).props("dense outline")

        # Dependencias en el diálogo
        if uc_class.depends_on:
            ui.separator().classes("bg-grey-8 q-mb-sm")
            ui.label("Se ejecutará junto con:").classes(
                "text-caption text-grey-5 q-mb-xs"
            )
            for dep in uc_class.depends_on:
                with ui.row().classes("items-center gap-1"):
                    ui.icon("chevron_right", size="xs").classes("text-grey-6")
                    ui.label(dep.as_etl_data().process_name).classes(
                        "text-caption text-grey-4"
                    )
            ui.element("div").classes("q-mb-md")

        # Contenedor de estado / resultado
        status_box = ui.column().classes("w-full q-mb-md gap-1")

        # Botones
        with ui.row().classes("justify-end gap-2"):
            cancel_btn = ui.button("Cancelar", on_click=dialog.close).props(
                "flat dense"
            ).classes("text-grey-5")

            async def _on_run() -> None:
                cancel_btn.props(add="disable")
                run_btn.props("loading disable")
                await _execute(uc_class, selected, status_box, run_btn, cancel_btn)

            run_btn = ui.button("Ejecutar", icon="play_arrow", on_click=_on_run).props(
                "dense"
            ).classes("text-positive")

    dialog.open()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


async def _execute(
    uc_class: type[BaseETLUseCase],
    selected: dict[str, str],
    status_box: ui.column,
    run_btn: ui.button,
    cancel_btn: ui.button,
) -> None:
    status_box.clear()
    with status_box:
        with ui.row().classes("items-center gap-2"):
            ui.spinner("dots", size="sm").classes("text-primary")
            ui.label("Ejecutando pipeline…").classes("text-caption text-grey-5")

    try:
        result: dict = await run.io_bound(
            _run_pipeline, uc_class, selected["source"]
        )
        status_box.clear()
        with status_box:
            with ui.row().classes("items-center gap-2"):
                ui.icon("check_circle", size="sm").classes("text-positive")
                ui.label("Completado").classes("text-caption text-positive text-weight-medium")
            for cls_name, cls_result in result.items():
                with ui.row().classes("items-center gap-1 q-ml-md"):
                    ui.icon("chevron_right", size="xs").classes("text-grey-6")
                    label = cls_name
                    if isinstance(cls_result, dict):
                        rows = cls_result.get("rows", "?")
                        table = cls_result.get("table", "")
                        label = f"{cls_name}: {rows} filas → {table}"
                    ui.label(label).classes("text-caption text-grey-4")
    except Exception as exc:
        status_box.clear()
        with status_box:
            with ui.row().classes("items-center gap-2"):
                ui.icon("error", size="sm").classes("text-negative")
                ui.label("Error").classes("text-caption text-negative text-weight-medium")
            ui.label(str(exc)).classes("text-caption text-grey-5 q-ml-md")
    finally:
        run_btn.props(remove="loading disable")
        cancel_btn.props(remove="disable")


def _run_pipeline(uc_class: type[BaseETLUseCase], source_name: str) -> dict:
    """Ejecuta el pipeline completo usando puertos configurados desde .env."""
    from src.adapters.endpoints.destinations.clickhouse import ClickhouseDestination
    from src.adapters.endpoints.sources.connectorx_based import (
        DbSource,
        DbSourceConfiguration,
    )
    from src.adapters.logging.console_logger import ConsoleLogger
    from src.application.orchestrators.pipeline_orchestrator import PipelineOrchestrator

    source_type = SourceType[source_name]
    env_path = Path(".env")

    _DB_CONF: dict[SourceType, DbSourceConfiguration] = {
        SourceType.MYSQL: DbSourceConfiguration.MYSQL,
        SourceType.POSTGRESQL: DbSourceConfiguration.POSTGRESQL,
        SourceType.SQLITE: DbSourceConfiguration.SQLITE,
    }

    if source_type not in _DB_CONF:
        raise NotImplementedError(
            f"La fuente '{source_name}' requiere selección de archivo. "
            "Funcionalidad disponible próximamente."
        )

    source_port = DbSource(envfile=env_path, conf=_DB_CONF[source_type])
    dest_port = ClickhouseDestination(envfile=env_path)
    logger = ConsoleLogger()

    orch = PipelineOrchestrator(
        source_port=source_port,
        destination_port=dest_port,
        logger_port=logger,
    )
    return orch.run(uc_class)
