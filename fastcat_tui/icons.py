"""Nerd Font icons for fastfetch keys.

Only Basic Multilingual Plane private-use glyphs (U+E000-U+F8FF) are used: every terminal draws them
one cell wide, so the info text stays in a straight column. The newer U+F0000+ "md" icons can be
drawn two cells wide (Terminal.app) and push their line out of alignment.
"""
import sys

OS_ICONS = {
    "macos": "", "linux": "", "windows": "", "freebsd": "",
    "arch": "", "debian": "", "fedora": "", "ubuntu": "", "manjaro": "",
    "linuxmint": "", "opensuse": "", "gentoo": "", "nixos": "",
    "alpine": "", "centos": "", "elementary": "", "pop": "",
    "endeavouros": "", "void": "", "kali": "", "raspbian": "",
}

GLYPH_NAMES = {
    "": "apple", "": "tux", "": "windows", "": "freebsd", "": "arch",
    "": "debian", "": "fedora", "": "ubuntu", "": "manjaro", "": "mint",
    "": "opensuse", "": "gentoo", "": "nixos", "": "alpine", "": "centos",
    "": "elementary", "": "pop!_os", "": "endeavour", "": "void", "": "kali",
    "": "raspberry pi",
    "": "laptop", "": "desktop", "": "server", "": "gear", "": "gears",
    "": "cube", "": "clock", "": "bolt", "": "package", "": "terminal",
    "": "bash", "": "code", "": "tv", "": "browser", "": "window",
    "": "grid", "": "sitemap", "": "paintbrush", "": "magic wand",
    "": "image", "": "font", "": "pointer", "": "terminal box",
    "": "microchip", "": "cpu", "": "circuit board", "": "memory",
    "": "swap arrows", "": "hard drive", "": "globe", "": "wifi",
    "": "battery", "": "plug", "": "language", "": "calendar",
    "": "music", "": "user", "": "home", "": "heart", "": "star",
    "": "leaf", "": "fire", "": "eye", "": "paw",
}

# module type -> icons to offer, recommended first
MODULE_ICONS = {
    "host": ["", "", ""],
    "kernel": ["", "", ""],
    "uptime": ["", ""],
    "packages": ["", ""],
    "shell": ["", "", ""],
    "display": ["", ""],
    "monitor": ["", ""],
    "de": ["", "", ""],
    "wm": ["", "", ""],
    "wmtheme": ["", ""],
    "theme": ["", ""],
    "icons": ["", ""],
    "font": [""],
    "terminalfont": [""],
    "cursor": [""],
    "terminal": ["", ""],
    "cpu": ["", ""],
    "gpu": ["", "", ""],
    "memory": ["", ""],
    "swap": [""],
    "disk": [""],
    "localip": ["", "", ""],
    "battery": ["", ""],
    "poweradapter": [""],
    "locale": [""],
    "datetime": ["", ""],
    "date": [""],
    "time": [""],
    "media": [""],
    "player": [""],
    "title": ["", ""],
}
FUN_ICONS = ["", "", "", "", "", "", "", ""]


def detect_os() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("freebsd"):
        return "freebsd"
    try:
        with open("/etc/os-release") as f:
            info = dict(line.rstrip("\n").split("=", 1) for line in f if "=" in line)
    except OSError:
        return "linux"
    ids = [info.get("ID", "").strip('"')] + info.get("ID_LIKE", "").strip('"').split()
    return next((i for i in ids if i in OS_ICONS), "linux")


def os_icon(os_id: str | None = None) -> str:
    return OS_ICONS.get(os_id or detect_os(), OS_ICONS["linux"])


def choices(module_type: str) -> list[str]:
    if module_type == "os":
        mine = os_icon()
        return [mine] + [g for g in OS_ICONS.values() if g != mine]
    return MODULE_ICONS.get(module_type, []) + [g for g in FUN_ICONS if g not in MODULE_ICONS.get(module_type, [])]


def recommended(module_type: str) -> str | None:
    if module_type == "os":
        return os_icon()
    return MODULE_ICONS.get(module_type, [None])[0]


def is_icon(ch: str) -> bool:
    """Private-use glyph (Nerd Font icon), in either plane."""
    cp = ord(ch)
    return 0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0x10FFFD


def name(glyph: str) -> str:
    return GLYPH_NAMES.get(glyph, f"U+{ord(glyph):04X}") if glyph else ""


def parse(text: str) -> str | None:
    """User input -> glyph: a pasted glyph, or a hex code point like f179 / U+F179."""
    t = text.strip()
    if len(t) == 1:
        return t
    t = t.upper().removeprefix("U+").removeprefix("0X")
    try:
        return chr(int(t, 16))
    except ValueError:
        return None
