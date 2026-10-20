"""ASCII logo files with fastfetch colour tags: $1..$9 switch colour, $$ is a literal dollar."""
import re

from .colors import RESET, ansi
from .console import printable

TOKEN_RE = re.compile(r"\$(\d|\$)")


def used_colors(text: str) -> list[str]:
    """Colour slots a logo uses, in order. Untagged logos print in colour 1."""
    found = sorted({m.group(1) for m in TOKEN_RE.finditer(text) if m.group(1) != "$"})
    return found or ["1"]


def plain(text: str) -> str:
    return TOKEN_RE.sub(lambda m: "$" if m.group(1) == "$" else "", text)


def size(text: str) -> tuple[int, int]:
    """(width, height) in terminal cells."""
    lines = plain(text).rstrip("\n").splitlines()
    return max((len(l) for l in lines), default=0), len(lines)


def render(text: str, colors: dict) -> list[str]:
    """Logo lines with ANSI colours, the way fastfetch draws them (colour carries across lines)."""
    current = colors.get("1", "default")
    out = []
    for line in printable(text).rstrip("\n").splitlines():
        parts, i = [ansi(current)], 0
        for m in TOKEN_RE.finditer(line):
            parts.append(line[i:m.start()])
            if m.group(1) == "$":
                parts.append("$")
            else:
                current = colors.get(m.group(1), "default")
                parts.append(ansi(current))
            i = m.end()
        parts.append(line[i:] + RESET)
        out.append("".join(parts))
    return out
