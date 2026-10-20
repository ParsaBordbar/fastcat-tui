"""Helpers shared by the TUI screens: messages, running fastfetch and mock previews."""
from pathlib import Path

from .. import colors, fastfetch, ffconfig, logo, themes
from ..colors import RESET
from ..console import BOLD, DIM, RED, color, pad, visible_len
from ..menu import clear, screen, select, wait_key

_SAMPLE = {"os": "your OS", "host": "your machine", "kernel": "kernel", "uptime": "2 hours", "packages": "packages",
           "shell": "zsh", "terminal": "terminal", "de": "desktop", "wm": "window manager", "cpu": "cpu",
           "gpu": "graphics", "memory": "4 GiB / 16 GiB", "disk": "120 GiB / 500 GiB", "datetime": "today"}


def say(*lines: str) -> None:
    screen(list(lines))
    wait_key()


def run_screen(fn, title: str | None = None) -> None:
    clear()
    if title:
        print(color(title, DIM) + "\n")
    if not fastfetch.available():
        print(color("fastfetch is not installed.", RED) + " Install it: https://github.com/fastfetch-cli/fastfetch#installation")
    else:
        try:
            fn()
        except (OSError, ValueError) as e:
            print(color(f"error: {e}", RED))
    wait_key()


def overwrite_ok(name: str) -> bool:
    """True when no theme called name exists under Mine, or the user agrees to overwrite it."""
    return not themes.mine_dir(name).exists() or select(f"'{name}' exists", [("Overwrite it", ""), ("Cancel", "")]) == 0


def home_relative(path) -> str:
    return str(path).replace(str(Path.home()), "~")


def mock(cfg: dict, base: Path) -> list[str]:
    """Rough picture of what fastfetch will print: logo, then each line's key and value."""
    logo_text = themes.logo_text(cfg, base)
    lg = ffconfig.logo_section(cfg) or {}
    padding = lg.get("padding") if isinstance(lg.get("padding"), dict) else {}
    left = logo.render(logo_text, ffconfig.logo_colors(cfg)) if logo_text else []
    if not logo_text and lg.get("source"):
        left = [color(f"[image logo: {Path(str(lg['source'])).name}]", DIM)]
    left = [""] * int(padding.get("top", 0)) + left
    width = max((visible_len(l) for l in left), default=0)
    gap = int(padding.get("right", 4)) if left else 0
    kw, sep, text = ffconfig.key_width(cfg), ffconfig.separator(cfg), ffconfig.text_color(cfg)
    right = []
    for m in ffconfig.modules(cfg):
        t = ffconfig.mtype(m)
        if t == "break":
            right.append("")
            continue
        key = m.get("key", t.capitalize()) if isinstance(m, dict) else t.capitalize()
        kc = m.get("keyColor", "default") if isinstance(m, dict) else "default"
        right.append(colors.ansi(kc) + pad(key, kw) + RESET + sep + colors.ansi(text) + _SAMPLE.get(t, t) + RESET)
    rows = max(len(left), len(right))
    return [pad(left[i] if i < len(left) else "", width + gap) + (right[i] if i < len(right) else "") for i in range(rows)]


def theme_preview(t: themes.Theme, cache: dict) -> list[str]:
    if t.path not in cache:
        try:
            cache[t.path] = [color(f"{t.category} / {t.name}", BOLD), ""] + mock(t.config(), t.path)
        except Exception as e:
            cache[t.path] = [color(f"can't read this theme: {e}", RED)]
    return cache[t.path]
