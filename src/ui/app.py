"""Punto de entrada de la aplicación NiceGUI."""

from nicegui import ui

from src.ui.pages import dashboard


def start_app() -> None:
    dashboard.setup()
    ui.run(
        title="ETL Manager",
        dark=True,
        port=8080,
        reload=False,
        show=False,
        favicon="🔄",
    )
