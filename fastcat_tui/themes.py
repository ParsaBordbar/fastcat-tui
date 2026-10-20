"""Finding themes. A theme is a folder holding fastfetch/config.jsonc (plus its logo files).

Sources, in menu order:
  mine     your themes (made with image -> logo, or saved copies)     <data>/themes/<Name>/fastfetch
  gallery  themes installed from the community gallery               <data>/gallery/<code>/fastfetch
  bundled  themes shipped with fastcat-tui                            fastcat_tui/themes/<Category>/<Name>/fastfetch
  fastcat  the FastCat pack and any folder you add                    <dir>/<Category>-Themes/<Name>/fastfetch
"""
import os
import re
from dataclasses import dataclass
from pathlib import Path

from . import colors, ffconfig, jsonc, logo, settings

BUNDLED_DIR = Path(__file__).parent / "themes"
_CONFIG_DIR_PREFIX = re.compile(r"^(~|\$HOME|\$\{HOME\})/\.config/fastfetch/")


@dataclass
class Theme:
    name: str
    category: str
    path: Path          # the fastfetch/ folder
    source: str         # mine | bundled | fastcat

    @property
    def config_path(self) -> Path:
        return self.path / "config.jsonc"

    def config(self) -> dict:
        return jsonc.load(self.config_path)

    def logo_file(self) -> Path | None:
        return logo_file(self.config(), self.path)

    def logo_text(self) -> str | None:
        f = self.logo_file()
        return f.read_text(encoding="utf-8", errors="replace") if f else None


def safe_name(raw: str) -> str:
    """A theme name usable as a single folder name."""
    return re.sub(r"[^\w.-]+", "-", raw.strip()).strip("-.") or "My-Theme"


def mine_dir(name: str) -> Path:
    return settings.user_themes_dir() / name / "fastfetch"


def save_logo_theme(name: str, text: str, palette: dict) -> tuple[Theme, dict]:
    """Write a new theme under Mine from an ASCII logo: recommended lines, key colours from the logo,
    info centred beside it. Returns the theme and its config."""
    dest = mine_dir(name)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "ascii.txt").write_text(text, encoding="utf-8")
    cfg = ffconfig.recommended(logo_palette=palette)
    n = len(ffconfig.info_indices(cfg))
    ffconfig.set_key_colors(cfg, colors.spread(ffconfig.visible_logo_palette(cfg, logo.used_colors(text)), n))
    ffconfig.center(cfg, logo.size(text)[1])
    jsonc.save(dest / "config.jsonc", cfg)
    return Theme(name, "Mine", dest, "mine"), cfg


def resolve_source(source: str, base: Path) -> Path:
    """A logo path from a config, as seen from the folder the config lives in.

    Paths into ~/.config/fastfetch/ point at the theme's own folder (that is where they end up once
    applied); relative paths are relative to the config.
    """
    s = _CONFIG_DIR_PREFIX.sub("", source)
    if s != source or not os.path.isabs(os.path.expanduser(s)):
        return base / s
    return Path(os.path.expanduser(s))


def logo_file(cfg: dict, base: Path) -> Path | None:
    """The text logo file a config draws, or None for image / built-in / no logo."""
    lg = cfg.get("logo")
    if isinstance(lg, str):
        lg = {"source": lg}
    if not isinstance(lg, dict) or not isinstance(lg.get("source"), str):
        return None
    if lg.get("type") not in (None, "auto", "file", "file-raw"):
        return None
    f = resolve_source(lg["source"], base)
    return f if f.is_file() and f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif", ".webp") else None


def logo_height(cfg: dict, base: Path) -> int:
    f = logo_file(cfg, base)
    if f:
        return logo.size(f.read_text(encoding="utf-8", errors="replace"))[1]
    lg = cfg.get("logo")
    return int(lg.get("height", 0)) if isinstance(lg, dict) and str(lg.get("height", "")).isdigit() else 0


def _scan(base: Path, source: str) -> list[Theme]:
    found = []
    if not base.is_dir():
        return found
    for cfg in sorted(base.glob("*/fastfetch/config.jsonc")):
        found.append(Theme(cfg.parent.parent.name, {"mine": "Mine", "gallery": "Gallery"}.get(source, base.name), cfg.parent, source))
    for cfg in sorted(base.glob("*/*/fastfetch/config.jsonc")):
        category = cfg.parent.parent.parent.name.removesuffix("-Themes")
        found.append(Theme(cfg.parent.parent.name, category, cfg.parent, source))
    return found


def fastcat_dirs(cfg: dict | None = None) -> list[Path]:
    cfg = settings.load() if cfg is None else cfg
    dirs = [settings.fastcat_clone_dir()] + [Path(d).expanduser() for d in cfg.get("theme_dirs", [])]
    seen, out = set(), []
    for d in dirs:
        if d.resolve() not in seen:
            seen.add(d.resolve())
            out.append(d)
    return out


def all_themes(cfg: dict | None = None) -> list[Theme]:
    themes = _scan(settings.user_themes_dir(), "mine") + _scan(settings.gallery_dir(), "gallery") + _scan(BUNDLED_DIR, "bundled")
    for d in fastcat_dirs(cfg):
        themes += _scan(d, "fastcat")
    return themes


def find(name: str, cfg: dict | None = None) -> Theme | None:
    """Theme by name (case-insensitive); 'Category/Name' picks between duplicates."""
    want = name.lower()
    for t in all_themes(cfg):
        if want in (t.name.lower(), f"{t.category}/{t.name}".lower()):
            return t
    return None
