"""Image -> logo: convert a picture to a braille logo, tune it, and save it as a theme."""
from pathlib import Path

from .. import fastfetch, image, logo, themes
from ..console import BOLD, DIM, RED, ask, ask_int, backup_note, color
from ..menu import screen, select
from .common import home_relative, mock, overwrite_ok, run_screen, say


def image_to_logo() -> None:
    if not image.have_pillow():
        say(color("Image → logo needs Pillow.", BOLD), "",
            "  pip install pillow", color("  (or: pip install 'fastcat-tui[image]')", DIM))
        return
    screen([color("Image → logo", BOLD),
            color("png with a transparent background works best; stickers and line art work too", DIM), ""])
    path = ask("image file (drag it into the terminal)")
    if not path or not Path(path).is_file():
        if path:
            say(color("not found: " + path, RED))
        return
    width, mode, ncolors, trim, k = 40, "auto", 4, 0, 0
    converted = None
    while True:
        if converted is None or converted[0] != (width, mode, ncolors, trim):
            try:
                text, palette, used = image.convert(path, width, mode, ncolors, trim)
            except Exception as e:
                say(color(f"could not convert: {e}", RED))
                return
            converted = (width, mode, ncolors, trim), logo.render(text, palette)
        art = converted[1]
        w, h = logo.size(text)
        opts = [("Save as a theme", f"{w}×{h} cells"),
                ("Width", f"{width} cells"),
                ("Mode", mode if mode != "auto" else f"auto → {used}"),
                ("Colors", f"{ncolors}" if used == "color" else "only in color mode"),
                ("Trim border", f"{trim}px" + (" · eats into sticker outlines" if trim else " · off"))]
        k = select("Image → logo", opts, k, preview=lambda _: art)
        if k is None:
            return
        if k == 1:
            screen([color("Width", BOLD), color("terminal cells; 30-45 suits most screens", DIM), ""])
            width = ask_int("width", width, 8, 120)
        elif k == 2:
            m = select("Mode", [("auto", "pick for me"), ("color", "keep the image's colors"),
                                ("light", "light parts light up (art on dark)"), ("ink", "dark lines light up (line art)")],
                       image.MODES.index(mode))
            mode = image.MODES[m] if m is not None else mode
        elif k == 3:
            screen([color("Colors", BOLD), color("how many colors to keep (fastfetch allows 9)", DIM), ""])
            ncolors = ask_int("colors", ncolors, 1, 9)
        elif k == 4:
            screen([color("Trim border", BOLD), color("shrinks the shape by N pixels: removes white sticker outlines", DIM), ""])
            trim = ask_int("pixels", trim, 0, 80)
        else:
            _save_logo_theme(Path(path), text, palette)
            return


def _save_logo_theme(src: Path, text: str, palette: dict) -> None:
    screen([color("Save as a theme", BOLD), ""])
    name = themes.safe_name(ask("theme name", themes.safe_name(src.stem.title())))
    if not overwrite_ok(name):
        return
    t, cfg = themes.save_logo_theme(name, text, palette)
    k = select(f"✓ saved {name}", [("Apply it now", "current config is backed up"), ("Preview", "nothing changes"),
                                   ("Done", home_relative(t.path))],
               preview=lambda _: mock(cfg, t.path))
    if k == 0:
        saved = fastfetch.apply(t)
        run_screen(fastfetch.run, f"✓ applied {name}" + backup_note(saved))
    elif k == 1:
        run_screen(lambda: fastfetch.preview(t), f"preview · {name}")
