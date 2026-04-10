"""
Квадратна обкладинка: кремовий фон, темно-зелений текст і клевер.
Підпис завжди українською: «Гороскоп на 8 квітня» (незалежно від HOROSCOPE_LANG).
"""

from __future__ import annotations

import io
import math
import os
from datetime import date

from PIL import Image, ImageDraw, ImageFont

SIZE = 1080
BG = (214, 207, 193)
CARD_BG = (240, 236, 226)
FG = (15, 66, 48)
MUTED = (231, 227, 217)
MUTED_2 = (224, 220, 210)
HANDLE = "@goroskop_dnya_ua"

_UA_MONTHS_GEN = (
    "січня",
    "лютого",
    "березня",
    "квітня",
    "травня",
    "червня",
    "липня",
    "серпня",
    "вересня",
    "жовтня",
    "листопада",
    "грудня",
)

def cover_title_for_date(d: date) -> str:
    return f"Гороскоп на {d.day} {_UA_MONTHS_GEN[d.month - 1]}"


def _font_paths() -> list[str]:
    return [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        r"C:\Windows\Fonts\timesbd.ttf",
        r"C:\Windows\Fonts\times.ttf",
        r"C:\Windows\Fonts\georgiab.ttf",
        r"C:\Windows\Fonts\georgia.ttf",
    ]


def _load_serif_font(size: int) -> ImageFont.FreeTypeFont:
    import os

    for p in _font_paths():
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_round_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int],
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def _draw_zodiac_wheel(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    rings = [r, int(r * 0.77), int(r * 0.56)]
    for rr in rings:
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=MUTED, width=2)
    for i in range(12):
        a = math.radians(-90 + i * 30)
        x = cx + int(math.cos(a) * r)
        y = cy + int(math.sin(a) * r)
        draw.line((cx, cy, x, y), fill=MUTED_2, width=1)
    glyphs = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]
    glyph_font = _load_serif_font(44)
    gr = int(r * 0.88)
    for i, g in enumerate(glyphs):
        a = math.radians(-90 + i * 30)
        gx = cx + int(math.cos(a) * gr)
        gy = cy + int(math.sin(a) * gr)
        draw.text((gx, gy), g, font=glyph_font, fill=MUTED, anchor="mm")


def _draw_stars(draw: ImageDraw.ImageDraw) -> None:
    stars = [
        (150, 130, 14),
        (250, 260, 10),
        (845, 190, 18),
        (915, 305, 11),
        (210, 870, 16),
        (880, 860, 12),
        (500, 100, 8),
    ]
    for x, y, s in stars:
        draw.line((x - s, y, x + s, y), fill=MUTED, width=2)
        draw.line((x, y - s, x, y + s), fill=MUTED, width=2)


def _draw_gradient_vertical(
    img: Image.Image, top_rgb: tuple[int, int, int], bottom_rgb: tuple[int, int, int]
) -> None:
    px = img.load()
    for y in range(SIZE):
        t = y / (SIZE - 1)
        r = int(top_rgb[0] * (1 - t) + bottom_rgb[0] * t)
        g = int(top_rgb[1] * (1 - t) + bottom_rgb[1] * t)
        b = int(top_rgb[2] * (1 - t) + bottom_rgb[2] * t)
        for x in range(SIZE):
            px[x, y] = (r, g, b)


def _render_soft_beige(draw: ImageDraw.ImageDraw, title: str) -> None:
    margin = 98
    _draw_round_rect(
        draw,
        (margin, margin, SIZE - margin, SIZE - margin),
        radius=4,
        fill=CARD_BG,
    )
    _draw_stars(draw)
    _draw_zodiac_wheel(draw, SIZE // 2, int(SIZE * 0.53), int(SIZE * 0.33))
    top_symbol_font = _load_serif_font(50)
    draw.text((SIZE // 2, margin + 28), "♉", font=top_symbol_font, fill=FG, anchor="mm")
    title_band_h = 170
    title_band_y = SIZE // 2 + 30
    draw.rectangle(
        (
            margin,
            title_band_y - title_band_h // 2,
            SIZE - margin,
            title_band_y + title_band_h // 2,
        ),
        fill=(233, 228, 216),
    )
    font = _fit_title_font(title, max_width=SIZE - 220, max_size=92, min_size=44)
    draw.text((SIZE // 2, title_band_y), title, font=font, fill=FG, anchor="mm")
    handle_font = _load_serif_font(46)
    draw.text((SIZE // 2, SIZE - margin - 18), HANDLE, font=handle_font, fill=FG, anchor="ms")


def _render_emerald_noir(img: Image.Image, draw: ImageDraw.ImageDraw, title: str) -> None:
    _draw_gradient_vertical(img, (233, 226, 212), (216, 206, 190))
    gold = (150, 127, 84)
    pale = (33, 62, 49)
    margin = 72
    draw.rounded_rectangle(
        (margin, margin, SIZE - margin, SIZE - margin),
        radius=26,
        fill=(242, 238, 228),
        outline=gold,
        width=3,
    )
    draw.rounded_rectangle(
        (margin + 20, margin + 20, SIZE - margin - 20, SIZE - margin - 20),
        radius=20,
        outline=(134, 138, 120),
        width=2,
    )
    cx, cy = SIZE // 2, int(SIZE * 0.47)
    r = int(SIZE * 0.31)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(156, 160, 142), width=2)
    draw.ellipse(
        (
            cx - int(r * 0.76),
            cy - int(r * 0.76),
            cx + int(r * 0.76),
            cy + int(r * 0.76),
        ),
        outline=(174, 176, 160),
        width=1,
    )
    for i in range(12):
        a = math.radians(-90 + i * 30)
        x = cx + int(math.cos(a) * r)
        y = cy + int(math.sin(a) * r)
        draw.line((cx, cy, x, y), fill=(194, 192, 178), width=1)
    glyphs = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]
    glyph_font = _load_serif_font(40)
    gr = int(r * 0.89)
    for i, g in enumerate(glyphs):
        a = math.radians(-90 + i * 30)
        gx = cx + int(math.cos(a) * gr)
        gy = cy + int(math.sin(a) * gr)
        draw.text((gx, gy), g, font=glyph_font, fill=(185, 184, 170), anchor="mm")
    title_font = _fit_title_font(title, max_width=SIZE - 240, max_size=106, min_size=48)
    draw.text((SIZE // 2, int(SIZE * 0.53)), title, font=title_font, fill=pale, anchor="mm")
    sub_font = _load_serif_font(44)
    draw.text((SIZE // 2, SIZE - margin - 24), HANDLE, font=sub_font, fill=gold, anchor="ms")
    top_font = _load_serif_font(44)
    draw.text((SIZE // 2, margin + 28), "✶", font=top_font, fill=gold, anchor="mm")


def _fit_title_font(text: str, max_width: int, max_size: int, min_size: int) -> ImageFont.FreeTypeFont:
    for size in range(max_size, min_size - 1, -2):
        font = _load_serif_font(size)
        bbox = font.getbbox(text)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            return font
    return _load_serif_font(min_size)


def render_cover_png(d: date) -> bytes:
    title = cover_title_for_date(d)
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    style = (os.environ.get("HOROSCOPE_COVER_STYLE") or "emerald_noir").strip().lower()
    if style == "soft_beige":
        _render_soft_beige(draw, title)
    else:
        _render_emerald_noir(img, draw, title)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
