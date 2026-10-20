from pathlib import Path

import pytest

from fastcat_tui import fastfetch, jsonc, settings, themes


@pytest.fixture
def homes(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("FASTCAT_TUI_HOME", str(tmp_path / "app"))
    return tmp_path


def make_theme(base: Path, category: str, name: str, source: str = "~/.config/fastfetch/ascii.txt") -> Path:
    d = base / category / name / "fastfetch"
    d.mkdir(parents=True)
    (d / "config.jsonc").write_text('// c\n{"logo": {"source": "%s"}, "modules": ["os",],}' % source)
    (d / "ascii.txt").write_text("$1##\n$2##\n")
    return d


def test_resolve_source_variants(tmp_path):
    for src in ("~/.config/fastfetch/ascii.txt", "$HOME/.config/fastfetch/ascii.txt", "ascii.txt"):
        assert themes.resolve_source(src, tmp_path) == tmp_path / "ascii.txt"
    assert themes.resolve_source("/abs/logo.txt", tmp_path) == Path("/abs/logo.txt")


def test_discovery_and_find(homes):
    pack = homes / "FastCat"
    make_theme(pack, "Large-Themes", "Cat")
    make_theme(pack, "Small-Themes", "Cat")
    settings.save({"theme_dirs": [str(pack)]})
    found = [t for t in themes.all_themes() if t.source == "fastcat"]
    assert {(t.category, t.name) for t in found} == {("Large", "Cat"), ("Small", "Cat")}
    assert themes.find("small/cat").category == "Small"
    assert any(t.source == "bundled" for t in themes.all_themes())


def test_logo_file_skips_images(homes):
    d = make_theme(homes / "p", "X", "Pic", "image.png")
    (d / "image.png").write_bytes(b"png")
    cfg = jsonc.load(d / "config.jsonc")
    assert themes.logo_file(cfg, d) is None


def test_apply_backup_restore(homes):
    live = fastfetch.config_dir()
    live.mkdir(parents=True)
    (live / "config.jsonc").write_text('{"mine": true}')
    theme = themes.Theme("Cat", "Large", make_theme(homes / "p", "Large-Themes", "Cat"), "fastcat")

    saved = fastfetch.apply(theme)
    assert (saved / "config.jsonc").read_text() == '{"mine": true}'
    assert (live / "ascii.txt").exists()

    fastfetch.restore(saved)
    assert (live / "config.jsonc").read_text() == '{"mine": true}'
    assert len(fastfetch.backups()) == 2       # one per change


def test_standalone_points_logo_at_theme(homes):
    d = make_theme(homes / "p", "Large-Themes", "Cat")
    cfg = fastfetch.standalone(jsonc.load(d / "config.jsonc"), d)
    assert cfg["logo"]["source"] == str(d / "ascii.txt")


def test_bundled_themes_load():
    bundled = [t for t in themes.all_themes() if t.source == "bundled"]
    assert len(bundled) >= 6
    for t in bundled:
        assert t.config()["modules"]
        assert t.logo_text()


def test_non_object_config_is_a_value_error(homes):
    live = fastfetch.config_dir()
    live.mkdir(parents=True)
    (live / "config.jsonc").write_text("[]")
    assert fastfetch.load_live() is None


def test_backups_sort_by_counter(homes):
    for name in ("2026-01-01_00-00-00", "2026-01-01_00-00-00-2", "2026-01-01_00-00-00-10", "2025-12-31_23-59-59"):
        (settings.backups_dir() / name).mkdir(parents=True)
    assert [b.name for b in fastfetch.backups()] == [
        "2026-01-01_00-00-00-10", "2026-01-01_00-00-00-2", "2026-01-01_00-00-00", "2025-12-31_23-59-59"]


def test_failed_apply_keeps_live_config(homes, monkeypatch):
    live = fastfetch.config_dir()
    live.mkdir(parents=True)
    (live / "config.jsonc").write_text('{"mine": true}')
    theme = themes.Theme("Cat", "Large", make_theme(homes / "p", "Large-Themes", "Cat"), "fastcat")

    def broken_copy(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(fastfetch.shutil, "copytree", broken_copy)
    with pytest.raises(OSError):
        fastfetch._install(theme.path)
    assert (live / "config.jsonc").read_text() == '{"mine": true}'
    assert [p.name for p in live.parent.iterdir()] == ["fastfetch"]
