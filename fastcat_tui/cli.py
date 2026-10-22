"""Command-line entry point. No arguments opens the TUI; subcommands script the same actions."""
import argparse
import sys
from pathlib import Path

from . import __version__, fastfetch, ffconfig, gallery, image, logo, settings, themes
from .console import GREEN, RED, backup_note, color, is_tty, printable

USAGE = """\
Browse, customise and create fastfetch themes.

Examples:
    fastcat-tui                                   # no args -> interactive TUI
    fastcat-tui list                              # every theme it can see
    fastcat-tui preview Venom                     # run fastfetch with a theme, change nothing
    fastcat-tui apply Large/Cat                   # install a theme (backs up your config first)
    fastcat-tui gallery                           # list community themes
    fastcat-tui gallery cat neon                  # ... matching every word, like the site's search
    fastcat-tui get neon-cat --apply              # install one by its code (and apply it)
    fastcat-tui share --name "Neon Cat"           # submit your config to the gallery (no git needed)
    fastcat-tui logo ~/Pictures/cat.png --width 36 --name Kitty --apply
    fastcat-tui fix-icons                         # one-cell Nerd Font icons in your config
    fastcat-tui restore                           # put the newest backup back

Gallery: https://parsabordbar.github.io/fastcat-gallery/
Needs fastfetch. Icons need a Nerd Font in your terminal; image -> logo needs Pillow.
"""


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="fastcat-tui", description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"fastcat-tui {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list", help="list themes")
    for name, text in (("preview", "run fastfetch with a theme"), ("apply", "install a theme")):
        p = sub.add_parser(name, help=text)
        p.add_argument("theme", help="theme name, or Category/Name")
    p = sub.add_parser("logo", help="turn an image into a theme")
    p.add_argument("image")
    p.add_argument("--width", type=int, default=40, help="logo width in cells (default 40)")
    p.add_argument("--mode", choices=image.MODES, default="auto")
    p.add_argument("--colors", type=int, default=4, help="colors to keep in color mode (1-9, default 4)")
    p.add_argument("--trim", type=int, default=0, help="shrink the shape by N px (removes sticker borders)")
    p.add_argument("--name", help="theme name (default: image file name)")
    p.add_argument("--apply", action="store_true", help="apply the new theme right away")
    p.add_argument("--force", action="store_true", help="overwrite a theme of yours with the same name")
    p = sub.add_parser("gallery", help="list themes in the community gallery")
    p.add_argument("query", nargs="*", help="only themes matching every word (name, author, description, tags, code)")
    p = sub.add_parser("get", help="install a gallery theme by its code")
    p.add_argument("code", help="the code shown on the gallery site")
    p.add_argument("--apply", action="store_true", help="apply it right away")
    p = sub.add_parser("share", help="submit a theme to the community gallery (opens a pre-filled form)")
    p.add_argument("theme", nargs="?", help="theme to share (default: your current fastfetch config)")
    p.add_argument("--name", help="display name (default: the theme's name)")
    p.add_argument("--code", help="the code people will type (default: from the name)")
    p.add_argument("--description", default="", help="one line about it")
    p.add_argument("--tags", default="", help="comma separated, e.g. 'cat, neon'")
    p.add_argument("--no-browser", action="store_true", help="print the link instead of opening it")
    sub.add_parser("fix-icons", help="replace icon keys in your config with one-cell Nerd Font icons")
    p = sub.add_parser("restore", help="restore a backup (newest by default)")
    p.add_argument("backup", nargs="?", help="backup folder name, from `fastcat-tui restore --list`")
    p.add_argument("--list", action="store_true", help="list backups")
    sub.add_parser("paths", help="show where fastcat-tui keeps its files")
    return ap


def _theme(name: str) -> themes.Theme:
    t = themes.find(name)
    if not t:
        sys.exit(f"no theme called {name!r} (see: fastcat-tui list)")
    return t


def cmd_list(args) -> None:
    for t in themes.all_themes():
        print(f"{t.category + '/' + t.name:32} {t.source}")


def cmd_preview(args) -> None:
    sys.exit(fastfetch.preview(_theme(args.theme)))


def cmd_apply(args) -> None:
    t = _theme(args.theme)
    saved = fastfetch.apply(t)
    print(color(f"✓ applied {t.category}/{t.name}", GREEN) + backup_note(saved))


def cmd_logo(args) -> None:
    if not image.have_pillow():
        sys.exit("image -> logo needs Pillow: pip install pillow")
    name = themes.safe_name(args.name or Path(args.image).stem.title())
    if themes.mine_dir(name).exists() and not args.force:
        sys.exit(f"you already have a theme called {name!r}: pick another --name, or pass --force to overwrite it")
    text, palette, used = image.convert(args.image, args.width, args.mode, args.colors, args.trim)
    theme, _ = themes.save_logo_theme(name, text, palette)
    print("\n".join(logo.render(text, palette)) if is_tty() else logo.plain(text), end="\n\n")
    w, h = logo.size(text)
    print(color(f"✓ saved {name}", GREEN), f"({w}x{h}, {used} mode) -> {theme.path}")
    if args.apply:
        print(color("✓ applied", GREEN) + backup_note(fastfetch.apply(theme)))


def cmd_gallery(args) -> None:
    found = gallery.search(gallery.fetch_index(), " ".join(args.query))
    if args.query and not found:
        sys.exit(f"nothing in the gallery matches {' '.join(args.query)!r}")
    for e in sorted(found, key=lambda e: e["code"]):
        mark = "  installed" if gallery.installed(e["code"]) else ""
        print(f"{e['code']:24} {printable(e.get('name', ''))[:28]:28} by {printable(e.get('author', ''))[:20]}{mark}")


def cmd_get(args) -> None:
    entry = gallery.lookup(args.code, gallery.fetch_index())
    if not entry:
        sys.exit(f"no gallery theme with code {args.code!r} (see: fastcat-tui gallery)")
    t = gallery.install(entry)
    print(color(f"✓ installed {entry['code']}", GREEN),
          f"({printable(entry.get('name'))} by {printable(entry.get('author'))}) -> {t.path}")
    if args.apply:
        print(color("✓ applied", GREEN) + backup_note(fastfetch.apply(t)))
    else:
        print(f"apply it with: fastcat-tui apply Gallery/{entry['code']}")


def cmd_share(args) -> None:
    if args.theme:
        t = _theme(args.theme)
        cfg, base, name = t.config(), t.path, args.name or t.name
    else:
        cfg, base, name = fastfetch.load_live(), fastfetch.config_dir(), args.name
        if cfg is None:
            sys.exit(f"no readable config at {fastfetch.config_path()}")
        if not name:
            sys.exit("give it a name: fastcat-tui share --name \"Neon Cat\"")
    res = gallery.share(cfg, base, args.code or gallery.suggest_code(name), name, args.description, args.tags,
                        open_browser=not args.no_browser)
    if args.no_browser:
        print("open this to submit:", res["url"])
    else:
        print(color("✓ opened the gallery's submit form in your browser", GREEN))
    for line in gallery.share_instructions(res):
        print("  ·", line)


def cmd_fix_icons(args) -> None:
    cfg = fastfetch.load_live()
    if cfg is None:
        sys.exit(f"no readable config at {fastfetch.config_path()}")
    n = ffconfig.fix_icons(cfg)
    if not n:
        print("icons already look right")
        return
    saved = fastfetch.backup()
    fastfetch.save_live(cfg)
    print(color(f"✓ {n} icon(s) updated", GREEN) + backup_note(saved))


def cmd_restore(args) -> None:
    bs = fastfetch.backups()
    if args.list:
        print("\n".join(b.name for b in bs) or "no backups")
        return
    if not bs:
        sys.exit("no backups")
    pick = next((b for b in bs if b.name == args.backup), None) if args.backup else bs[0]
    if not pick:
        sys.exit(f"no backup called {args.backup!r}")
    fastfetch.restore(pick)
    print(color(f"✓ restored {pick.name}", GREEN))


def cmd_paths(args) -> None:
    for label, path in (("fastfetch config", fastfetch.config_dir()), ("your themes", settings.user_themes_dir()),
                        ("backups", settings.backups_dir()), ("FastCat pack", settings.fastcat_clone_dir()),
                        ("gallery themes", settings.gallery_dir()), ("settings", settings.settings_path())):
        print(f"{label:17} {path}")


COMMANDS = {"list": cmd_list, "preview": cmd_preview, "apply": cmd_apply, "logo": cmd_logo,
            "gallery": cmd_gallery, "get": cmd_get, "share": cmd_share, "fix-icons": cmd_fix_icons,
            "restore": cmd_restore, "paths": cmd_paths}


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        from .tui import run
        run()
        return
    parser = build_parser()
    args = parser.parse_args(argv)
    command = COMMANDS.get(args.cmd)
    if command is None:
        parser.print_help()
        return
    try:
        command(args)
    except (OSError, ValueError) as e:
        sys.exit(color(f"error: {e}", RED))
