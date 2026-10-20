"""Edits on a loaded fastfetch config (a dict): logo and key colours, icons, modules and layout."""
import copy

from . import colors, icons

# Lines in a fresh config, top to bottom.
RECOMMENDED_MODULES = ["os", "host", "kernel", "uptime", "packages", "shell", "terminal",
                       "de", "wm", "cpu", "gpu", "memory", "disk", "datetime"]
# Modules offered when adding lines.
CATALOG = ["title", "os", "host", "kernel", "uptime", "packages", "shell", "display", "de", "wm",
           "wmtheme", "theme", "icons", "font", "cursor", "terminal", "terminalfont", "cpu", "gpu",
           "memory", "swap", "disk", "localip", "battery", "poweradapter", "locale", "datetime",
           "media", "colors", "break"]



def modules(cfg: dict) -> list:
    mods = cfg.get("modules")
    if not isinstance(mods, list):
        mods = cfg["modules"] = []
    return mods


def mtype(m) -> str:
    return m if isinstance(m, str) else str(m.get("type", ""))


def as_dict(cfg: dict, i: int) -> dict:
    """modules[i] as a dict, converting the short "os" string form in place."""
    mods = modules(cfg)
    if isinstance(mods[i], str):
        mods[i] = {"type": mods[i]}
    return mods[i]


def info_indices(cfg: dict) -> list[int]:
    """Modules that print a line (everything except spacers)."""
    return [i for i, m in enumerate(modules(cfg)) if mtype(m) not in ("break", "separator", "colors")]


def key_icon(m) -> str:
    key = m.get("key", "") if isinstance(m, dict) else ""
    key = key.strip()
    return key if len(key) == 1 and icons.is_icon(key) else ""


def set_icon(cfg: dict, i: int, glyph: str) -> None:
    as_dict(cfg, i)["key"] = glyph + " "


def fix_icons(cfg: dict) -> int:
    """Swap single-icon keys for the recommended one-cell icons. Text keys are left alone."""
    changed = 0
    for i, m in enumerate(modules(cfg)):
        current = key_icon(m)
        best = icons.recommended(mtype(m))
        if current and best and current != best:
            set_icon(cfg, i, best)
            changed += 1
    return changed


def logo_section(cfg: dict) -> dict | None:
    lg = cfg.get("logo")
    if lg is None or lg == "none":
        return None
    if not isinstance(lg, dict):
        lg = cfg["logo"] = {"source": lg}
    return lg


def logo_colors(cfg: dict) -> dict:
    lg = logo_section(cfg)
    return dict(lg.get("color") or {}) if lg else {}


def set_logo_color(cfg: dict, slot: str, spec: str) -> None:
    lg = logo_section(cfg)
    if lg is not None:
        lg.setdefault("color", {})[slot] = spec


def key_colors(cfg: dict) -> list[str]:
    c = display(cfg).get("color")
    fallback = c.get("keys", "default") if isinstance(c, dict) else "default"
    mods = modules(cfg)
    return [mods[i].get("keyColor", fallback) if isinstance(mods[i], dict) else fallback
            for i in info_indices(cfg)]


def set_key_colors(cfg: dict, specs: list[str]) -> None:
    """Key colour per info line, top to bottom."""
    for i, spec in zip(info_indices(cfg), specs):
        as_dict(cfg, i)["keyColor"] = spec


def visible_logo_palette(cfg: dict, used: list[str]) -> list[str]:
    """Logo colours (in slot order) bright enough to read as key colours on a dark terminal."""
    lc = logo_colors(cfg)
    pal = [lc.get(s, "default") for s in used]
    bright = [c for c in pal if colors.brightness(c) > 0.18]
    return bright or pal


def display(cfg: dict) -> dict:
    d = cfg.get("display")
    if not isinstance(d, dict):
        d = cfg["display"] = {}
    return d


def text_color(cfg: dict) -> str:
    c = display(cfg).get("color")
    return c.get("output", "default") if isinstance(c, dict) else "default"


def set_text_color(cfg: dict, spec: str) -> None:
    c = display(cfg).get("color")
    if not isinstance(c, dict):
        c = display(cfg)["color"] = {} if c is None else {"keys": c}
    c["output"] = spec


def key_width(cfg: dict) -> int:
    k = display(cfg).get("key")
    return int(k.get("width", 0)) if isinstance(k, dict) else 0


def set_key_width(cfg: dict, width: int) -> None:
    k = display(cfg).get("key")
    if not isinstance(k, dict):
        k = display(cfg)["key"] = {}
    k["width"] = width


def separator(cfg: dict) -> str:
    return display(cfg).get("separator", ": ")


def set_separator(cfg: dict, sep: str) -> None:
    display(cfg)["separator"] = sep


def center(cfg: dict, logo_height: int) -> str:
    """Line the info block up with the middle of the logo. Returns what was done.

    Taller logo: blank lines above the info. Shorter logo: top padding on the logo.
    """
    mods = modules(cfg)
    while mods and mtype(mods[0]) == "break":
        mods.pop(0)
    lg = logo_section(cfg)
    if lg is not None and isinstance(lg.get("padding"), dict):
        lg["padding"].pop("top", None)
    n = len(mods)               # every module prints a row, blank lines and separators included
    if logo_height > n:
        pad = (logo_height - n) // 2
        mods[:0] = [{"type": "break"} for _ in range(pad)]
        return f"{pad} blank line(s) above the info"
    if lg is not None and logo_height < n:
        pad = (n - logo_height) // 2
        lg.setdefault("padding", {})["top"] = pad
        return f"logo moved down {pad} line(s)"
    return "already centred"


def new_module(module_type: str, key_color: str | None = None) -> dict:
    if module_type == "colors":
        return {"type": "colors", "symbol": "circle"}
    if module_type in ("break", "separator", "title"):
        return {"type": module_type}
    m = {"type": module_type}
    icon = icons.recommended(module_type)
    if icon:
        m["key"] = icon + " "
    if key_color:
        m["keyColor"] = key_color
    return m


def recommended(logo_source: str = "~/.config/fastfetch/ascii.txt", logo_palette: dict | None = None) -> dict:
    """A clean config: file logo, one-cell icons, aligned keys."""
    return {
        "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
        "logo": {"source": logo_source, "color": copy.deepcopy(logo_palette or {"1": "default"}),
                 "padding": {"right": 4}},
        "display": {"separator": " ", "key": {"width": 3}},
        "modules": [new_module(t) for t in RECOMMENDED_MODULES],
    }
