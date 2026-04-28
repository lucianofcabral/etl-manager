from pathlib import Path


class ConfigFolders:
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_FOLDER = PROJECT_ROOT / "data"


def ensure_folders():
    """Asegura que las carpetas necesarias existan."""
    ConfigFolders.DATA_FOLDER.mkdir(exist_ok=True)
