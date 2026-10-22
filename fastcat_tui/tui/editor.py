"""Config editor: logo, key and text colours, lines, icons and layout of the live config."""
import shutil
from pathlib import Path

from .. import colors, fastfetch, ffconfig, icons, jsonc, logo, themes
from ..console import BOLD, CORAL, DIM, GREEN, ask, ask_int, backup_note, color
from ..menu import checklist, screen, select
from .common import home_relative, mock, overwrite_ok, run_screen, say
from .pickers import pick_color, pick_icon

SEPARATORS = [" ", "  ", ": ", " → ", " │ ", " ~ ", " ❯ "]


def _logo_slots(cfg: dict, base: Path) -> list[str]:
    """Colour slots the logo uses; for image and built-in logos, the slots the config sets."""
    text = themes.logo_text(cfg, base)
    return logo.used_colors(text) if text is not None else sorted(ffconfig.logo_colors(cfg)) or ["1"]


def _key_colors(cfg: dict, base: Path) -> bool:
    n = len(ffconfig.info_indices(cfg))
    opts = [("Match the logo", "logo colors, top to bottom"), ("One color", "every key the same"),
            ("Gradient", "blend between two colors"), ("Per line…", "pick each key's color")]
    k = select("Key colors", opts, preview=lambda _: mock(cfg, base))
    if k is None:
        return False
    if k == 0:
        ffconfig.set_key_colors(cfg, colors.spread(ffconfig.visible_logo_palette(cfg, _logo_slots(cfg, base)), n))
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
        sel = select("Key color per line", opts, sel, preview=lambda _: mock(cfg, base))
        if sel is None:
            return changed
        m = mods[idx[sel]]
        c = pick_color(f"Key color: {ffconfig.mtype(m)}", m.get("keyColor") if isinstance(m, dict) else None)
        if c:
            ffconfig.as_dict(cfg, idx[sel])["keyColor"] = c
            changed = True


def _logo_colors(cfg: dict, base: Path) -> bool:
    if ffconfig.logo_section(cfg) is None:
        say("This config has no logo.")
        return False
    used = _logo_slots(cfg, base)
    changed, k = False, 0
    while True:
        lc = ffconfig.logo_colors(cfg)
        opts = [(f"${s}  " + colors.swatch(lc.get(s, "default"), "████"), lc.get(s, "default")) for s in used]
        k = select("Logo colors", opts, k, preview=lambda _: mock(cfg, base))
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
                   preview=lambda _: mock(cfg, base), subtitle="icons need a Nerd Font in your terminal")
        if k is None:
            return changed
        if k == 0:
            n = ffconfig.fix_icons(cfg)
            changed |= bool(n)
            say(color(f"✓ {n} icon(s) updated", GREEN) if n else "Icons already look right.")
            continue
        sel = 0
        while True:
            idx = ffconfig.info_indices(cfg)
            mods = ffconfig.modules(cfg)
            opts = [(_line_label(mods[i]), icons.name(ffconfig.key_icon(mods[i]))) for i in idx]
            sel = select("Change which icon?", opts, sel, preview=lambda _: mock(cfg, base))
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
        k = select("Layout", opts, k, preview=lambda _: mock(cfg, base))
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
                say("No text logo to centre against.")
                continue
            say(color("✓ " + ffconfig.center(cfg, h), GREEN))
            changed = True


def _save_as_theme(cfg: dict, base: Path) -> None:
    screen([color("Save as my theme", BOLD), color("a copy of this config and its logo, listed under Mine", DIM), ""])
    name = themes.safe_name(ask("theme name"))
    if not overwrite_ok(name):
        return
    dest = themes.mine_dir(name)
    if base.is_dir():
        shutil.copytree(base, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
    dest.mkdir(parents=True, exist_ok=True)
    jsonc.save(dest / "config.jsonc", cfg)
    say(color(f"✓ saved as {name}", GREEN), color(str(dest), DIM))


def customize() -> None:
    cfg = fastfetch.load_live()
    base = fastfetch.config_dir()
    dirty = cfg is None
    if cfg is None:
        if select(f"No fastfetch config at {fastfetch.config_path()}",
                  [("Start from a clean config", "recommended lines and icons, built-in logo"), ("Back", "")], back=False) != 0:
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
                ("Save", "write " + home_relative(fastfetch.config_path())),
                ("Save as my theme", "keep a copy under Mine")]
        title = "Customize your config" + (color("  · unsaved changes", CORAL) if dirty else "")
        k = select(title, opts, k, preview=lambda _: mock(cfg, base))
        if k is None:
            if not dirty:
                return
            a = select("Unsaved changes", [("Save", "write them to your config"), ("Discard", "leave without saving"),
                                           ("Keep editing", "")], back=False)
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
            run_screen(lambda: fastfetch.run(cfg, base), "preview · nothing saved yet")
        elif k == 7:
            saved = None if backed_up else fastfetch.backup()
            backed_up = True
            fastfetch.save_live(cfg)
            dirty = False
            run_screen(fastfetch.run, "✓ saved" + backup_note(saved))
            if leaving:
                return
        elif k == 8:
            _save_as_theme(cfg, base)
