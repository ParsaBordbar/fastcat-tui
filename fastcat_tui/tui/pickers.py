"""Colour and icon pickers: a menu of presets plus a typed-in fallback."""
import re

from .. import colors, icons
from ..console import BOLD, DIM, ask, color
from ..menu import screen, select


def pick_color(title: str, current: str | None = None) -> str | None:
    opts = [(colors.swatch(spec) + "  " + spec.removeprefix("38;5;"),
             label.split(" · ")[0] if " · " in label else ("" if label == spec else label))
            for spec, label in colors.PICKER]
    opts.append(("type a color…", "a name, 38;5;N (0-255) or #rrggbb"))
    specs = [spec for spec, _ in colors.PICKER]
    default = specs.index(current) if current in specs else 0
    k = select(title, opts, default)
    if k is None:
        return None
    if k < len(specs):
        return specs[k]
    screen([color(title, BOLD), color("examples: cyan · 38;5;208 · #ff8800", DIM), ""])
    raw = ask("color", current or "").strip().lower()
    if re.fullmatch(r"#?[0-9a-f]{6}", raw):
        return f"38;5;{colors.nearest_256(colors.hex_rgb(raw))}"
    if re.fullmatch(r"\d{1,3}", raw) and int(raw) < 256:
        return f"38;5;{raw}"
    if raw in colors.NAMED or re.fullmatch(r"[0-9;]+", raw):
        return raw
    return None


def pick_icon(module_type: str) -> str | None:
    """Returns a glyph, "" for no icon, or None when cancelled."""
    glyphs = icons.choices(module_type)
    opts = [(f"{g}  {icons.name(g)}", "recommended" if i == 0 else "") for i, g in enumerate(glyphs)]
    opts += [("no icon", "plain text key"), ("type a glyph or code point…", "e.g. f179")]
    k = select(f"Icon for {module_type}", opts, subtitle="icons need a Nerd Font in your terminal")
    if k is None:
        return None
    if k < len(glyphs):
        return glyphs[k]
    if k == len(glyphs):
        return ""
    screen([color(f"Icon for {module_type}", BOLD), color("paste a glyph, or type its hex code point (f179)", DIM), ""])
    return icons.parse(ask("icon")) or None
