"""Community gallery: install themes by code, or share your own."""
from .. import gallery, logo
from ..console import BOLD, CORAL, DIM, GREEN, RED, ask, color
from ..menu import screen, select
from .browser import theme_actions
from .common import say
from .share import share_live


def _entry_preview(e: dict) -> list[str]:
    head = [color(f"{e.get('name', e['code'])}", BOLD) + color(f"  by {e.get('author', '?')}", DIM)]
    if e.get("description"):
        head.append(color(str(e["description"]), DIM))
    head += [color(f"code: {e['code']}", CORAL) + (color("  · installed", GREEN) if gallery.installed(e["code"]) else ""), ""]
    text = e.get("logo")
    lcolors = {k: v for k, v in (e.get("colors") or {}).items() if isinstance(v, str)}
    return head + (logo.render(text, lcolors) if isinstance(text, str) else [color("(image or built-in logo)", DIM)])


def _install(e: dict) -> None:
    screen([color(f"downloading {e['code']}…", DIM)])
    theme_actions(gallery.install(e), {})


def gallery_menu() -> None:
    url = gallery.base_url()
    screen([color("Community gallery", BOLD), color(f"loading {url}index.json…", DIM)])
    try:
        index = sorted(gallery.fetch_index(), key=lambda e: str(e.get("name", e["code"])).lower())
        status = f"{len(index)} themes · {url}"
    except gallery.GalleryError as e:      # still let people share while the gallery is unreachable
        index, status = [], color(str(e), RED)

    def preview(i: int) -> list[str]:
        if i == 0:
            return [color("Find a theme on the site, copy its code, paste it here.", DIM), "", url]
        if i == 1:
            return [color("Sends your current config and logo to the gallery's submit form.", DIM),
                    color("You review it in the browser before anything is posted.", DIM)]
        return _entry_preview(index[i - 2])

    k = 0
    while True:
        opts = [("Enter a code", "copied from the gallery site"),
                ("Share my config", "submit your current fastfetch to the gallery")]
        opts += [(str(e.get("name", e["code"])), e["code"] + (" · installed" if gallery.installed(e["code"]) else ""))
                 for e in index]
        k = select("Community gallery", opts, k, subtitle=status, preview=preview)
        if k is None:
            return
        if k == 1:
            share_live()
            continue
        if k == 0:
            screen([color("Install from the gallery", BOLD), ""])
            code = ask("code")
            if not code:
                continue
            e = gallery.lookup(code, index)
            if not e:
                say(color(f"no gallery theme with code {code!r}", RED))
                continue
        else:
            e = index[k - 2]
        _install(e)
