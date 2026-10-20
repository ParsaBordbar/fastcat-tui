"""fastfetch colour specs: names ("red"), raw SGR codes ("38;5;196") and helpers to pick and blend them.

Everything written to configs is a basic name or a 256-colour code, so themes look the same in
terminals without truecolor. Hex input is mapped to the nearest 256-colour entry.
"""
import re

RESET = "\033[0m"
NAMED = {"black": 30, "red": 31, "green": 32, "yellow": 33, "blue": 34,
         "magenta": 35, "cyan": 36, "white": 37, "default": 39}
_BASIC_RGB = [(0, 0, 0), (205, 49, 49), (13, 188, 121), (229, 229, 16), (36, 114, 200),
              (188, 63, 188), (17, 168, 205), (229, 229, 229), (102, 102, 102), (241, 76, 76),
              (35, 209, 139), (245, 245, 67), (59, 142, 234), (214, 112, 214), (41, 184, 219), (255, 255, 255)]
_CUBE = (0, 95, 135, 175, 215, 255)


def to_sgr(spec) -> str:
    """fastfetch colour spec -> SGR parameter string. Unknown specs fall back to the default colour."""
    s = str(spec).strip().lower()
    if s in NAMED:
        return str(NAMED[s])
    if re.fullmatch(r"[0-9;]+", s):
        return s
    if re.fullmatch(r"#?[0-9a-f]{6}", s):
        return f"38;5;{nearest_256(hex_rgb(s))}"
    return "39"


def ansi(spec) -> str:
    return f"\033[{to_sgr(spec)}m"


def swatch(spec, text: str = "██") -> str:
    return ansi(spec) + text + RESET


def hex_rgb(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def xterm_rgb(n: int) -> tuple[int, int, int]:
    if n < 16:
        return _BASIC_RGB[n]
    if n < 232:
        n -= 16
        return _CUBE[n // 36], _CUBE[(n // 6) % 6], _CUBE[n % 6]
    v = 8 + 10 * (n - 232)
    return v, v, v


def nearest_256(rgb) -> int:
    """Closest xterm-256 entry (16-255; the first 16 vary per terminal theme)."""
    r, g, b = rgb
    return min(range(16, 256), key=lambda n: sum((a - c) ** 2 for a, c in zip(xterm_rgb(n), (r, g, b))))


def spec_rgb(spec) -> tuple[int, int, int]:
    """Approximate RGB of a spec, used for blending and brightness checks."""
    parts = to_sgr(spec).split(";")
    if len(parts) >= 3 and parts[0] == "38" and parts[1] == "5":
        return xterm_rgb(int(parts[2]))
    if len(parts) >= 5 and parts[0] == "38" and parts[1] == "2":
        return int(parts[2]), int(parts[3]), int(parts[4])
    code = next((int(p) for p in parts if p.isdigit() and (30 <= int(p) <= 37 or 90 <= int(p) <= 97)), 39)
    if code == 39:
        return 229, 229, 229
    return _BASIC_RGB[code - 30] if code < 90 else _BASIC_RGB[code - 90 + 8]


def brightness(spec) -> float:
    r, g, b = spec_rgb(spec)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def gradient(start, end, n: int) -> list[str]:
    """n 256-colour specs blending start -> end."""
    a, b = spec_rgb(start), spec_rgb(end)
    if n == 1:
        return [f"38;5;{nearest_256(a)}"]
    return [f"38;5;{nearest_256(tuple(round(x + (y - x) * i / (n - 1)) for x, y in zip(a, b)))}" for i in range(n)]


def spread(palette: list[str], n: int) -> list[str]:
    """Stretch a palette over n lines in contiguous blocks (top colour first)."""
    if not palette:
        return ["default"] * n
    return [palette[i * len(palette) // n] for i in range(n)]


# Picker: the 8 basic names (follow the terminal's own theme) plus a curated 256-colour set.
PICKER = [("white", "white"), ("red", "red"), ("green", "green"), ("yellow", "yellow"),
          ("blue", "blue"), ("magenta", "magenta"), ("cyan", "cyan"), ("default", "terminal default")]
_CURATED = [
    ("reds", [203, 196, 160, 124, 88]), ("oranges", [215, 208, 202, 166, 130]),
    ("yellows", [229, 226, 220, 178, 136]), ("greens", [120, 82, 46, 40, 34, 28, 22]),
    ("mint & teal", [121, 114, 78, 71, 37, 30]), ("cyans", [159, 123, 51, 45, 38, 31]),
    ("blues", [117, 75, 33, 27, 25, 19]), ("purples", [183, 141, 135, 99, 93, 54]),
    ("pinks", [218, 213, 205, 199, 162, 125]), ("grays", [255, 252, 248, 244, 240, 236])]
for _family, _codes in _CURATED:
    PICKER += [(f"38;5;{c}", f"{_family} · {c}") for c in _codes]
