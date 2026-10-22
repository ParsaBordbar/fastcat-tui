"""Community gallery: search and install themes by code, or share your own."""
from .. import colors, gallery, logo
from ..console import BOLD, CORAL, DIM, GREEN, RED, ask, color, printable
from ..menu import screen, select
from .browser import theme_actions
from .common import say
from .share import share_live


def _entry_preview(e: dict) -> list[str]:
    """The site's theme card, in the terminal: name, author, description, tags, install command, logo."""
    head = [color(_name(e), BOLD) + color(f"  by {printable(e.get('author', '?'))}", DIM)]
    if e.get("description"):
        head.append(color(printable(e["description"]), DIM))
    if gallery.tags(e):
        head.append(color(" ".join("#" + printable(t) for t in gallery.tags(e)), DIM))
    head.append(color(f"fastcat-tui get {e['code']}", CORAL)
                + (color("  · installed", GREEN) if gallery.installed(e["code"]) else ""))
    keys = "".join(colors.swatch(c, "▮") for c in e.get("keyColors") or [] if isinstance(c, str))
    link = printable(e.get("link") or "")
    if keys or link:
        head.append(keys + ("  " if keys and link else "") + color(link, DIM))
    head.append("")
    text = e.get("logo")
    lcolors = {k: v for k, v in (e.get("colors") or {}).items() if isinstance(v, str)}
    return head + (logo.render(text, lcolors) if isinstance(text, str) else [color("(image or built-in logo)", DIM)])


def _name(e: dict) -> str:
    return printable(e.get("name", e["code"]))


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
    query, shown = "", index

    def preview(i: int) -> list[str]:
        if i == 0:
            return [color("Find a theme on the site, copy its code, paste it here.", DIM), "", url]
        if i == 1:
            return [color("Same search as the site: every word has to match", DIM),
                    color("the name, author, description, tags or code.", DIM), "", gallery.page_url(query)]
        if i == 2:
            return [color("Sends your current config and logo to the gallery's submit form.", DIM),
                    color("You review it in the browser before anything is posted.", DIM)]
        return _entry_preview(shown[i - 3])

    k = 0
    while True:
        opts = [("Enter a code", "copied from the gallery site"),
                ("Search", f"{query!r} · {len(shown)} of {len(index)}" if query else "name, author, tag, code…"),
                ("Share my config", "submit your current fastfetch to the gallery")]
        opts += [(_name(e), e["code"] + (" · installed" if gallery.installed(e["code"]) else ""))
                 for e in shown]
        k = select("Community gallery", opts, k, subtitle=status, preview=preview)
        if k is None:
            return
        if k == 1:
            screen([color("Search the gallery", BOLD), color("leave it empty to show every theme", DIM), ""])
            query = ask("search")
            shown = gallery.search(index, query)
            k = 3 if query and shown else 1
            continue
        if k == 2:
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
            e = shown[k - 3]
        _install(e)
