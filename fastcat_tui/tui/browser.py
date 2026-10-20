"""Theme browser: every theme it can find, with preview, apply and share."""
from .. import fastfetch, themes
from ..console import DIM, backup_note, color
from ..menu import select
from .common import run_screen, say, theme_preview
from .editor import customize
from .share import share


def theme_actions(t: themes.Theme, cache: dict) -> None:
    opts = [("Preview", "run fastfetch with this theme, nothing changes"),
            ("Apply", "make it your fastfetch (current config is backed up)"),
            ("Apply and customize", "apply, then open the editor")]
    if t.source == "mine":
        opts.append(("Share to the gallery", "opens a pre-filled form in your browser · no git needed"))
    k = select(t.name, opts, preview=lambda _: theme_preview(t, cache))
    if k is None:
        return
    if k == 3:
        share(t.config(), t.path, t.name)
        return
    if k == 0:
        run_screen(lambda: fastfetch.preview(t), f"preview · {t.category} / {t.name}")
        return
    saved = fastfetch.apply(t)
    if k == 2:
        customize()
        return
    run_screen(fastfetch.run, f"✓ applied {t.name}" + backup_note(saved))


def browse() -> None:
    ts = themes.all_themes()
    if not ts:
        say("No themes found.", color("Get the FastCat pack from Theme sources.", DIM))
        return
    cache: dict = {}
    opts = [(t.name, t.category) for t in ts]
    k = 0
    while True:
        k = select("Themes", opts, k, preview=lambda i: theme_preview(ts[i], cache))
        if k is None:
            return
        theme_actions(ts[k], cache)
