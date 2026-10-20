"""The community gallery (github.com/ParsaBordbar/fastcat-gallery): themes people submitted, fetched by code.

The gallery is a static site. index.json lists every theme with its files and their SHA-256;
each file lives at themes/<code>/<file> next to it. Installed themes go to <data>/gallery/<code>/fastfetch
and show up in the browser under "Gallery". Set FASTCAT_GALLERY_URL to use a fork or a local copy.

Sharing goes the other way without git: share() opens the gallery's "Submit a theme" issue form
pre-filled through its URL, and a bot there turns the issue into a pull request.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from . import __version__, jsonc, settings, themes

DEFAULT_URL = "https://parsabordbar.github.io/fastcat-gallery/"
SUBMIT_URL = "https://github.com/ParsaBordbar/fastcat-gallery/issues/new"
MAX_URL = 7000                      # browsers and GitHub cope with this; longer fields go via the clipboard
CODE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$")
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ALLOWED_EXT = {".jsonc", ".json", ".txt", ".png"}
SKIP_FILES = {"theme.json"}         # gallery metadata, not part of the fastfetch config
MAX_FILE = 256 * 1024
BLOCKED_MODULES = {"command"}       # runs programs; the gallery rejects these, and so do we


class GalleryError(OSError):
    """Network, hash or safety failure; an OSError so the CLI and TUI report it like other I/O errors."""


def base_url() -> str:
    url = os.environ.get("FASTCAT_GALLERY_URL") or DEFAULT_URL
    return url if url.endswith("/") else url + "/"


def _get(url: str, limit: int, timeout: float = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": f"fastcat-tui/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read(limit + 1)
    except OSError as e:
        raise GalleryError(f"can't reach the gallery ({getattr(e, 'reason', e)})") from None
    if len(data) > limit:
        raise GalleryError(f"{url} is too large")
    return data


def fetch_index() -> list[dict]:
    try:
        data = json.loads(_get(base_url() + "index.json", 8 * 1024 * 1024))
        entries = data["themes"]
    except (ValueError, KeyError, TypeError):
        raise GalleryError("the gallery index is not valid") from None
    return [e for e in entries if isinstance(e, dict) and isinstance(e.get("code"), str) and CODE_RE.match(e["code"])]


def lookup(code: str, index: list[dict]) -> dict | None:
    code = code.strip().lower()
    return next((e for e in index if e["code"] == code), None)


def installed(code: str) -> Path | None:
    p = settings.gallery_dir() / code / "fastfetch"
    return p if (p / "config.jsonc").is_file() else None


def check_config(cfg) -> None:
    if not isinstance(cfg, dict):
        raise GalleryError("config.jsonc is not a JSON object")
    for m in cfg.get("modules", []):
        t = m.get("type") if isinstance(m, dict) else m
        if isinstance(t, str) and t.lower() in BLOCKED_MODULES:
            raise GalleryError(f"refusing to install: the theme uses the '{t}' module, which runs programs")


def install(entry: dict) -> themes.Theme:
    """Download a theme's files, check their hashes and config, and save it. Replaces an older copy."""
    code = entry["code"]
    files = entry.get("files")
    if not isinstance(files, dict) or "config.jsonc" not in files:
        raise GalleryError(f"gallery entry {code!r} has no config.jsonc")
    root = settings.gallery_dir()
    root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{code}-", dir=root))
    try:
        dest = tmp / "fastfetch"
        dest.mkdir()
        for name, digest in files.items():
            if name in SKIP_FILES:
                continue
            if not isinstance(name, str) or not FILE_RE.match(name) or Path(name).suffix.lower() not in ALLOWED_EXT:
                raise GalleryError(f"refusing to install: unexpected file {name!r}")
            data = _get(f"{base_url()}themes/{code}/{name}", MAX_FILE)
            if hashlib.sha256(data).hexdigest() != digest:
                raise GalleryError(f"{name} does not match the gallery index (try again later)")
            (dest / name).write_bytes(data)
        try:
            check_config(jsonc.load(dest / "config.jsonc"))
        except ValueError as e:
            raise GalleryError(f"config.jsonc is not valid: {e}") from None
        final = root / code
        if final.exists():
            shutil.rmtree(final)
        tmp.rename(final)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
    return themes.Theme(code, "Gallery", final / "fastfetch", "gallery")


# ---------------------------------------------------------------- sharing
def suggest_code(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:32].strip("-") or "my-theme"


def share_files(cfg: dict, base: Path) -> tuple[str, str | None]:
    """(config.jsonc text, ascii.txt text or None) as the gallery wants them, logo pointed at ascii.txt."""
    check_config(cfg)
    out = jsonc.loads(jsonc.dumps(cfg))
    lg = out.get("logo")
    if isinstance(lg, str):
        lg = out["logo"] = {"source": lg}
    f = themes.logo_file(cfg, base)
    if f:
        lg["source"] = "~/.config/fastfetch/ascii.txt"
        return jsonc.dumps(out), f.read_text(encoding="utf-8", errors="replace")
    if isinstance(lg, dict) and isinstance(lg.get("source"), str) and lg.get("type") not in ("builtin", "small", "data", "data-raw", "none"):
        src = themes.resolve_source(lg["source"], base)
        if not src.is_file() and "/" in lg["source"]:
            raise GalleryError(f"the logo file {src} does not exist")
        if src.is_file():
            raise GalleryError("only text logos can be shared through the form; for an image logo open a pull request "
                               "on github.com/ParsaBordbar/fastcat-gallery with the image file")
    return jsonc.dumps(out), None


def copy_to_clipboard(text: str) -> bool:
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        if shutil.which(cmd[0]):
            try:
                return subprocess.run(cmd, input=text.encode(), timeout=5).returncode == 0
            except (OSError, subprocess.SubprocessError):
                continue
    return False


def share(cfg: dict, base: Path, code: str, name: str, description: str = "", tags: str = "",
          open_browser: bool = True) -> dict:
    """Pre-fill the gallery's submission form with a theme and open it.

    Fields too long for the URL (usually a big braille logo) go to the clipboard, or failing that are
    left in the saved folder. Returns {url, folder, missing: [form box, ...], copied: form box or None}.
    """
    code = code.strip().lower()
    if not CODE_RE.match(code):
        raise GalleryError("the code must be 2-32 chars of a-z, 0-9 and '-'")
    if not name.strip() or len(name) > 40:
        raise GalleryError("the name must be 1-40 characters")
    config_text, logo_text = share_files(cfg, base)
    folder = settings.data_dir() / "share" / code
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "config.jsonc").write_text(config_text, encoding="utf-8")
    if logo_text:
        (folder / "ascii.txt").write_text(logo_text, encoding="utf-8")

    params = {"template": "theme.yml", "title": f"Theme: {name}", "code": code, "name": name,
              "description": description[:200], "tags": tags}
    missing = []
    for field, box, text in (("config", "config.jsonc", config_text), ("logo", "ascii.txt", logo_text)):
        if not text:
            continue
        url = SUBMIT_URL + "?" + urllib.parse.urlencode(params | {field: text})
        if len(url) <= MAX_URL:
            params[field] = text
        else:
            missing.append((box, text))
    url = SUBMIT_URL + "?" + urllib.parse.urlencode(params)
    copied = missing[-1][0] if missing and copy_to_clipboard(missing[-1][1]) else None
    if open_browser:
        webbrowser.open(url)
    return {"url": url, "folder": folder, "missing": [box for box, _ in missing], "copied": copied}


def share_instructions(result: dict) -> list[str]:
    """What the user still has to do in the browser, one line each."""
    lines = []
    for box in result["missing"]:
        if box == result["copied"]:
            lines.append(f"{box} was too long for the link and is on your clipboard: paste it into the {box} box")
        else:
            lines.append(f"paste {result['folder'] / box} into the {box} box")
    lines.append("tick the rights box and submit; a bot checks it and opens the pull request")
    return lines
