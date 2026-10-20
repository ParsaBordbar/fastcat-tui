import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw  # noqa: E402

from fastcat_tui import image, logo  # noqa: E402


def test_color_mode_on_transparent_png(tmp_path):
    im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 49, 99), fill=(220, 30, 30, 255))
    d.rectangle((50, 0, 99, 99), fill=(30, 200, 30, 255))
    p = tmp_path / "two.png"
    im.save(p)
    text, palette, mode = image.convert(p, width=10, mode="auto", ncolors=2)
    assert mode == "color" and len(palette) == 2
    assert logo.size(text) == (10, 5)
    assert set(logo.plain(text).replace("\n", "")) == {"⣿"}


def test_ink_mode_on_white_background(tmp_path):
    im = Image.new("RGB", (80, 40), "white")
    ImageDraw.Draw(im).line((5, 20, 75, 20), fill="black", width=6)
    p = tmp_path / "line.jpg"
    im.save(p)
    text, palette, mode = image.convert(p, width=20, mode="auto")
    assert mode == "ink" and palette == {"1": "38;5;255"}
    assert "$" not in text and any(ch != "⠀" for ch in logo.plain(text).strip())


def test_empty_image_raises(tmp_path):
    p = tmp_path / "blank.png"
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(p)
    with pytest.raises(ValueError):
        image.convert(p)
