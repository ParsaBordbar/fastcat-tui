import hashlib
import json
from urllib.parse import parse_qs, urlparse

import pytest

from fastcat_tui import cli, gallery, jsonc, themes

CONFIG = '// c\n{"logo": {"source": "~/.config/fastfetch/ascii.txt"}, "modules": ["os",],}'


@pytest.fixture
def site(tmp_path, monkeypatch):
    """A fake gallery on disk, served through a file:// URL."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("FASTCAT_TUI_HOME", str(tmp_path / "app"))
    root = tmp_path / "site"
    monkeypatch.setenv("FASTCAT_GALLERY_URL", root.as_uri())

    def publish(code: str, files: dict[str, str], hashes: dict[str, str] | None = None):
        d = root / "themes" / code
        d.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (d / name).write_text(text)
        index = json.loads((root / "index.json").read_text()) if (root / "index.json").exists() else {"themes": []}
        digests = {n: hashlib.sha256(t.encode()).hexdigest() for n, t in files.items()} | (hashes or {})
        index["themes"].append({"code": code, "name": code.title(), "author": "me", "files": digests})
        (root / "index.json").write_text(json.dumps(index))

    return publish


def test_get_installs_and_lists_under_gallery(site, capsys):
    site("neon-cat", {"config.jsonc": CONFIG, "ascii.txt": "$1##\n", "theme.json": "{}"})
    cli.main(["get", "NEON-CAT"])
    path = gallery.installed("neon-cat")
    assert path and (path / "ascii.txt").read_text() == "$1##\n"
    assert not (path / "theme.json").exists()
    t = themes.find("gallery/neon-cat")
    assert (t.category, t.source) == ("Gallery", "gallery")
    assert t.logo_text() == "$1##\n"
    cli.main(["gallery"])
    assert "installed" in capsys.readouterr().out


def test_unknown_code(site):
    site("neon-cat", {"config.jsonc": CONFIG})
    with pytest.raises(SystemExit, match="no gallery theme"):
        cli.main(["get", "nope"])


def test_hash_mismatch_installs_nothing(site):
    site("neon-cat", {"config.jsonc": CONFIG}, hashes={"config.jsonc": "0" * 64})
    entry = gallery.lookup("neon-cat", gallery.fetch_index())
    with pytest.raises(gallery.GalleryError, match="does not match"):
        gallery.install(entry)
    assert gallery.installed("neon-cat") is None


def test_refuses_command_module(site):
    site("evil", {"config.jsonc": '{"modules": [{"type": "Command", "text": "rm -rf ~"}]}'})
    with pytest.raises(gallery.GalleryError, match="runs programs"):
        gallery.install(gallery.lookup("evil", gallery.fetch_index()))
    assert gallery.installed("evil") is None


@pytest.mark.parametrize("name", ["../escape.txt", "run.sh", ".hidden.txt"])
def test_refuses_unexpected_files(site, name):
    site("odd", {"config.jsonc": CONFIG})
    entry = gallery.lookup("odd", gallery.fetch_index())
    entry["files"][name] = "0" * 64
    with pytest.raises(gallery.GalleryError, match="unexpected file"):
        gallery.install(entry)


def test_reinstall_replaces_old_copy(site):
    site("neon-cat", {"config.jsonc": CONFIG, "old.txt": "x"})
    gallery.install(gallery.lookup("neon-cat", gallery.fetch_index()))
    entry = {"code": "neon-cat", "files": {"config.jsonc": hashlib.sha256(CONFIG.encode()).hexdigest()}}
    gallery.install(entry)
    assert not (gallery.installed("neon-cat") / "old.txt").exists()


# ---------------------------------------------------------------- sharing
def _form(url: str) -> dict:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


@pytest.fixture
def mine(site, tmp_path, monkeypatch):
    monkeypatch.setattr(gallery, "copy_to_clipboard", lambda text: True)
    d = tmp_path / "theme"
    d.mkdir()
    (d / "logo.txt").write_text("$1##\n")
    return d


def test_share_prefills_form_and_points_logo_at_ascii_txt(mine):
    cfg = {"logo": {"source": "logo.txt", "color": {"1": "red"}}, "modules": ["os"]}
    res = gallery.share(cfg, mine, "Neon-Cat", "Neon Cat", "glows", "cat, neon", open_browser=False)
    form = _form(res["url"])
    assert form["template"] == "theme.yml" and form["code"] == "neon-cat" and form["tags"] == "cat, neon"
    assert form["logo"] == "$1##\n"
    assert jsonc.loads(form["config"])["logo"]["source"] == "~/.config/fastfetch/ascii.txt"
    assert res["missing"] == [] and (res["folder"] / "ascii.txt").read_text() == "$1##\n"


def test_share_long_logo_goes_to_clipboard(mine):
    (mine / "logo.txt").write_text("⣿" * 3000)
    res = gallery.share({"logo": "logo.txt"}, mine, "big", "Big", open_browser=False)
    assert "logo" not in _form(res["url"]) and "config" in _form(res["url"])
    assert res["missing"] == ["ascii.txt"] and res["copied"] == "ascii.txt"
    assert len(res["url"]) <= gallery.MAX_URL


def test_share_refuses_command_modules_and_image_logos(mine):
    with pytest.raises(gallery.GalleryError, match="runs programs"):
        gallery.share({"modules": [{"type": "command"}]}, mine, "x1", "X", open_browser=False)
    (mine / "cat.png").write_bytes(b"\x89PNG")
    with pytest.raises(gallery.GalleryError, match="only text logos"):
        gallery.share({"logo": {"source": "cat.png"}}, mine, "x1", "X", open_browser=False)


def test_share_builtin_logo_and_bad_code(mine):
    res = gallery.share({"logo": "arch"}, mine, "arch-ish", "Arch", open_browser=False)
    assert "logo" not in _form(res["url"]) and res["missing"] == []
    with pytest.raises(gallery.GalleryError, match="code"):
        gallery.share({}, mine, "../x", "X", open_browser=False)


def test_cli_share_needs_a_name_for_the_live_config(site):
    with pytest.raises(SystemExit):
        cli.main(["share", "--no-browser"])
