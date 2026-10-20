"""Image -> braille logo, with fastfetch $N colour tags. Needs Pillow (pip install pillow).

Each text cell is a braille character holding a 2x4 grid of dots, so a logo W cells wide samples the
image at 2W x 4H. Lit dots are the subject; the background (transparency, or the colour of the image
corners) stays dark.

Modes
  color  lit = subject pixels that are not near-black; up to N colours, picked from the image
  light  lit = bright subject pixels (art drawn light on dark)
  ink    lit = dark subject pixels (line art / ink on a light background)
  auto   color for colourful images, otherwise light or ink depending on the background
"""
import colorsys

from . import colors as colorlib

MODES = ("auto", "color", "light", "ink")
_BITS = [(0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08), (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80)]


def have_pillow() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def _subject_mask(im, trim: int):
    """(L-mode mask of the subject, background brightness 0-1 or None when transparent).

    The subject is the opaque part of a transparent image, else whatever differs from the corners.
    """
    from PIL import Image, ImageChops, ImageFilter

    alpha = im.getchannel("A")
    bg_lum = None
    if alpha.getextrema()[0] < 250:
        mask = alpha.point(lambda p: 255 if p > 128 else 0)
    else:
        rgb = im.convert("RGB")
        w, h = rgb.size
        corners = [rgb.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
        bg = tuple(sorted(c[i] for c in corners)[1] for i in range(3))
        diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, bg)).convert("L")
        mask = diff.point(lambda p: 255 if p > 40 else 0)
        bg_lum = (0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]) / 255
    if trim > 0:
        mask = mask.filter(ImageFilter.MinFilter(trim * 2 + 1))
    return mask, bg_lum


def _auto_mode(rgb_small, mask_small, bg_lum) -> str:
    sats, lums, n = 0.0, 0.0, 0
    w, h = rgb_small.size
    for y in range(h):
        for x in range(w):
            if mask_small.getpixel((x, y)) > 127:
                r, g, b = (c / 255 for c in rgb_small.getpixel((x, y)))
                sats += colorsys.rgb_to_hsv(r, g, b)[1]
                lums += 0.299 * r + 0.587 * g + 0.114 * b
                n += 1
    if n and sats / n > 0.25:
        return "color"
    if bg_lum is not None:                       # opaque: dark art on a light page is ink
        return "ink" if bg_lum > 0.5 else "light"
    return "light" if n and lums / n > 0.5 else "ink"


def _vivid(rgb) -> tuple[int, int, int]:
    """Undo some of the dulling that averaging causes: more saturation, a little more light."""
    h, sat, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    if sat > 0.15:
        sat, v = min(1.0, sat * 1.3), min(1.0, max(v, 0.45) * 1.1)
    else:
        v = min(1.0, v * 1.1)
    return tuple(round(c * 255) for c in colorsys.hsv_to_rgb(h, sat, v))


def convert(path, width: int = 40, mode: str = "auto", ncolors: int = 4, trim: int = 0,
            threshold: int | None = None) -> tuple[str, dict, str]:
    """Returns (logo text with $N tags, {slot: colour spec}, mode actually used)."""
    from PIL import Image

    im = Image.open(path).convert("RGBA")
    mask, bg_lum = _subject_mask(im, trim)
    box = mask.getbbox()
    if not box:
        raise ValueError("could not find anything in the image")
    im, mask = im.crop(box), mask.crop(box)
    pw = max(2, width * 2)
    ph = max(4, round(im.height * pw / im.width / 4) * 4)
    rgb = im.convert("RGB").resize((pw, ph), Image.BOX)
    msk = mask.resize((pw, ph), Image.BOX)
    if mode == "auto":
        mode = _auto_mode(rgb, msk, bg_lum)

    def lum(x, y):
        r, g, b = rgb.getpixel((x, y))
        return 0.299 * r + 0.587 * g + 0.114 * b

    inside = lambda x, y: msk.getpixel((x, y)) > 127
    slot = [[0] * pw for _ in range(ph)]          # 0 = dark dot, k = lit in colour k
    palette: dict[str, str] = {}

    if mode == "color":
        # Pick colours at 3x resolution, where they are not yet blended with the black outlines,
        # then let each dot take the majority colour of its 3x3 block.
        f = 3
        big = im.convert("RGB").resize((pw * f, ph * f), Image.LANCZOS)
        bmask = mask.resize((pw * f, ph * f), Image.BOX)
        lit = [(x, y) for y in range(ph * f) for x in range(pw * f)
               if bmask.getpixel((x, y)) > 127 and max(big.getpixel((x, y))) > 56]
        if lit:
            strip = Image.new("RGB", (len(lit), 1))
            strip.putdata([big.getpixel(p) for p in lit])
            q = strip.quantize(colors=max(1, min(9, ncolors)), method=Image.Quantize.MEDIANCUT)
            pal = q.getpalette()
            code_slot: dict[int, int] = {}
            index_slot = {}
            for idx in sorted({i for _, i in q.getcolors()}):
                code = colorlib.nearest_256(_vivid(pal[3 * idx: 3 * idx + 3]))
                if code not in code_slot:
                    code_slot[code] = len(code_slot) + 1
                    palette[str(code_slot[code])] = f"38;5;{code}"
                index_slot[idx] = code_slot[code]
            votes = {}
            flat = getattr(q, "get_flattened_data", q.getdata)()
            for (x, y), idx in zip(lit, flat):
                cell = votes.setdefault((x // f, y // f), {})
                cell[index_slot[idx]] = cell.get(index_slot[idx], 0) + 1
            for (x, y), v in votes.items():
                if sum(v.values()) * 2 >= f * f:
                    slot[y][x] = max(v, key=v.get)
    else:
        inside_l = [lum(x, y) for y in range(ph) for x in range(pw) if inside(x, y)]
        mean = sum(inside_l) / len(inside_l) if inside_l else 128
        t = threshold if threshold is not None else (min(mean, 140) if mode == "ink" else max(mean, 100))
        for y in range(ph):
            for x in range(pw):
                if inside(x, y) and ((lum(x, y) < t) if mode == "ink" else (lum(x, y) > t)):
                    slot[y][x] = 1
        palette = {"1": "38;5;255"}

    lines = []
    for cy in range(0, ph, 4):
        out, current = [], None
        for cx in range(0, pw, 2):
            value, votes = 0, {}
            for dx, dy, bit in _BITS:
                k = slot[cy + dy][cx + dx]
                if k:
                    value |= bit
                    votes[k] = votes.get(k, 0) + 1
            if votes and len(palette) > 1:
                k = max(votes, key=votes.get)
                if k != current:
                    out.append(f"${k}")
                    current = k
            out.append(chr(0x2800 + value))
        lines.append("".join(out))
    return "\n".join(lines) + "\n", palette or {"1": "38;5;255"}, mode
