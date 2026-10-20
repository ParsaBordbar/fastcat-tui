"""The live fastfetch config: run it, apply themes, back it up and restore it."""
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from . import jsonc, settings, themes


def config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")) / "fastfetch"


def config_path() -> Path:
    return config_dir() / "config.jsonc"


def available() -> bool:
    return shutil.which("fastfetch") is not None


def backup() -> Path | None:
    """Copy the live config folder into the backups folder. None when there is nothing to back up."""
    src = config_dir()
    if not src.exists():
        return None
    stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    dest = settings.backups_dir() / stamp
    n = 1
    while dest.exists():
        n += 1
        dest = settings.backups_dir() / f"{stamp}-{n}"
    # Follow symlinks: a dotfiles-managed config.jsonc is often a link, and save_live() writes
    # through it, so a backup holding only the link would not keep the old contents.
    shutil.copytree(src, dest, symlinks=False, ignore_dangling_symlinks=True)
    return dest


def backups() -> list[Path]:
    d = settings.backups_dir()
    return sorted((p for p in d.iterdir() if p.is_dir()), reverse=True) if d.is_dir() else []


def _replace_live(src: Path) -> None:
    dest = config_dir()
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    elif dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, symlinks=True)


def apply(theme: themes.Theme) -> Path | None:
    """Back up the live config, then install the theme. Returns the backup path."""
    saved = backup()
    _replace_live(theme.path)
    return saved


def restore(path: Path) -> Path | None:
    """Back up the live config, then put a backup back. Returns the backup of what was replaced."""
    saved = backup()
    _replace_live(path)
    return saved


def save_live(cfg: dict) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    jsonc.save(config_path(), cfg)


def load_live() -> dict | None:
    try:
        return jsonc.load(config_path())
    except (OSError, ValueError):
        return None


def standalone(cfg: dict, base: Path) -> dict:
    """Copy of cfg whose logo path works from anywhere (for previews)."""
    out = jsonc.loads(jsonc.dumps(cfg))
    lg = out.get("logo")
    if isinstance(lg, str):
        lg = out["logo"] = {"source": lg}
    if isinstance(lg, dict) and isinstance(lg.get("source"), str) and lg.get("type") not in ("builtin", "small", "data", "data-raw"):
        candidate = themes.resolve_source(lg["source"], base)
        if candidate.exists():
            lg["source"] = str(candidate)
    return out


def run(cfg: dict | None = None, base: Path | None = None) -> int:
    """Run fastfetch, optionally with an unsaved config (written to a temp file)."""
    if cfg is None:
        return subprocess.call(["fastfetch"])
    with tempfile.NamedTemporaryFile("w", suffix=".jsonc", delete=False, encoding="utf-8") as f:
        f.write(jsonc.dumps(standalone(cfg, base or config_dir())))
        tmp = f.name
    try:
        return subprocess.call(["fastfetch", "-c", tmp])
    finally:
        os.unlink(tmp)


def preview(theme: themes.Theme) -> int:
    return run(theme.config(), theme.path)
