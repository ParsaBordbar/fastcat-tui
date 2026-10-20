"""Backups and theme sources: restore an old config, get the FastCat pack, add theme folders."""
import shutil
import subprocess
from pathlib import Path

from .. import fastfetch, jsonc, settings, themes
from ..console import BOLD, DIM, GREEN, RED, ask, color
from ..menu import clear, screen, select, wait_key
from .common import mock, run_screen, say

FASTCAT_REPO = "https://github.com/m3tozz/FastCat.git"


def backups_menu() -> None:
    bs = fastfetch.backups()
    if not bs:
        say("No backups yet.", color("fastcat-tui saves one every time it changes your config.", DIM))
        return
    cache: dict = {}

    def preview(i: int) -> list[str]:
        if i not in cache:
            try:
                cache[i] = mock(jsonc.load(bs[i] / "config.jsonc"), bs[i])
            except Exception:
                cache[i] = [color("no readable config.jsonc", DIM)]
        return cache[i]

    k = select("Restore a backup", [(b.name, "") for b in bs], preview=preview)
    if k is None:
        return
    if select(f"Restore {bs[k].name}?", [("Restore", "your current config is backed up first"), ("Cancel", "")]) == 0:
        fastfetch.restore(bs[k])
        run_screen(fastfetch.run, f"✓ restored {bs[k].name}")


def _update_fastcat(clone: Path, has: bool) -> None:
    if not shutil.which("git"):
        say(color("git is not installed.", RED))
        return
    clear()
    cmd = ["git", "-C", str(clone), "pull", "--ff-only"] if has else ["git", "clone", "--depth", "1", FASTCAT_REPO, str(clone)]
    print(color(" ".join(cmd), DIM) + "\n")
    ok = subprocess.call(cmd) == 0
    print("\n" + (color("✓ done", GREEN) if ok else color("git failed", RED)))
    wait_key()


def _add_folder(st: dict, dirs: list[str]) -> None:
    screen([color("Add a theme folder", BOLD), color("folders like FastCat/ (with *-Themes inside) or one holding <Name>/fastfetch/", DIM), ""])
    d = ask("folder")
    if d and Path(d).is_dir():
        d = str(Path(d).resolve())
        if d not in dirs:
            st["theme_dirs"] = dirs + [d]
            settings.save(st)
        found = len(themes.scan(Path(d), "fastcat"))
        say(color(f"✓ added · {found} theme(s) found", GREEN))
    elif d:
        say(color("not a folder: " + d, RED))


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
            _update_fastcat(clone, has)
        elif k == 1:
            _add_folder(st, dirs)
        else:
            d = dirs[k - 2]
            if select(f"Remove {d}?", [("Remove", "the folder itself is not touched"), ("Cancel", "")]) == 0:
                st["theme_dirs"] = [x for x in dirs if x != d]
                settings.save(st)
                k = 0
