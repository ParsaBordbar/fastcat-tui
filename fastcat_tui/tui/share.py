"""Sharing a config to the community gallery through its pre-filled submit form."""
from pathlib import Path

from .. import fastfetch, gallery
from ..console import BOLD, DIM, GREEN, RED, ask, color
from ..menu import screen
from .common import say


def share(cfg: dict, base: Path, default_name: str = "") -> None:
    screen([color("Share to the community gallery", BOLD),
            color("Opens the gallery's submit form, filled in. Submit it and a bot opens the pull request.", DIM), ""])
    name = ask("name", default_name)
    if not name:
        return
    code = ask("code people will type", gallery.suggest_code(name))
    description = ask("one line about it")
    tags = ask("tags, comma separated")
    try:
        res = gallery.share(cfg, base, code, name, description, tags)
    except gallery.GalleryError as e:
        say(color(f"can't share this: {e}", RED))
        return
    say(color("✓ opened the submit form in your browser", GREEN), "",
        *[f"  · {line}" for line in gallery.share_instructions(res)], "",
        color("if no browser opened, use this link:", DIM), res["url"][:200] + ("…" if len(res["url"]) > 200 else ""))


def share_live() -> None:
    cfg = fastfetch.load_live()
    if cfg is None:
        say(color(f"no readable config at {fastfetch.config_path()}", RED))
        return
    share(cfg, fastfetch.config_dir())
