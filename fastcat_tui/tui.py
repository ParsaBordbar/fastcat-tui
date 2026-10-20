"""The interactive app: main menu, theme browser, config editor, image -> logo, backups, sources."""
import re
import shutil
import subprocess
from pathlib import Path

from . import colors, fastfetch, ffconfig, gallery, icons, image, jsonc, logo, settings, themes
from .colors import RESET
from .console import BOLD, CORAL, DIM, GREEN, RED, ask, ask_int, color, is_tty, pad, visible_len
from .menu import Quit, checklist, clear, fullscreen, screen, select, wait_key

FASTCAT_REPO = "https://github.com/m3tozz/FastCat.git"
SEPARATORS = [" ", "  ", ": ", " → ", " │ ", " ~ ", " ❯ "]


def _say(*lines: str) -> None:
    screen(list(lines))
    wait_key()


def _run_screen(fn, title: str | None = None) -> None:
    clear()
    if title:
        print(color(title, DIM) + "\n")
    if not fastfetch.available():
        print(color("fastfetch is not installed.", RED) + " Install it: https://github.com/fastfetch-cli/fastfetch#installation")
    else:
        try:
            fn()
        except (OSError, ValueError) as e:
            print(color(f"error: {e}", RED))
    wait_key()


# ---------------------------------------------------------------- previews
_SAMPLE = {"os": "your OS", "host": "your machine", "kernel": "kernel", "uptime": "2 hours", "packages": "packages",
           "shell": "zsh", "terminal": "terminal", "de": "desktop", "wm": "window manager", "cpu": "cpu",
           "gpu": "graphics", "memory": "4 GiB / 16 GiB", "disk": "120 GiB / 500 GiB", "datetime": "today"}


def _mock(cfg: dict, base: Path, logo_text: str | None = None) -> list[str]:
    """Rough picture of what fastfetch will print: logo, then each line's key and value."""
    if logo_text is None:
        f = themes.logo_file(cfg, base)
        logo_text = f.read_text(encoding="utf-8", errors="replace") if f else None
    lg = ffconfig.logo_section(cfg) or {}
    padding = lg.get("padding") if isinstance(lg.get("padding"), dict) else {}
    left = logo.render(logo_text, ffconfig.logo_colors(cfg)) if logo_text else []
    if not logo_text and lg.get("source"):
        left = [color(f"[image logo: {Path(str(lg['source'])).name}]", DIM)]
    left = [""] * int(padding.get("top", 0)) + left
    width = max((visible_len(l) for l in left), default=0)
    gap = int(padding.get("right", 4)) if left else 0
    kw, sep, text = ffconfig.key_width(cfg), ffconfig.separator(cfg), ffconfig.text_color(cfg)
    right = []
    for m in ffconfig.modules(cfg):
        t = ffconfig.mtype(m)
        if t == "break":
            right.append("")
            continue
        key = m.get("key", t.capitalize()) if isinstance(m, dict) else t.capitalize()
        kc = m.get("keyColor", "default") if isinstance(m, dict) else "default"
        right.append(colors.ansi(kc) + pad(key, kw) + RESET + sep + colors.ansi(text) + _SAMPLE.get(t, t) + RESET)
    rows = max(len(left), len(right))
    return [pad(left[i] if i < len(left) else "", width + gap) + (right[i] if i < len(right) else "") for i in range(rows)]


def _theme_preview(t: themes.Theme, cache: dict) -> list[str]:
    if t.path not in cache:
        try:
            cache[t.path] = [color(f"{t.category} / {t.name}", BOLD), ""] + _mock(t.config(), t.path)
        except Exception as e:
            cache[t.path] = [color(f"can't read this theme: {e}", RED)]
    return cache[t.path]


# ---------------------------------------------------------------- pickers
def pick_color(title: str, current: str | None = None) -> str | None:
    opts = [(colors.swatch(spec) + "  " + spec.removeprefix("38;5;"),
             label.split(" · ")[0] if " · " in label else ("" if label == spec else label))
            for spec, label in colors.PICKER]
    opts.append(("type a color…", "a name, 38;5;N (0-255) or #rrggbb"))
    specs = [spec for spec, _ in colors.PICKER]
    default = specs.index(current) if current in specs else 0
    k = select(title, opts, default)
    if k is None:
        return None
    if k < len(specs):
        return specs[k]
    screen([color(title, BOLD), color("examples: cyan · 38;5;208 · #ff8800", DIM), ""])
    raw = ask("color", current or "").strip().lower()
    if re.fullmatch(r"#?[0-9a-f]{6}", raw):
        return f"38;5;{colors.nearest_256(colors.hex_rgb(raw))}"
    if re.fullmatch(r"\d{1,3}", raw) and int(raw) < 256:
        return f"38;5;{raw}"
    if raw in colors.NAMED or re.fullmatch(r"[0-9;]+", raw):
        return raw
    return None


def pick_icon(module_type: str) -> str | None:
    """Returns a glyph, "" for no icon, or None when cancelled."""
    glyphs = icons.choices(module_type)
    opts = [(f"{g}  {icons.name(g)}", "recommended" if i == 0 else "") for i, g in enumerate(glyphs)]
    opts += [("no icon", "plain text key"), ("type a glyph or code point…", "e.g. f179")]
    k = select(f"Icon for {module_type}", opts, subtitle="icons need a Nerd Font in your terminal")
    if k is None:
        return None
    if k < len(glyphs):
        return glyphs[k]
    if k == len(glyphs):
        return ""
    screen([color(f"Icon for {module_type}", BOLD), color("paste a glyph, or type its hex code point (f179)", DIM), ""])
    return icons.parse(ask("icon")) or None


# ---------------------------------------------------------------- customize
def _key_colors(cfg: dict, base: Path) -> bool:
    n = len(ffconfig.info_indices(cfg))
    opts = [("Match the logo", "logo colors, top to bottom"), ("One color", "every key the same"),
            ("Gradient", "blend between two colors"), ("Per line…", "pick each key's color")]
    k = select("Key colors", opts, preview=lambda _: _mock(cfg, base))
    if k is None:
        return False
    if k == 0:
        f = themes.logo_file(cfg, base)
        used = logo.used_colors(f.read_text(encoding="utf-8", errors="replace")) if f else sorted(ffconfig.logo_colors(cfg)) or ["1"]
        ffconfig.set_key_colors(cfg, colors.spread(ffconfig.visible_logo_palette(cfg, used), n))
        return True
    if k == 1:
        c = pick_color("Key color")
        if c:
            ffconfig.set_key_colors(cfg, [c] * n)
        return bool(c)
    if k == 2:
        a = pick_color("Gradient: top color")
        b = pick_color("Gradient: bottom color") if a else None
        if a and b:
            ffconfig.set_key_colors(cfg, colors.gradient(a, b, n))
        return bool(a and b)
    changed, sel = False, 0
    while True:
        idx = ffconfig.info_indices(cfg)
        mods = ffconfig.modules(cfg)
        opts = []
        for i in idx:
            m = mods[i]
            kc = m.get("keyColor", "default") if isinstance(m, dict) else "default"
            opts.append((colors.swatch(kc, ffconfig.key_icon(m) or "■") + "  " + ffconfig.mtype(m), kc))
        sel = select("Key color per line", opts, sel, preview=lambda _: _mock(cfg, base))
        if sel is None:
            return changed
        m = mods[idx[sel]]
        c = pick_color(f"Key color: {ffconfig.mtype(m)}", m.get("keyColor") if isinstance(m, dict) else None)
        if c:
            ffconfig.as_dict(cfg, idx[sel])["keyColor"] = c
            changed = True


def _logo_colors(cfg: dict, base: Path) -> bool:
    if ffconfig.logo_section(cfg) is None:
        _say("This config has no logo.")
        return False
    f = themes.logo_file(cfg, base)
    used = logo.used_colors(f.read_text(encoding="utf-8", errors="replace")) if f else sorted(ffconfig.logo_colors(cfg)) or ["1"]
    changed, k = False, 0
    while True:
        lc = ffconfig.logo_colors(cfg)
        opts = [(f"${s}  " + colors.swatch(lc.get(s, "default"), "████"), lc.get(s, "default")) for s in used]
        k = select("Logo colors", opts, k, preview=lambda _: _mock(cfg, base))
        if k is None:
            return changed
        c = pick_color(f"Logo color ${used[k]}", lc.get(used[k]))
        if c:
            ffconfig.set_logo_color(cfg, used[k], c)
            changed = True


def _line_label(m) -> str:
    t = ffconfig.mtype(m)
    if t == "break":
        return "── blank line ──"
    return f"{ffconfig.key_icon(m) or icons.recommended(t) or ' '}  {t}"


def _lines(cfg: dict) -> bool:
    mods = ffconfig.modules(cfg)
    present = {ffconfig.mtype(m) for m in mods}
    extra = [t for t in ffconfig.CATALOG if t not in present or t == "break"]
    items = [(_line_label(m), "", True) for m in mods] + [(_line_label(t), "add", False) for t in extra]
    res = checklist("Lines: [x] shown", items, subtitle="new lines get the recommended icon")
    if res is None:
        return False
    first_color = next((m.get("keyColor") for m in mods if isinstance(m, dict) and m.get("keyColor")), None)
    new = [mods[i] if i < len(mods) else ffconfig.new_module(extra[i - len(mods)], first_color) for i, on in res if on]
    if new == mods:
        return False
    cfg["modules"] = new
    return True


def _icons(cfg: dict, base: Path) -> bool:
    changed, k = False, 0
    while True:
        k = select("Icons", [("Fix all icons", "one-cell Nerd Font icons, your OS logo on the OS line"),
                             ("Change one…", "pick a line, then its icon")], k,
                   preview=lambda _: _mock(cfg, base), subtitle="icons need a Nerd Font in your terminal")
        if k is None:
            return changed
        if k == 0:
            n = ffconfig.fix_icons(cfg)
            changed |= bool(n)
            _say(color(f"✓ {n} icon(s) updated", GREEN) if n else "Icons already look right.")
            continue
        sel = 0
        while True:
            idx = ffconfig.info_indices(cfg)
            mods = ffconfig.modules(cfg)
            opts = [(_line_label(mods[i]), icons.name(ffconfig.key_icon(mods[i]))) for i in idx]
            sel = select("Change which icon?", opts, sel, preview=lambda _: _mock(cfg, base))
            if sel is None:
                break
            g = pick_icon(ffconfig.mtype(mods[idx[sel]]))
            if g is None:
                continue
            if g:
                ffconfig.set_icon(cfg, idx[sel], g)
            else:
                ffconfig.as_dict(cfg, idx[sel]).pop("key", None)
            changed = True


def _layout(cfg: dict, base: Path) -> bool:
    changed, k = False, 0
    while True:
        kw = ffconfig.key_width(cfg)
        opts = [("Key width", f"{kw} cells" if kw else "off (text starts right after each key)"),
                ("Separator", repr(ffconfig.separator(cfg))),
                ("Centre beside the logo", "blank lines above the info, or move the logo down")]
        k = select("Layout", opts, k, preview=lambda _: _mock(cfg, base))
        if k is None:
            return changed
        if k == 0:
            screen([color("Key width", BOLD), color("pads every key to the same width so the text lines up (0 = off)", DIM), ""])
            ffconfig.set_key_width(cfg, ask_int("key width", kw or 3, 0, 30))
            changed = True
        elif k == 1:
            s = select("Separator", [(repr(s), "") for s in SEPARATORS] + [("type one…", "")])
            if s is None:
                continue
            if s < len(SEPARATORS):
                ffconfig.set_separator(cfg, SEPARATORS[s])
            else:
                screen([color("Separator", BOLD), ""])
                try:
                    raw = input(color("? ", CORAL, BOLD) + "separator: ")
                except EOFError:
                    raw = ""
                if raw:
                    ffconfig.set_separator(cfg, raw)
            changed = True
        else:
            h = themes.logo_height(cfg, base)
            if not h:
                _say("No text logo to centre against.")
                continue
            _say(color("✓ " + ffconfig.center(cfg, h), GREEN))
            changed = True


def _save_as_theme(cfg: dict, base: Path) -> None:
    screen([color("Save as my theme", BOLD), color("a copy of this config and its logo, listed under Mine", DIM), ""])
    name = themes.safe_name(ask("theme name"))
    dest = themes.mine_dir(name)
    if dest.exists() and select(f"'{name}' exists", [("Overwrite it", ""), ("Cancel", "")]) != 0:
        return
    if base.is_dir():
        shutil.copytree(base, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
    dest.mkdir(parents=True, exist_ok=True)
    jsonc.save(dest / "config.jsonc", cfg)
    _say(color(f"✓ saved as {name}", GREEN), color(str(dest), DIM))


def customize() -> None:
    cfg = fastfetch.load_live()
    base = fastfetch.config_dir()
    dirty = cfg is None
    if cfg is None:
        if select(f"No fastfetch config at {fastfetch.config_path()}",
                  [("Start from a clean config", "recommended lines and icons, built-in logo"), ("Back", "")]) != 0:
            return
        cfg = ffconfig.recommended()
        cfg["logo"] = {"padding": {"right": 4}}
    backed_up, leaving, k = False, False, 0
    while True:
        n = len(ffconfig.info_indices(cfg))
        lc = ffconfig.logo_colors(cfg)
        opts = [("Logo colors", " ".join(colors.swatch(c) for c in lc.values()) or "—"),
                ("Key colors", "".join(colors.swatch(c, "▮") for c in ffconfig.key_colors(cfg)[:16])),
                ("Text color", colors.swatch(ffconfig.text_color(cfg))),
                ("Lines", f"{n} shown · show, hide, reorder"),
                ("Icons", "fix all · change one"),
                ("Layout", "key width · separator · centre"),
                ("Preview", "run fastfetch with these changes"),
                ("Save", "write " + str(fastfetch.config_path()).replace(str(Path.home()), "~")),
                ("Save as my theme", "keep a copy under Mine")]
        title = "Customize your config" + (color("  · unsaved changes", CORAL) if dirty else "")
        k = select(title, opts, k, preview=lambda _: _mock(cfg, base))
        if k is None:
            if not dirty:
                return
            a = select("Unsaved changes", [("Save", "write them to your config"), ("Discard", "leave without saving"),
                                           ("Keep editing", "")])
            if a == 0:
                k, leaving = 7, True
            elif a == 1:
                return
            else:
                k = 0
                continue
        if k == 0:
            dirty |= _logo_colors(cfg, base)
        elif k == 1:
            dirty |= _key_colors(cfg, base)
        elif k == 2:
            c = pick_color("Text color", ffconfig.text_color(cfg))
            if c:
                ffconfig.set_text_color(cfg, c)
                dirty = True
        elif k == 3:
            dirty |= _lines(cfg)
        elif k == 4:
            dirty |= _icons(cfg, base)
        elif k == 5:
            dirty |= _layout(cfg, base)
        elif k == 6:
            _run_screen(lambda: fastfetch.run(cfg, base), "preview · nothing saved yet")
        elif k == 7:
            saved = None if backed_up else fastfetch.backup()
            backed_up = True
            fastfetch.save_live(cfg)
            dirty = False
            _run_screen(fastfetch.run, "✓ saved" + (f" · previous config backed up to {saved}" if saved else ""))
            if leaving:
                return
        elif k == 8:
            _save_as_theme(cfg, base)


# ---------------------------------------------------------------- themes
def _theme_actions(t: themes.Theme, cache: dict) -> None:
    opts = [("Preview", "run fastfetch with this theme, nothing changes"),
            ("Apply", "make it your fastfetch (current config is backed up)"),
            ("Apply and customize", "apply, then open the editor")]
    if t.source == "mine":
        opts.append(("Share to the gallery", "opens a pre-filled form in your browser · no git needed"))
    k = select(t.name, opts, preview=lambda _: _theme_preview(t, cache))
    if k is None:
        return
    if k == 3:
        _share(t.config(), t.path, t.name)
        return
    if k == 0:
        _run_screen(lambda: fastfetch.preview(t), f"preview · {t.category} / {t.name}")
        return
    saved = fastfetch.apply(t)
    if k == 2:
        customize()
        return
    _run_screen(fastfetch.run, f"✓ applied {t.name}" + (f" · previous config backed up to {saved}" if saved else ""))


def browse() -> None:
    ts = themes.all_themes()
    if not ts:
        _say("No themes found.", color("Get the FastCat pack from Theme sources.", DIM))
        return
    cache: dict = {}
    opts = [(t.name, t.category) for t in ts]
    k = 0
    while True:
        k = select("Themes", opts, k, preview=lambda i: _theme_preview(ts[i], cache))
        if k is None:
            return
        _theme_actions(ts[k], cache)


# ---------------------------------------------------------------- community gallery
def _gallery_preview(e: dict) -> list[str]:
    head = [color(f"{e.get('name', e['code'])}", BOLD) + color(f"  by {e.get('author', '?')}", DIM)]
    if e.get("description"):
        head.append(color(str(e["description"]), DIM))
    head += [color(f"code: {e['code']}", CORAL) + (color("  · installed", GREEN) if gallery.installed(e["code"]) else ""), ""]
    text = e.get("logo")
    lcolors = {k: v for k, v in (e.get("colors") or {}).items() if isinstance(v, str)}
    return head + (logo.render(text, lcolors) if isinstance(text, str) else [color("(image or built-in logo)", DIM)])


def _gallery_install(e: dict) -> None:
    screen([color(f"downloading {e['code']}…", DIM)])
    t = gallery.install(e)
    _theme_actions(t, {})


def _share(cfg: dict, base: Path, default_name: str = "") -> None:
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
        _say(color(f"can't share this: {e}", RED))
        return
    _say(color("✓ opened the submit form in your browser", GREEN), "",
         *[f"  · {line}" for line in gallery.share_instructions(res)], "",
         color("if no browser opened, use this link:", DIM), res["url"][:200] + ("…" if len(res["url"]) > 200 else ""))


def _share_live() -> None:
    cfg = fastfetch.load_live()
    if cfg is None:
        _say(color(f"no readable config at {fastfetch.config_path()}", RED))
        return
    _share(cfg, fastfetch.config_dir())


def gallery_menu() -> None:
    url = gallery.base_url()
    screen([color("Community gallery", BOLD), color(f"loading {url}index.json…", DIM)])
    try:
        index = sorted(gallery.fetch_index(), key=lambda e: str(e.get("name", e["code"])).lower())
        status = f"{len(index)} themes · {url}"
    except gallery.GalleryError as e:      # still let people share while the gallery is unreachable
        index, status = [], color(str(e), RED)
    k = 0
    while True:
        opts = [("Enter a code", "copied from the gallery site"),
                ("Share my config", "submit your current fastfetch to the gallery")]
        opts += [(str(e.get("name", e["code"])), e["code"] + (" · installed" if gallery.installed(e["code"]) else ""))
                 for e in index]
        k = select("Community gallery", opts, k, subtitle=status,
                   preview=lambda i: _gallery_preview(index[i - 2]) if i > 1 else
                   [color("Find a theme on the site, copy its code, paste it here.", DIM), "", url] if i == 0 else
                   [color("Sends your current config and logo to the gallery's submit form.", DIM),
                    color("You review it in the browser before anything is posted.", DIM)])
        if k is None:
            return
        if k == 1:
            _share_live()
            continue
        if k == 0:
            screen([color("Install from the gallery", BOLD), ""])
            code = ask("code")
            if not code:
                continue
            e = gallery.lookup(code, index)
            if not e:
                _say(color(f"no gallery theme with code {code!r}", RED))
                continue
        else:
            e = index[k - 2]
        _gallery_install(e)


# ---------------------------------------------------------------- image -> logo
def image_to_logo() -> None:
    if not image.have_pillow():
        _say(color("Image → logo needs Pillow.", BOLD), "",
             "  pip install pillow", color("  (or: pip install 'fastcat-tui[image]')", DIM))
        return
    screen([color("Image → logo", BOLD),
            color("png with a transparent background works best; stickers and line art work too", DIM), ""])
    path = ask("image file (drag it into the terminal)")
    if not path or not Path(path).is_file():
        if path:
            _say(color("not found: " + path, RED))
        return
    width, mode, ncolors, trim, k = 40, "auto", 4, 0, 0
    while True:
        try:
            text, palette, used = image.convert(path, width, mode, ncolors, trim)
        except Exception as e:
            _say(color(f"could not convert: {e}", RED))
            return
        w, h = logo.size(text)
        art = logo.render(text, palette)
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
    if themes.mine_dir(name).exists() and select(f"'{name}' exists", [("Overwrite it", ""), ("Cancel", "")]) != 0:
        return
    t, cfg = themes.save_logo_theme(name, text, palette)
    k = select(f"✓ saved {name}", [("Apply it now", "current config is backed up"), ("Preview", "nothing changes"),
                                   ("Done", str(t.path).replace(str(Path.home()), "~"))],
               preview=lambda _: _mock(cfg, t.path))
    if k == 0:
        saved = fastfetch.apply(t)
        _run_screen(fastfetch.run, f"✓ applied {name}" + (f" · previous config backed up to {saved}" if saved else ""))
    elif k == 1:
        _run_screen(lambda: fastfetch.preview(t), f"preview · {name}")


# ---------------------------------------------------------------- backups & sources
def backups_menu() -> None:
    bs = fastfetch.backups()
    if not bs:
        _say("No backups yet.", color("fastcat-tui saves one every time it changes your config.", DIM))
        return
    cache: dict = {}

    def prev(i: int) -> list[str]:
        if i not in cache:
            try:
                cache[i] = _mock(jsonc.load(bs[i] / "config.jsonc"), bs[i])
            except Exception:
                cache[i] = [color("no readable config.jsonc", DIM)]
        return cache[i]

    k = select("Restore a backup", [(b.name, "") for b in bs], preview=prev)
    if k is None:
        return
    if select(f"Restore {bs[k].name}?", [("Restore", "your current config is backed up first"), ("Cancel", "")]) == 0:
        fastfetch.restore(bs[k])
        _run_screen(fastfetch.run, f"✓ restored {bs[k].name}")


def sources_menu() -> None:
    k = 0
    while True:
        st = settings.load()
        clone = settings.fastcat_clone_dir()
        has = (clone / ".git").is_dir()
        dirs = st.get("theme_dirs", [])
        opts = [("Update the FastCat pack" if has else "Download the FastCat pack", "m3tozz/FastCat, 50+ themes · git"),
                ("Add a theme folder", "a FastCat checkout or a folder of your own themes")]
        opts += [(d, "enter to remove") for d in dirs]
        k = select("Theme sources", opts, k, subtitle=f"FastCat pack: {clone if has else 'not downloaded'}")
        if k is None:
            return
        if k == 0:
            if not shutil.which("git"):
                _say(color("git is not installed.", RED))
                continue
            clear()
            cmd = ["git", "-C", str(clone), "pull", "--ff-only"] if has else ["git", "clone", "--depth", "1", FASTCAT_REPO, str(clone)]
            print(color(" ".join(cmd), DIM) + "\n")
            ok = subprocess.call(cmd) == 0
            print("\n" + (color("✓ done", GREEN) if ok else color("git failed", RED)))
            wait_key()
        elif k == 1:
            screen([color("Add a theme folder", BOLD), color("folders like FastCat/ (with *-Themes inside) or one holding <Name>/fastfetch/", DIM), ""])
            d = ask("folder")
            if d and Path(d).is_dir():
                if d not in dirs:
                    st["theme_dirs"] = dirs + [d]
                    settings.save(st)
                found = len(themes._scan(Path(d), "fastcat"))
                _say(color(f"✓ added · {found} theme(s) found", GREEN))
            elif d:
                _say(color("not a folder: " + d, RED))
        else:
            d = dirs[k - 2]
            if select(f"Remove {d}?", [("Remove", "the folder itself is not touched"), ("Cancel", "")]) == 0:
                st["theme_dirs"] = [x for x in dirs if x != d]
                settings.save(st)
                k = 0


# ---------------------------------------------------------------- main
def main_menu() -> None:
    k = 0
    while True:
        n_themes = len(themes.all_themes())
        opts = [("Browse themes", f"{n_themes} themes · preview & apply"),
                ("Customize my config", "colors · lines · icons · layout"),
                ("Image → logo", "turn a picture into a new theme" + ("" if image.have_pillow() else " · needs pillow")),
                ("Show fastfetch", "run it with your current config"),
                ("Backups", f"{len(fastfetch.backups())} saved · restore one"),
                ("Community gallery", "themes people shared · install by code"),
                ("Theme sources", "get the FastCat pack · add folders"),
                ("Quit", "")]
        k = select("What do you want to do?", opts, k)
        if k is None or k == 7:
            return
        try:
            [browse, customize, image_to_logo, lambda: _run_screen(fastfetch.run), backups_menu, gallery_menu,
             sources_menu][k]()
        except (OSError, ValueError) as e:     # a failed apply / save / unreadable theme: report it, keep the app
            _say(color(f"error: {e}", RED))


def run() -> None:
    if not is_tty():
        print("fastcat-tui needs an interactive terminal. See `fastcat-tui --help` for commands.")
        return
    try:
        with fullscreen():
            main_menu()
    except (Quit, KeyboardInterrupt):
        pass
