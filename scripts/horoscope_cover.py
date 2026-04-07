"""
Квадратна обкладинка «як на прикладі»: кремовий фон, темно-зелений текст і клевер.
Дата: «Гороскоп на 8 квітня» / «Гороскоп на 8 апреля».
"""

from __future__ import annotations

import io
from datetime import date

from PIL import Image, ImageDraw, ImageFont

SIZE = 1080
BG = (242, 239, 225)  # ~#F2EFE1
FG = (38, 78, 52)  # темно-зелений

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

_RU_MONTHS_GEN = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def cover_title_for_date(lang: str, d: date) -> str:
    if lang == "ru":
        return f"Гороскоп на {d.day} {_RU_MONTHS_GEN[d.month - 1]}"
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


def _draw_clover(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float) -> None:
    r = 28 * scale
    offsets = [
        (0, -r * 0.85),
        (r * 0.85, 0),
        (0, r * 0.85),
        (-r * 0.85, 0),
    ]
    for ox, oy in offsets:
        x0, y0 = cx + ox - r, cy + oy - r
        x1, y1 = cx + ox + r, cy + oy + r
        draw.ellipse((x0, y0, x1, y1), fill=FG)
    stem_w = max(4, int(6 * scale))
    h = int(55 * scale)
    draw.rectangle(
        (cx - stem_w // 2, cy + r * 0.4, cx + stem_w // 2, cy + r * 0.4 + h),
        fill=FG,
    )


def _fit_title_font(text: str, max_width: int, max_size: int, min_size: int) -> ImageFont.FreeTypeFont:
    for size in range(max_size, min_size - 1, -2):
        font = _load_serif_font(size)
        bbox = font.getbbox(text)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            return font
    return _load_serif_font(min_size)


def render_cover_png(lang: str, d: date) -> bytes:
    title = cover_title_for_date(lang, d)
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    _draw_clover(draw, SIZE // 2, SIZE * 0.22, scale=1.15)

    font = _fit_title_font(title, max_width=SIZE - 120, max_size=56, min_size=28)
    cx, cy = SIZE // 2, SIZE // 2 + int(SIZE * 0.06)
    draw.text((cx, cy), title, font=font, fill=FG, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
