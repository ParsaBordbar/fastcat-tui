"""Where fastcat-tui keeps its own files, and its saved preferences.

Data (your themes, backups, the downloaded FastCat pack) goes to $XDG_DATA_HOME/fastcat-tui
(~/.local/share/fastcat-tui). Preferences go to $XDG_CONFIG_HOME/fastcat-tui/settings.json.
Set FASTCAT_TUI_HOME to keep everything in one folder instead.
"""
import json
import os
from pathlib import Path


def _xdg(var: str, fallback: str) -> Path:
    return Path(os.environ.get(var) or os.path.expanduser(fallback))


def data_dir() -> Path:
    home = os.environ.get("FASTCAT_TUI_HOME")
    return Path(home).expanduser() if home else _xdg("XDG_DATA_HOME", "~/.local/share") / "fastcat-tui"


def settings_path() -> Path:
    home = os.environ.get("FASTCAT_TUI_HOME")
    base = Path(home).expanduser() if home else _xdg("XDG_CONFIG_HOME", "~/.config") / "fastcat-tui"
    return base / "settings.json"


def user_themes_dir() -> Path:
    return data_dir() / "themes"


def backups_dir() -> Path:
    return data_dir() / "backups"


def gallery_dir() -> Path:
    return data_dir() / "gallery"


def fastcat_clone_dir() -> Path:
    return data_dir() / "FastCat"


def load() -> dict:
    try:
        return json.loads(settings_path().read_text())
    except Exception:
        return {}


def save(cfg: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2))
