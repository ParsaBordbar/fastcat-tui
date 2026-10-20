"""Terminal output: colours, banner, text prompts and ANSI-aware width helpers."""
import os
import re
import shutil
import sys

# 256-colour codes so the accent also works in terminals without truecolor (older Terminal.app).
CORAL = "\033[38;5;173m"
GREEN = "\033[38;5;108m"
RED = "\033[38;5;167m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_PIECE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|.", re.S)


def is_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def color(text: str, *codes: str) -> str:
    """Wrap text in ANSI codes when stdout is a terminal, otherwise return it unchanged."""
    return "".join(codes) + text + RESET if sys.stdout.isatty() else text


def visible_len(s: str) -> int:
    """Printed width. Braille, block and Nerd Font glyphs all take one cell."""
    return len(ANSI_RE.sub("", s))


def pad(s: str, width: int) -> str:
    return s + " " * max(0, width - visible_len(s))


def clip(s: str, width: int) -> str:
    """Cut s to `width` printed cells, keeping its colour codes intact."""
    out, n, styled = [], 0, False
    for piece in _PIECE_RE.findall(s):
        if piece.startswith("\x1b"):
            out.append(piece)
            styled = True
        elif n < width:
            out.append(piece)
            n += 1
    return "".join(out) + (RESET if styled else "")


def term_size() -> tuple[int, int]:
    size = shutil.get_terminal_size((100, 30))
    return size.columns, size.lines


def backup_note(saved) -> str:
    return f" · previous config backed up to {saved}" if saved else ""


TAGLINE = "fastfetch themes, your way"


def banner_lines() -> list[str]:
    plain = f"fastcat-tui · {TAGLINE}"
    inner = len(plain) + 2
    title = f"{BOLD}fastcat-tui{RESET}{CORAL} · {TAGLINE}"
    return [color(f"╭{'─' * inner}╮", CORAL),
            color("│ ", CORAL) + title + color(" │", CORAL),
            color(f"╰{'─' * inner}╯", CORAL)]


def ask(prompt: str, default: str = "") -> str:
    """Prompt for a line of text. Strips quotes and escaped spaces (drag-and-drop paths), expands ~."""
    hint = color(f" [{default}]", DIM) if default else ""
    try:
        value = input(color("? ", CORAL, BOLD) + prompt + hint + ": ").strip()
    except EOFError:
        value = ""
    value = value.strip("'\"").replace("\\ ", " ")
    return os.path.expanduser(value) if value else default


def ask_int(prompt: str, default: int, lo: int, hi: int) -> int:
    while True:
        raw = ask(f"{prompt} ({lo}-{hi})", str(default))
        try:
            value = int(raw)
        except ValueError:
            print(color("  not a number: " + raw, RED))
            continue
        if lo <= value <= hi:
            return value
        print(color(f"  must be between {lo} and {hi}", RED))
