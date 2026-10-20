"""The interactive app: main menu, theme browser, config editor, image -> logo, backups, sources."""
from .. import fastfetch, image, themes
from ..console import RED, color, is_tty
from ..menu import Quit, fullscreen, select
from .browser import browse
from .common import run_screen, say
from .community import gallery_menu
from .editor import customize
from .image_logo import image_to_logo
from .sources import backups_menu, sources_menu


def main_menu() -> None:
    k = 0
    while True:
        entries = [("Browse themes", f"{len(themes.all_themes())} themes · preview & apply", browse),
                   ("Customize my config", "colors · lines · icons · layout", customize),
                   ("Image → logo", "turn a picture into a new theme" + ("" if image.have_pillow() else " · needs pillow"),
                    image_to_logo),
                   ("Show fastfetch", "run it with your current config", lambda: run_screen(fastfetch.run)),
                   ("Backups", f"{len(fastfetch.backups())} saved · restore one", backups_menu),
                   ("Community gallery", "themes people shared · install by code", gallery_menu),
                   ("Theme sources", "get the FastCat pack · add folders", sources_menu),
                   ("Quit", "", None)]
        k = select("What do you want to do?", [(label, desc) for label, desc, _ in entries], k)
        if k is None or entries[k][2] is None:
            return
        try:
            entries[k][2]()
        except (OSError, ValueError) as e:     # a failed apply / save / unreadable theme: report it, keep the app
            say(color(f"error: {e}", RED))


def run() -> None:
    if not is_tty():
        print("fastcat-tui needs an interactive terminal. See `fastcat-tui --help` for commands.")
        return
    try:
        with fullscreen():
            main_menu()
    except (Quit, KeyboardInterrupt):
        pass
