import json

import pytest

from fastcat_tui import colors, ffconfig, icons, jsonc, logo


def test_jsonc_comments_trailing_commas_and_urls():
    text = """// header
    {
        "$schema": "https://example.com/schema.json", /* block */
        "logo": {"source": "~/.config/fastfetch/ascii.txt",},
        "modules": ["os", {"type": "gpu", "format": "{3}",},], // trailing
    }"""
    cfg = jsonc.loads(text)
    assert cfg["$schema"] == "https://example.com/schema.json"
    assert cfg["modules"][1] == {"type": "gpu", "format": "{3}"}


def test_jsonc_keeps_commas_and_slashes_inside_strings():
    assert jsonc.loads('{"a": "x,]", "b": "//not a comment"}') == {"a": "x,]", "b": "//not a comment"}


def test_jsonc_roundtrip_is_valid_jsonc():
    cfg = {"key": " ", "n": 1}
    assert jsonc.loads(jsonc.dumps(cfg)) == cfg


@pytest.mark.parametrize("spec,sgr", [("red", "31"), ("38;5;196", "38;5;196"), ("#ff0000", "38;5;196"), ("bogus", "39")])
def test_to_sgr(spec, sgr):
    assert colors.to_sgr(spec) == sgr


def test_nearest_256_hits_exact_cube_and_gray():
    assert colors.nearest_256((0, 95, 135)) == 24
    assert colors.nearest_256((238, 238, 238)) == 255


def test_gradient_endpoints_and_spread():
    g = colors.gradient("38;5;255", "38;5;232", 5)
    assert g[0] == "38;5;255" and g[-1] == "38;5;232" and len(g) == 5
    assert colors.spread(["a", "b", "c"], 6) == ["a", "a", "b", "b", "c", "c"]


def test_logo_tokens_size_and_render():
    text = "$1ab$2cd\n$$x\n"
    assert logo.used_colors(text) == ["1", "2"]
    assert logo.plain(text) == "abcd\n$x\n"
    assert logo.size(text) == (4, 2)
    lines = logo.render(text, {"1": "red", "2": "38;5;46"})
    assert "\033[31mab" in lines[0] and "\033[38;5;46mcd" in lines[0]
    assert lines[1].startswith("\033[38;5;46m$x")   # colour carries to the next line


def test_untagged_logo_uses_colour_one():
    assert logo.used_colors("plain") == ["1"]


def test_fix_icons_replaces_icons_but_not_text_keys():
    cfg = {"modules": [{"type": "os", "key": " "}, {"type": "gpu", "key": "\U000f035b "},
                       {"type": "kernel", "key": "Kernel"}, {"type": "uptime"}, "memory"]}
    n = ffconfig.fix_icons(cfg)
    mods = cfg["modules"]
    assert mods[0]["key"] == icons.os_icon() + " "
    assert mods[1]["key"] == " "
    assert mods[2]["key"] == "Kernel" and "key" not in mods[3] and mods[4] == "memory"
    assert n == (2 if icons.os_icon() != "" else 1)


def test_recommended_icons_are_single_cell():
    for t in ffconfig.CATALOG:
        g = icons.recommended(t)
        assert g is None or 0xE000 <= ord(g) <= 0xF8FF, t


def test_set_key_colors_skips_breaks_and_converts_strings():
    cfg = {"modules": [{"type": "break"}, "os", {"type": "kernel"}]}
    ffconfig.set_key_colors(cfg, ["red", "blue"])
    assert cfg["modules"][0] == {"type": "break"}
    assert cfg["modules"][1] == {"type": "os", "keyColor": "red"}
    assert cfg["modules"][2]["keyColor"] == "blue"


def test_center_tall_logo_adds_breaks_and_is_idempotent():
    cfg = {"logo": {"source": "x"}, "modules": [{"type": t} for t in ("os", "kernel", "shell")]}
    ffconfig.center(cfg, 9)
    ffconfig.center(cfg, 9)
    assert [m["type"] for m in cfg["modules"]] == ["break"] * 3 + ["os", "kernel", "shell"]


def test_center_short_logo_pads_logo():
    cfg = {"logo": {"source": "x", "padding": {"top": 9, "right": 2}}, "modules": [{"type": "os"}] * 10}
    ffconfig.center(cfg, 4)
    assert cfg["logo"]["padding"] == {"right": 2, "top": 3}


def test_visible_logo_palette_drops_near_black():
    cfg = {"logo": {"color": {"1": "38;5;34", "2": "38;5;234"}}}
    assert ffconfig.visible_logo_palette(cfg, ["1", "2"]) == ["38;5;34"]


def test_icon_parse():
    assert icons.parse("f179") == ""
    assert icons.parse("U+F31A") == ""
    assert icons.parse("") == ""
    assert icons.parse("nope") is None


def test_recommended_config_is_plain_json():
    cfg = ffconfig.recommended(logo_palette={"1": "red"})
    json.dumps(cfg)
    assert cfg["logo"]["color"] == {"1": "red"} and cfg["display"]["key"]["width"] == 3


def test_render_strips_control_characters():
    lines = logo.render("a\x1b]0;pwned\x07b\n", {"1": "red"})
    assert "\x07" not in lines[0] and "]0;pwned" in lines[0] and "\x1b]" not in lines[0]
