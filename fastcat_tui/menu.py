"""Full-screen arrow-key menus on the terminal's alternate screen.

select()     pick one entry; an optional preview pane follows the cursor
checklist()  toggle and reorder entries (used for the module list)
Keys: up/down or j/k move, enter selects, esc / left / backspace go back, q quits.
"""
import os
import select as _select
import sys
import termios
import tty
from contextlib import contextmanager

from .console import BOLD, CORAL, DIM, HIDE_CURSOR, RESET, SHOW_CURSOR, banner_lines, clip, color, pad, term_size, visible_len

ALT_ON, ALT_OFF, HOME_CLEAR = "\033[?1049h", "\033[?1049l", "\033[H\033[2J"
_SEQS = {b"[A": "up", b"[B": "down", b"[C": "right", b"[D": "left", b"OA": "up", b"OB": "down",
         b"OC": "right", b"OD": "left", b"[H": "home", b"[F": "end", b"[5~": "pgup", b"[6~": "pgdn"}


class Quit(Exception):
    """User pressed q / ctrl-c."""


@contextmanager
def fullscreen():
    sys.stdout.write(ALT_ON)
    sys.stdout.flush()
    try:
        yield
    finally:
        sys.stdout.write(ALT_OFF + SHOW_CURSOR)
        sys.stdout.flush()


@contextmanager
def raw_mode():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()
    try:
        tty.setraw(fd)
        yield fd
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()


def read_key(fd: int) -> str:
    ch = os.read(fd, 1)
    if ch == b"\x1b":
        if not _select.select([fd], [], [], 0.05)[0]:
            return "esc"
        # Read one escape sequence only, so a following key already in the buffer
        # (key repeat, fast typing) is not swallowed into it.
        seq = os.read(fd, 1)
        if seq in (b"[", b"O"):
            while len(seq) < 8:
                b = os.read(fd, 1)
                seq += b
                if not b or 0x40 <= b[0] <= 0x7E:
                    break
        return _SEQS.get(seq, "esc")
    if ch in (b"\r", b"\n"):
        return "enter"
    if ch == b" ":
        return "space"
    if ch in (b"\x7f", b"\x08"):
        return "back"
    if ch in (b"\x03", b"\x04"):
        return "quit"
    return ch.decode(errors="ignore")


def clear() -> None:
    sys.stdout.write(HOME_CLEAR)
    sys.stdout.flush()


def screen(lines: list[str]) -> None:
    """Clear and draw the banner plus lines (cooked mode: before a text prompt or a command)."""
    clear()
    print("\n".join(banner_lines() + [""] + lines))


def wait_key(message: str = "press any key to go back") -> None:
    sys.stdout.write("\r\n" + color(message, DIM))
    sys.stdout.flush()
    with raw_mode() as fd:
        if read_key(fd) == "quit":
            raise Quit


def _draw(body: list[str], hint: str, preview: list[str] | None, subtitle: str | None) -> None:
    cols, rows = term_size()
    head = banner_lines() + [""] + ([color(subtitle, DIM), ""] if subtitle else [])
    lines = head + body
    if preview:
        menu_w = max((visible_len(l) for l in body), default=0) + 4
        prev_w = max(visible_len(p) for p in preview)
        if cols >= menu_w + prev_w:
            n = max(len(body), len(preview))
            body = [pad(body[i] if i < len(body) else "", menu_w) + (preview[i] if i < len(preview) else "")
                    for i in range(n)]
            lines = head + body
        else:
            lines = head + body + [""] + preview
    lines = [clip(l, cols) for l in lines[: rows - 2]] + ["", color(hint, DIM)]
    sys.stdout.write(HOME_CLEAR + "\r\n".join(lines))
    sys.stdout.flush()


def _window(n: int, idx: int, room: int) -> tuple[int, int]:
    rows = min(n, max(3, room))
    top = min(max(0, idx - rows // 2), max(0, n - rows))
    return top, rows


def select(title: str, options: list[tuple[str, str]], default: int = 0, preview=None,
           subtitle: str | None = None, hint: str = "↑/↓ move · enter select · esc back · q quit") -> int | None:
    """Arrow-key menu. options: (label, description). Returns the index, or None when going back.

    preview(idx) -> list of lines, drawn beside the menu (or under it on narrow terminals).
    """
    if not options:
        return None
    idx = max(0, min(default, len(options) - 1))
    label_w = min(42, max(visible_len(o[0]) for o in options))
    with raw_mode() as fd:
        while True:
            cols, rows = term_size()
            room = rows - len(banner_lines()) - 6 - (2 if subtitle else 0)
            top, shown = _window(len(options), idx, room)
            body = [color(title, BOLD)]
            for i in range(top, top + shown):
                label, desc = options[i]
                label = label if visible_len(label) <= 42 else clip(label, 41) + "…"
                text = pad(label, label_w)
                if i == idx:
                    row = color("❯ ", CORAL, BOLD) + (color(text, CORAL, BOLD) if "\x1b" not in text else BOLD + text + RESET)
                else:
                    row = "  " + text
                body.append(" " + row + (color(f"  {desc}", DIM) if desc else ""))
            more = f" · {idx + 1}/{len(options)}" if shown < len(options) else ""
            _draw(body, hint + more, preview(idx) if preview else None, subtitle)
            key = read_key(fd)
            if key in ("up", "k"):
                idx = (idx - 1) % len(options)
            elif key in ("down", "j"):
                idx = (idx + 1) % len(options)
            elif key in ("pgup", "home"):
                idx = 0 if key == "home" else max(0, idx - shown)
            elif key in ("pgdn", "end"):
                idx = len(options) - 1 if key == "end" else min(len(options) - 1, idx + shown)
            elif key in ("enter", "right", "l"):
                return idx
            elif key in ("esc", "left", "back", "h"):
                return None
            elif key in ("q", "quit"):
                raise Quit


def checklist(title: str, items: list[tuple[str, str, bool]], subtitle: str | None = None) -> list[tuple[int, bool]] | None:
    """Toggle (space) and reorder (K/J or +/-) entries. Returns [(original index, on)] in the new
    order, or None when cancelled."""
    order = list(range(len(items)))
    on = [it[2] for it in items]
    idx = 0
    label_w = min(40, max((visible_len(it[0]) for it in items), default=0))
    hint = "space show/hide · K/J move line up/down · enter save · esc cancel"
    with raw_mode() as fd:
        while True:
            cols, rows = term_size()
            room = rows - len(banner_lines()) - 6 - (2 if subtitle else 0)
            top, shown = _window(len(order), idx, room)
            body = [color(title, BOLD)]
            for pos in range(top, top + shown):
                i = order[pos]
                label, desc, _ = items[i]
                box = color("[x]", CORAL, BOLD) if on[i] else color("[ ]", DIM)
                cursor = color("❯", CORAL, BOLD) if pos == idx else " "
                text = pad(label, label_w)
                body.append(f" {cursor} {box} " + (text if on[i] else color(text, DIM)) + (color(f"  {desc}", DIM) if desc else ""))
            _draw(body, hint, None, subtitle)
            key = read_key(fd)
            if key in ("up", "k"):
                idx = (idx - 1) % len(order)
            elif key in ("down", "j"):
                idx = (idx + 1) % len(order)
            elif key == "space":
                on[order[idx]] = not on[order[idx]]
            elif key in ("K", "-") and idx > 0:
                order[idx - 1], order[idx] = order[idx], order[idx - 1]
                idx -= 1
            elif key in ("J", "+", "=") and idx < len(order) - 1:
                order[idx + 1], order[idx] = order[idx], order[idx + 1]
                idx += 1
            elif key == "enter":
                return [(i, on[i]) for i in order]
            elif key in ("esc", "back"):
                return None
            elif key == "quit":
                raise Quit
